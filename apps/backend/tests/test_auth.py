"""Tests for auth dependencies."""

import uuid
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.auth import Role
from app.auth.dependencies import ROLE_HIERARCHY, get_current_user
from app.core.database import get_session
from app.models.user import User


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


def test_require_role_forbidden() -> None:
    from app.main import app

    viewer = MagicMock(spec=User)
    viewer.id = uuid.uuid4()
    viewer.email = "viewer@test.com"
    viewer.name = "Viewer"
    viewer.role = Role.VIEWER
    viewer.created_at = viewer.updated_at = None

    mock_db = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: viewer

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/audit/logs")
    assert resp.status_code == 403
    app.dependency_overrides.clear()


def test_user_not_found_returns_401() -> None:
    from app.main import app

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)
    app.dependency_overrides[get_session] = lambda: mock_db

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(
        "/api/v1/users/me",
        headers={"x-user-id": str(uuid.uuid4())},
    )
    assert resp.status_code == 401
    app.dependency_overrides.clear()
