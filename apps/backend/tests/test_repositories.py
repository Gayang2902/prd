"""Tests for repository layer."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.analysis_session import SessionPriority, SessionState, SessionType
from app.models.finding_status import VerificationStatus
from app.models.project import Priority, ProjectStatus
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.repositories.comment import CommentRepository
from app.services.repositories.finding import FindingRepository
from app.services.repositories.project import ProjectRepository
from app.services.repositories.session import SessionRepository
from app.services.repositories.user import UserRepository


def _db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _scalars_all(items: list) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _scalar_one_or_none(item: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = item
    return result


# ── UserRepository ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_list() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalars_all(["u1", "u2"]))
    repo = UserRepository(db)

    users = await repo.list()
    assert users == ["u1", "u2"]
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_get() -> None:
    db = AsyncMock()
    uid = uuid.uuid4()
    sentinel = object()
    db.get = AsyncMock(return_value=sentinel)
    repo = UserRepository(db)

    result = await repo.get(uid)
    assert result is sentinel
    db.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_get_by_email() -> None:
    db = AsyncMock()
    sentinel = object()
    db.execute = AsyncMock(return_value=_scalar_one_or_none(sentinel))
    repo = UserRepository(db)

    result = await repo.get_by_email("a@b.com")
    assert result is sentinel


@pytest.mark.asyncio
async def test_user_get_by_email_not_found() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_one_or_none(None))
    repo = UserRepository(db)

    result = await repo.get_by_email("missing@b.com")
    assert result is None


@pytest.mark.asyncio
async def test_user_create() -> None:
    db = _db()
    repo = UserRepository(db)

    user = await repo.create(email="x@y.com", name="X", role="admin")
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    assert user.email == "x@y.com"
    assert user.name == "X"
    assert user.role == "admin"


# ── CommentRepository ───────────────────────────────────────


@pytest.mark.asyncio
async def test_comment_list_by_finding() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalars_all(["c1"]))
    repo = CommentRepository(db)

    comments = await repo.list_by_finding(uuid.uuid4())
    assert comments == ["c1"]


@pytest.mark.asyncio
async def test_comment_list_by_finding_empty() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalars_all([]))
    repo = CommentRepository(db)

    comments = await repo.list_by_finding(uuid.uuid4())
    assert comments == []


@pytest.mark.asyncio
async def test_comment_create() -> None:
    db = _db()
    repo = CommentRepository(db)

    comment = await repo.create(
        finding_id=uuid.uuid4(),
        author_id=uuid.uuid4(),
        content="looks bad",
    )
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    assert comment.content == "looks bad"


# ── ProjectRepository ───────────────────────────────────────


@pytest.mark.asyncio
async def test_project_list_no_filters() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalars_all(["p1", "p2"]))
    repo = ProjectRepository(db)

    projects = await repo.list()
    assert len(projects) == 2


@pytest.mark.asyncio
async def test_project_list_with_status() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalars_all(["p1"]))
    repo = ProjectRepository(db)

    projects = await repo.list(status=ProjectStatus.COMPLETED)
    assert projects == ["p1"]


@pytest.mark.asyncio
async def test_project_list_with_owner() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalars_all([]))
    repo = ProjectRepository(db)

    projects = await repo.list(owner_id=uuid.uuid4())
    assert projects == []


@pytest.mark.asyncio
async def test_project_get() -> None:
    db = AsyncMock()
    sentinel = object()
    db.get = AsyncMock(return_value=sentinel)
    repo = ProjectRepository(db)

    result = await repo.get(uuid.uuid4())
    assert result is sentinel


@pytest.mark.asyncio
async def test_project_get_not_found() -> None:
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    repo = ProjectRepository(db)

    result = await repo.get(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_project_create() -> None:
    db = _db()
    repo = ProjectRepository(db)

    payload = ProjectCreate(name="Test", gitlab_project_id="gl-1")
    project = await repo.create(payload, owner_id=uuid.uuid4())
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    assert project.name == "Test"


@pytest.mark.asyncio
async def test_project_update() -> None:
    db = _db()
    repo = ProjectRepository(db)

    project = MagicMock()
    project.name = "Old"
    payload = ProjectUpdate(name="New", priority=Priority.HIGH)

    updated = await repo.update(project, payload)
    assert updated.name == "New"
    assert updated.priority == Priority.HIGH
    db.flush.assert_awaited_once()


# ── FindingRepository ───────────────────────────────────────


@pytest.mark.asyncio
async def test_finding_list_by_session_no_filters() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalars_all(["f1", "f2"]))
    repo = FindingRepository(db)

    findings = await repo.list_by_session(uuid.uuid4())
    assert len(findings) == 2


@pytest.mark.asyncio
async def test_finding_list_by_session_all_filters() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalars_all([]))
    repo = FindingRepository(db)

    findings = await repo.list_by_session(
        uuid.uuid4(),
        severity="high",
        category="xss",
        regression_status="new",
        since=datetime(2025, 1, 1),
        until=datetime(2025, 12, 31),
    )
    assert findings == []


@pytest.mark.asyncio
async def test_finding_get() -> None:
    db = AsyncMock()
    sentinel = object()
    db.get = AsyncMock(return_value=sentinel)
    repo = FindingRepository(db)

    result = await repo.get(uuid.uuid4())
    assert result is sentinel


@pytest.mark.asyncio
async def test_finding_add_status() -> None:
    db = _db()
    repo = FindingRepository(db)

    fs = await repo.add_status(
        finding_id=uuid.uuid4(),
        changed_by=uuid.uuid4(),
        status=VerificationStatus.CONFIRMED,
        reason="verified in staging",
    )
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    assert fs.status == VerificationStatus.CONFIRMED
    assert fs.reason == "verified in staging"


@pytest.mark.asyncio
async def test_finding_add_status_no_reason() -> None:
    db = _db()
    repo = FindingRepository(db)

    fs = await repo.add_status(
        finding_id=uuid.uuid4(),
        changed_by=uuid.uuid4(),
        status=VerificationStatus.FALSE_POSITIVE,
    )
    assert fs.reason is None


@pytest.mark.asyncio
async def test_finding_get_status_history() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalars_all(["s1", "s2", "s3"]))
    repo = FindingRepository(db)

    history = await repo.get_status_history(uuid.uuid4())
    assert len(history) == 3


# ── SessionRepository ──────────────────────────────────────


@pytest.mark.asyncio
async def test_session_list_by_type() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalars_all(["s1", "s2"]))
    repo = SessionRepository(db)

    sessions = await repo.list_by_type(uuid.uuid4(), SessionType.TARGET_DISCOVERY)
    assert len(sessions) == 2
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_session_list_by_type_empty() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalars_all([]))
    repo = SessionRepository(db)

    sessions = await repo.list_by_type(uuid.uuid4(), SessionType.ZERO_DAY_HUNTING)
    assert sessions == []


@pytest.mark.asyncio
async def test_session_create_with_hunting_fields() -> None:
    db = _db()
    repo = SessionRepository(db)

    session = await repo.create(
        project_id=uuid.uuid4(),
        commit_sha="HEAD",
        agent_id=uuid.uuid4(),
        preset_id=uuid.uuid4(),
        model_version="hunting-agent-0.1.0",
        session_type=SessionType.TARGET_DISCOVERY,
        phase_data={"config": {"skill": "opentarget"}, "phases": {}},
    )
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    assert session.session_type == SessionType.TARGET_DISCOVERY
    assert session.phase_data is not None


@pytest.mark.asyncio
async def test_session_update_phase_data() -> None:
    db = _db()
    existing = MagicMock()
    existing.phase_data = {"config": {}, "phases": {}}
    db.get = AsyncMock(return_value=existing)
    repo = SessionRepository(db)

    result = await repo.update_phase_data(uuid.uuid4(), "gathering", "running")
    assert result is not None
    assert result.current_phase == "gathering"
    assert result.phase_data["phases"]["gathering"]["status"] == "running"


@pytest.mark.asyncio
async def test_session_update_phase_data_with_extra() -> None:
    db = _db()
    existing = MagicMock()
    existing.phase_data = {"config": {}, "phases": {"gathering": {"status": "done"}}}
    db.get = AsyncMock(return_value=existing)
    repo = SessionRepository(db)

    result = await repo.update_phase_data(
        uuid.uuid4(), "filtering", "running", {"progress": 50}
    )
    assert result.phase_data["phases"]["filtering"]["status"] == "running"
    assert result.phase_data["phases"]["filtering"]["progress"] == 50
    assert result.phase_data["phases"]["gathering"]["status"] == "done"


@pytest.mark.asyncio
async def test_session_update_phase_data_not_found() -> None:
    db = _db()
    db.get = AsyncMock(return_value=None)
    repo = SessionRepository(db)

    result = await repo.update_phase_data(uuid.uuid4(), "gathering", "running")
    assert result is None


@pytest.mark.asyncio
async def test_session_list_hunting_all() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalars_all(["h1", "h2", "h3"]))
    repo = SessionRepository(db)

    sessions = await repo.list_hunting()
    assert len(sessions) == 3
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_session_list_hunting_by_project() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalars_all(["h1"]))
    repo = SessionRepository(db)

    sessions = await repo.list_hunting(project_id=uuid.uuid4())
    assert len(sessions) == 1


@pytest.mark.asyncio
async def test_session_transition_sets_completed_at() -> None:
    db = _db()
    repo = SessionRepository(db)
    analysis = MagicMock()
    analysis.state = SessionState.POST_PROCESSING
    analysis.completed_at = None

    await repo.transition(analysis, SessionState.COMPLETED)
    assert analysis.state == SessionState.COMPLETED
    assert analysis.completed_at is not None


@pytest.mark.asyncio
async def test_session_transition_idempotent() -> None:
    db = _db()
    repo = SessionRepository(db)
    analysis = MagicMock()
    analysis.state = SessionState.PREPARING

    result = await repo.transition(analysis, SessionState.PREPARING)
    assert result is analysis
    db.flush.assert_not_awaited()
