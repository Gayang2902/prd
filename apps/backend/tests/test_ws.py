"""Tests for WebSocket session sync handler with Redis pub/sub."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.api.v1.ws import _connections
from app.main import app


class FakePubSub:
    """In-process fake that delivers published messages synchronously."""

    def __init__(self) -> None:
        self._channels: dict[str, list[AsyncMock]] = {}

    def subscriber(self) -> "FakeSubscriber":
        return FakeSubscriber(self)

    async def publish(self, channel: str, message: str) -> None:
        if channel in self._channels:
            for cb in self._channels[channel]:
                await cb({"type": "message", "data": message})

    def register(self, channel: str, cb: AsyncMock) -> None:
        self._channels.setdefault(channel, []).append(cb)

    def unregister(self, channel: str, cb: AsyncMock) -> None:
        if channel in self._channels:
            self._channels[channel] = [c for c in self._channels[channel] if c is not cb]


class FakeSubscriber:
    def __init__(self, hub: FakePubSub) -> None:
        self._hub = hub
        self._channel: str | None = None
        self._queue: asyncio.Queue[dict[str, str]] = asyncio.Queue()

    async def subscribe(self, channel: str) -> None:
        self._channel = channel

    async def unsubscribe(self, channel: str) -> None:
        pass

    async def aclose(self) -> None:
        pass

    async def listen(self):  # type: ignore[no-untyped-def]
        while True:
            msg = await self._queue.get()
            yield msg


class FakeRedis:
    """Minimal fake Redis that routes publish → _local_broadcast directly."""

    def __init__(self) -> None:
        self._callbacks: dict[str, list[object]] = {}

    async def publish(self, channel: str, message: str) -> None:
        from app.api.v1.ws import _local_broadcast

        data = json.loads(message)
        await _local_broadcast(channel.split(":")[-1], data["event"], data.get("exclude_id"))

    def pubsub(self) -> MagicMock:
        mock = MagicMock()
        mock.subscribe = AsyncMock()
        mock.unsubscribe = AsyncMock()
        mock.aclose = AsyncMock()
        mock.listen = MagicMock(return_value=_empty_aiter())
        return mock


async def _empty_aiter():  # type: ignore[no-untyped-def]
    return
    yield  # noqa: RET504


def _patch_redis():  # type: ignore[no-untyped-def]
    fake = FakeRedis()
    return patch("app.api.v1.ws._get_redis", new=AsyncMock(return_value=fake))


def test_ws_join_and_leave() -> None:
    client = TestClient(app)
    with _patch_redis():
        with client.websocket_connect("/ws/sessions/s1?user_id=u1"):
            assert "s1" in _connections
        assert "s1" not in _connections


def test_ws_finding_status_changed() -> None:
    client = TestClient(app)
    with (
        _patch_redis(),
        client.websocket_connect("/ws/sessions/s2?user_id=reviewer1") as ws1,
        client.websocket_connect("/ws/sessions/s2?user_id=reviewer2") as ws2,
    ):
        joined = ws1.receive_json()
        assert joined["type"] == "user_joined"
        assert joined["user_id"] == "reviewer2"

        ws2.send_json(
            {
                "type": "finding_status_changed",
                "finding_id": "f1",
                "status": "confirmed",
            }
        )
        event = ws1.receive_json()
        assert event["type"] == "finding_status_changed"
        assert event["finding_id"] == "f1"
        assert event["user_id"] == "reviewer2"


def test_ws_comment_added() -> None:
    client = TestClient(app)
    with (
        _patch_redis(),
        client.websocket_connect("/ws/sessions/s3?user_id=a") as ws1,
        client.websocket_connect("/ws/sessions/s3?user_id=b") as ws2,
    ):
        ws1.receive_json()  # user_joined

        ws2.send_json(
            {
                "type": "comment_added",
                "finding_id": "f2",
                "content": "looks bad",
            }
        )
        event = ws1.receive_json()
        assert event["type"] == "comment_added"
        assert event["content"] == "looks bad"


def test_ws_cursor_moved() -> None:
    client = TestClient(app)
    with (
        _patch_redis(),
        client.websocket_connect("/ws/sessions/s4?user_id=x") as ws1,
        client.websocket_connect("/ws/sessions/s4?user_id=y") as ws2,
    ):
        ws1.receive_json()  # user_joined

        ws2.send_json({"type": "cursor_moved", "finding_id": "f3"})
        event = ws1.receive_json()
        assert event["type"] == "cursor_moved"
        assert event["finding_id"] == "f3"


def test_ws_user_left_broadcast() -> None:
    client = TestClient(app)
    with (
        _patch_redis(),
        client.websocket_connect("/ws/sessions/s5?user_id=stayer") as ws1,
    ):  # noqa: SIM117
        with client.websocket_connect("/ws/sessions/s5?user_id=leaver"):
            ws1.receive_json()  # user_joined
        left = ws1.receive_json()
        assert left["type"] == "user_left"
        assert left["user_id"] == "leaver"


def test_ws_anonymous_user() -> None:
    client = TestClient(app)
    with (
        _patch_redis(),
        client.websocket_connect("/ws/sessions/s6") as ws1,
        client.websocket_connect("/ws/sessions/s6"),
    ):
        joined = ws1.receive_json()
        assert joined["user_id"] == "anonymous"
