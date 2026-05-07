"""Tests for preset and session repositories."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.analysis_session import SessionPriority, SessionState
from app.services.repositories.preset import PresetRepository
from app.services.repositories.session import (
    InvalidStateTransitionError,
    SessionRepository,
    VALID_TRANSITIONS,
)


def _db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    return db


def _scalars_all(items: list) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


# ── PresetRepository ────────────────────────────────────────


@pytest.mark.asyncio
async def test_preset_list_no_filter() -> None:
    db = _db()
    db.execute = AsyncMock(return_value=_scalars_all(["p1", "p2"]))
    repo = PresetRepository(db)

    presets = await repo.list()
    assert presets == ["p1", "p2"]


@pytest.mark.asyncio
async def test_preset_list_by_agent() -> None:
    db = _db()
    db.execute = AsyncMock(return_value=_scalars_all(["p1"]))
    repo = PresetRepository(db)

    presets = await repo.list(agent_id=uuid.uuid4())
    assert presets == ["p1"]


@pytest.mark.asyncio
async def test_preset_get() -> None:
    db = _db()
    sentinel = object()
    db.get = AsyncMock(return_value=sentinel)
    repo = PresetRepository(db)

    result = await repo.get(uuid.uuid4())
    assert result is sentinel


@pytest.mark.asyncio
async def test_preset_get_not_found() -> None:
    db = _db()
    db.get = AsyncMock(return_value=None)
    repo = PresetRepository(db)

    result = await repo.get(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_preset_create() -> None:
    db = _db()
    repo = PresetRepository(db)

    preset = await repo.create(name="fast-scan", agent_id=uuid.uuid4())
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    assert preset.name == "fast-scan"


@pytest.mark.asyncio
async def test_preset_update() -> None:
    db = _db()
    repo = PresetRepository(db)

    preset = MagicMock()
    preset.name = "old"
    updated = await repo.update(preset, name="new", description=None)
    assert updated.name == "new"
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_preset_update_skips_none() -> None:
    db = _db()
    repo = PresetRepository(db)

    preset = MagicMock()
    preset.name = "keep"
    await repo.update(preset, name=None)
    assert preset.name == "keep"


@pytest.mark.asyncio
async def test_preset_delete() -> None:
    db = _db()
    repo = PresetRepository(db)

    preset = MagicMock()
    await repo.delete(preset)
    db.delete.assert_awaited_once_with(preset)
    db.flush.assert_awaited_once()


# ── SessionRepository ───────────────────────────────────────


@pytest.mark.asyncio
async def test_session_list_by_project() -> None:
    db = _db()
    db.execute = AsyncMock(return_value=_scalars_all(["s1", "s2"]))
    repo = SessionRepository(db)

    sessions = await repo.list_by_project(uuid.uuid4())
    assert len(sessions) == 2


@pytest.mark.asyncio
async def test_session_get() -> None:
    db = _db()
    sentinel = object()
    db.get = AsyncMock(return_value=sentinel)
    repo = SessionRepository(db)

    result = await repo.get(uuid.uuid4())
    assert result is sentinel


@pytest.mark.asyncio
async def test_session_list_queue_no_filter() -> None:
    db = _db()
    db.execute = AsyncMock(return_value=_scalars_all(["q1"]))
    repo = SessionRepository(db)

    queue = await repo.list_queue()
    assert queue == ["q1"]


@pytest.mark.asyncio
async def test_session_list_queue_with_state() -> None:
    db = _db()
    db.execute = AsyncMock(return_value=_scalars_all([]))
    repo = SessionRepository(db)

    queue = await repo.list_queue(state=SessionState.QUEUED)
    assert queue == []


@pytest.mark.asyncio
async def test_session_create() -> None:
    db = _db()
    repo = SessionRepository(db)

    session = await repo.create(
        project_id=uuid.uuid4(),
        commit_sha="abc123",
        agent_id=uuid.uuid4(),
        preset_id=uuid.uuid4(),
        model_version="claude-v1",
        priority=SessionPriority.URGENT,
    )
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    assert session.commit_sha == "abc123"
    assert session.priority == SessionPriority.URGENT


@pytest.mark.asyncio
async def test_session_transition_valid() -> None:
    db = _db()
    repo = SessionRepository(db)

    analysis = MagicMock()
    analysis.state = SessionState.QUEUED
    result = await repo.transition(analysis, SessionState.PREPARING)
    assert result.state == SessionState.PREPARING
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_session_transition_invalid() -> None:
    db = _db()
    repo = SessionRepository(db)

    analysis = MagicMock()
    analysis.state = SessionState.COMPLETED
    with pytest.raises(InvalidStateTransitionError, match="Cannot transition"):
        await repo.transition(analysis, SessionState.RUNNING)


@pytest.mark.asyncio
async def test_session_transition_cancel_from_queued() -> None:
    db = _db()
    repo = SessionRepository(db)

    analysis = MagicMock()
    analysis.state = SessionState.QUEUED
    result = await repo.transition(analysis, SessionState.CANCELED)
    assert result.state == SessionState.CANCELED


def test_valid_transitions_terminal_states() -> None:
    assert VALID_TRANSITIONS[SessionState.COMPLETED] == set()
    assert VALID_TRANSITIONS[SessionState.FAILED] == set()
    assert VALID_TRANSITIONS[SessionState.CANCELED] == set()
