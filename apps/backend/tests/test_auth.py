"""Tests for auth dependencies."""

import uuid

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.auth import CurrentUser, Role, require_role
from app.auth.dependencies import get_current_user, ROLE_HIERARCHY
from app.core.errors import register_error_handlers


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
