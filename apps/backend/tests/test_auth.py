"""Tests for auth dependencies."""

from fastapi.testclient import TestClient

from app.auth import Role
from app.auth.dependencies import ROLE_HIERARCHY


def test_role_hierarchy_ordering() -> None:
    assert ROLE_HIERARCHY[Role.VIEWER] < ROLE_HIERARCHY[Role.REVIEWER]
    assert ROLE_HIERARCHY[Role.REVIEWER] < ROLE_HIERARCHY[Role.LEAD]
    assert ROLE_HIERARCHY[Role.LEAD] < ROLE_HIERARCHY[Role.ADMIN]


def test_missing_user_id_header() -> None:
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 422 or resp.status_code == 401


def test_invalid_user_id_header() -> None:
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/users/me", headers={"x-user-id": "not-a-uuid"})
    assert resp.status_code == 401
