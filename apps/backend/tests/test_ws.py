"""Tests for WebSocket session sync handler."""

from fastapi.testclient import TestClient

from app.api.v1.ws import _connections
from app.main import app


def test_ws_join_and_leave() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws/sessions/s1?user_id=u1"):
        assert "s1" in _connections
    assert "s1" not in _connections


def test_ws_finding_status_changed() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws/sessions/s2?user_id=reviewer1") as ws1:  # noqa: SIM117
        with client.websocket_connect("/ws/sessions/s2?user_id=reviewer2") as ws2:
            joined = ws1.receive_json()
            assert joined["type"] == "user_joined"
            assert joined["user_id"] == "reviewer2"

            ws2.send_json({
                "type": "finding_status_changed",
                "finding_id": "f1",
                "status": "confirmed",
            })
            event = ws1.receive_json()
            assert event["type"] == "finding_status_changed"
            assert event["finding_id"] == "f1"
            assert event["user_id"] == "reviewer2"


def test_ws_comment_added() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws/sessions/s3?user_id=a") as ws1:  # noqa: SIM117
        with client.websocket_connect("/ws/sessions/s3?user_id=b") as ws2:
            ws1.receive_json()  # user_joined

            ws2.send_json({
                "type": "comment_added",
                "finding_id": "f2",
                "content": "looks bad",
            })
            event = ws1.receive_json()
            assert event["type"] == "comment_added"
            assert event["content"] == "looks bad"


def test_ws_cursor_moved() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws/sessions/s4?user_id=x") as ws1:  # noqa: SIM117
        with client.websocket_connect("/ws/sessions/s4?user_id=y") as ws2:
            ws1.receive_json()  # user_joined

            ws2.send_json({"type": "cursor_moved", "finding_id": "f3"})
            event = ws1.receive_json()
            assert event["type"] == "cursor_moved"
            assert event["finding_id"] == "f3"


def test_ws_user_left_broadcast() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws/sessions/s5?user_id=stayer") as ws1:
        with client.websocket_connect("/ws/sessions/s5?user_id=leaver"):  # noqa: SIM117
            ws1.receive_json()  # user_joined
        left = ws1.receive_json()
        assert left["type"] == "user_left"
        assert left["user_id"] == "leaver"


def test_ws_anonymous_user() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws/sessions/s6") as ws1:  # noqa: SIM117
        with client.websocket_connect("/ws/sessions/s6"):
            joined = ws1.receive_json()
            assert joined["user_id"] == "anonymous"
