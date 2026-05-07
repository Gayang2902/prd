"""WebSocket handler for real-time verification screen sync.

Clients connect per session. Events are broadcast via Redis pub/sub so
multiple backend instances stay in sync.
"""

import asyncio
import json
from collections import defaultdict
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings

router = APIRouter()

_connections: dict[str, set[WebSocket]] = defaultdict(set)
_subscribers: dict[str, asyncio.Task[None]] = {}
_redis: aioredis.Redis | None = None


def _channel(session_id: str) -> str:
    return f"ws:session:{session_id}"


async def _get_redis() -> aioredis.Redis:
    global _redis  # noqa: PLW0603
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def _local_broadcast(
    session_id: str, event: dict[str, Any], exclude_id: str | None = None
) -> None:
    dead: list[WebSocket] = []
    for ws in _connections[session_id]:
        if exclude_id and getattr(ws, "_ws_id", None) == exclude_id:
            continue
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections[session_id].discard(ws)


async def broadcast(
    session_id: str,
    event: dict[str, Any],
    exclude_id: str | None = None,
) -> None:
    r = await _get_redis()
    payload = json.dumps({"event": event, "exclude_id": exclude_id}, ensure_ascii=False)
    await r.publish(_channel(session_id), payload)


async def _subscribe_loop(session_id: str) -> None:
    r = await _get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(_channel(session_id))
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = json.loads(message["data"])
            await _local_broadcast(session_id, data["event"], data.get("exclude_id"))
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(_channel(session_id))
        await pubsub.aclose()  # type: ignore[no-untyped-call]


def _ensure_subscriber(session_id: str) -> None:
    if session_id not in _subscribers or _subscribers[session_id].done():
        _subscribers[session_id] = asyncio.create_task(_subscribe_loop(session_id))


def _cleanup_subscriber(session_id: str) -> None:
    if session_id in _subscribers:
        _subscribers[session_id].cancel()
        del _subscribers[session_id]


@router.websocket("/ws/sessions/{session_id}")
async def session_ws(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()

    ws_id = f"{id(websocket)}"
    websocket._ws_id = ws_id  # type: ignore[attr-defined]

    _connections[session_id].add(websocket)
    _ensure_subscriber(session_id)

    user_id = websocket.query_params.get("user_id", "anonymous")

    await broadcast(
        session_id,
        {"type": "user_joined", "user_id": user_id},
        exclude_id=ws_id,
    )

    try:
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")

            if event_type == "finding_status_changed":
                await broadcast(
                    session_id,
                    {
                        "type": "finding_status_changed",
                        "user_id": user_id,
                        "finding_id": data.get("finding_id"),
                        "status": data.get("status"),
                    },
                    exclude_id=ws_id,
                )
            elif event_type == "comment_added":
                await broadcast(
                    session_id,
                    {
                        "type": "comment_added",
                        "user_id": user_id,
                        "finding_id": data.get("finding_id"),
                        "content": data.get("content"),
                    },
                    exclude_id=ws_id,
                )
            elif event_type == "cursor_moved":
                await broadcast(
                    session_id,
                    {
                        "type": "cursor_moved",
                        "user_id": user_id,
                        "finding_id": data.get("finding_id"),
                    },
                    exclude_id=ws_id,
                )

    except WebSocketDisconnect:
        pass
    finally:
        _connections[session_id].discard(websocket)
        await broadcast(
            session_id,
            {"type": "user_left", "user_id": user_id},
        )
        if not _connections[session_id]:
            del _connections[session_id]
            _cleanup_subscriber(session_id)
