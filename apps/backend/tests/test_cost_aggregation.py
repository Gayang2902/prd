"""Tests for cost aggregation service."""

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.cost_aggregation import cost_by_agent, cost_by_project, cost_daily, cost_summary


def _mock_row(**kwargs: object) -> MagicMock:
    row = MagicMock()
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


@pytest.mark.asyncio
async def test_cost_summary_no_filters() -> None:
    db = AsyncMock()
    row = _mock_row(total_sessions=5, total_tokens=1000, total_cost=Decimal("12.50"))
    result = MagicMock()
    result.one.return_value = row
    db.execute = AsyncMock(return_value=result)

    data = await cost_summary(db)
    assert data["total_sessions"] == 5
    assert data["total_tokens"] == 1000
    assert data["total_cost"] == Decimal("12.50")


@pytest.mark.asyncio
async def test_cost_summary_with_date_range() -> None:
    db = AsyncMock()
    row = _mock_row(total_sessions=2, total_tokens=500, total_cost=Decimal("5.00"))
    result = MagicMock()
    result.one.return_value = row
    db.execute = AsyncMock(return_value=result)

    data = await cost_summary(db, since=date(2025, 1, 1), until=date(2025, 12, 31))
    assert data["total_sessions"] == 2


@pytest.mark.asyncio
async def test_cost_by_project() -> None:
    db = AsyncMock()
    pid = uuid.uuid4()
    rows = [_mock_row(project_id=pid, sessions=3, tokens=800, cost=Decimal("10.00"))]
    result = MagicMock()
    result.all.return_value = rows
    db.execute = AsyncMock(return_value=result)

    data = await cost_by_project(db, since=date(2025, 1, 1))
    assert len(data) == 1
    assert data[0]["project_id"] == str(pid)
    assert data[0]["sessions"] == 3


@pytest.mark.asyncio
async def test_cost_by_agent() -> None:
    db = AsyncMock()
    rows = [_mock_row(model_version="claude-v1", sessions=4, tokens=900, cost=Decimal("8.00"))]
    result = MagicMock()
    result.all.return_value = rows
    db.execute = AsyncMock(return_value=result)

    data = await cost_by_agent(db, until=date(2025, 6, 30))
    assert len(data) == 1
    assert data[0]["model_version"] == "claude-v1"


@pytest.mark.asyncio
async def test_cost_daily() -> None:
    db = AsyncMock()
    rows = [
        _mock_row(day="2025-01-01", sessions=2, tokens=300, cost=Decimal("3.00")),
        _mock_row(day="2025-01-02", sessions=1, tokens=100, cost=Decimal("1.50")),
    ]
    result = MagicMock()
    result.all.return_value = rows
    db.execute = AsyncMock(return_value=result)

    data = await cost_daily(db, since=date(2025, 1, 1), until=date(2025, 1, 3))
    assert len(data) == 2
    assert data[0]["date"] == "2025-01-01"
    assert data[1]["sessions"] == 1
