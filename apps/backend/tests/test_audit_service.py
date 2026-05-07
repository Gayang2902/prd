"""Tests for audit service functions."""

import uuid
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from app.services.audit import list_audit_logs, record_audit


@pytest.mark.asyncio
async def test_record_audit() -> None:
    db = AsyncMock()
    db.flush = AsyncMock()

    log = await record_audit(
        db,
        user_id=uuid.uuid4(),
        action="login",
        resource_type="user",
        resource_id="u1",
        detail="test",
        ip_address="127.0.0.1",
    )
    db.add.assert_called_once()
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_audit_minimal() -> None:
    db = AsyncMock()
    db.flush = AsyncMock()

    log = await record_audit(
        db,
        user_id=None,
        action="system_event",
        resource_type="session",
        resource_id="s1",
    )
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_list_audit_logs_no_filters() -> None:
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    logs = await list_audit_logs(db)
    assert logs == []
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_audit_logs_with_filters() -> None:
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    logs = await list_audit_logs(
        db,
        action="login",
        resource_type="user",
        user_id=uuid.uuid4(),
        limit=50,
        offset=10,
    )
    assert logs == []
