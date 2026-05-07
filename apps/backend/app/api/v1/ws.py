"""WebSocket handler for real-time verification screen sync.

Clients connect per session. When a reviewer changes a finding status or adds
a comment, the event is broadcast to all other connected reviewers.
"""

from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

_connections: dict[str, set[WebSocket]] = defaultdict(set)


async def broadcast(session_id: str, event: dict, exclude: WebSocket | None = None) -> None:
    dead: list[WebSocket] = []
    for ws in _connections[session_id]:
        if ws is exclude:
            continue
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections[session_id].discard(ws)


@router.websocket("/ws/sessions/{session_id}")
async def session_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    _connections[session_id].add(websocket)

    user_id = websocket.query_params.get("user_id", "anonymous")

    await broadcast(
        session_id,
        {"type": "user_joined", "user_id": user_id},
        exclude=websocket,
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
                    exclude=websocket,
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
                    exclude=websocket,
                )
            elif event_type == "cursor_moved":
                await broadcast(
                    session_id,
                    {
                        "type": "cursor_moved",
                        "user_id": user_id,
                        "finding_id": data.get("finding_id"),
                    },
                    exclude=websocket,
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
