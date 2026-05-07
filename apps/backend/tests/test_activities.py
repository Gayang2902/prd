"""Tests for Temporal workflow activities."""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from securescope_schemas.agent_interface import (
    AnalysisContext,
    AnalysisResult,
    CodeScope,
    LogEvent,
    LogLevel,
    PresetConfig,
    ResourceLimits,
)

from app.models.analysis_session import SessionState
from app.workflows.activities import (
    ResourceLimitExceededError,
    cleanup_isolated_env,
    clone_repository,
    provision_isolated_env,
    record_session_state,
    run_agent,
)
from app.workflows.models import EnvHandle


def _env(sid: uuid.UUID | None = None) -> EnvHandle:
    return EnvHandle(
        session_id=sid or uuid.uuid4(),
        pod_name="test-pod",
        work_dir="/tmp/work",
    )


def _scope() -> CodeScope:
    return CodeScope(
        repo_path="https://git.example.com/repo.git",
        commit_sha="abc123",
        paths=["src/"],
    )


def _limits(**overrides: object) -> ResourceLimits:
    defaults: dict = {"max_runtime_seconds": 1800, "max_tokens": 1_000_000, "max_cost_usd": 50.0}
    defaults.update(overrides)
    return ResourceLimits(**defaults)


def _context(**overrides: object) -> AnalysisContext:
    defaults: dict = {
        "session_id": uuid.uuid4(),
        "scope": _scope(),
        "preset": PresetConfig(
            id=uuid.uuid4(),
            version_sha="abc123",
            prompt_template="analyze {file}",
            ruleset={"rules": []},
        ),
        "limits": _limits(),
    }
    defaults.update(overrides)
    return AnalysisContext(**defaults)


@pytest.mark.asyncio
@patch("app.workflows.activities.activity")
@patch("app.services.k8s.create_analysis_pod")
async def test_provision_isolated_env(mock_create: AsyncMock, mock_activity: MagicMock) -> None:
    sid = uuid.uuid4()
    expected = _env(sid)
    mock_create.return_value = expected

    result = await provision_isolated_env(sid)
    assert result == expected
    mock_create.assert_awaited_once_with(sid)


@pytest.mark.asyncio
@patch("app.workflows.activities.activity")
async def test_clone_repository(mock_activity: MagicMock) -> None:
    env = _env()
    scope = _scope()
    await clone_repository(env, scope)
    mock_activity.logger.info.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.activities.activity")
@patch("app.services.k8s.delete_analysis_pod")
async def test_cleanup_isolated_env(mock_delete: AsyncMock, mock_activity: MagicMock) -> None:
    env = _env()
    await cleanup_isolated_env(env)
    mock_delete.assert_awaited_once_with(env)


@pytest.mark.asyncio
@patch("app.workflows.activities.activity")
async def test_run_agent_happy_path(mock_activity: MagicMock) -> None:
    ctx = _context()
    findings_result = AnalysisResult(findings=[], tokens_used=100, cost_usd=1.0, raw_output="ok")

    mock_agent = AsyncMock()

    async def fake_analyze(_ctx: object):  # noqa: ANN202
        yield LogEvent(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            message="step",
            progress=0.5,
            tokens_used=50,
        )
        yield findings_result

    mock_agent.analyze = fake_analyze
    mock_agent_cls = MagicMock(return_value=mock_agent)

    with patch("app.services.agent_registry.get_registry", return_value={"test": mock_agent_cls}):
        result = await run_agent(_env(), ctx)

    assert result == findings_result
    mock_agent.prepare.assert_awaited_once()
    mock_agent.terminate.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.workflows.activities.activity")
async def test_run_agent_no_agents_registered(mock_activity: MagicMock) -> None:
    ctx = _context()
    with (
        patch("app.services.agent_registry.get_registry", return_value={}),
        pytest.raises(RuntimeError, match="No agents registered"),
    ):
        await run_agent(_env(), ctx)


@pytest.mark.asyncio
@patch("app.workflows.activities.activity")
async def test_run_agent_no_result(mock_activity: MagicMock) -> None:
    ctx = _context()
    mock_agent = AsyncMock()

    async def empty_analyze(_ctx: object):  # noqa: ANN202
        yield LogEvent(
            timestamp=datetime.now(), level=LogLevel.INFO, message="done", progress=1.0
        )

    mock_agent.analyze = empty_analyze
    mock_agent_cls = MagicMock(return_value=mock_agent)

    with (
        patch("app.services.agent_registry.get_registry", return_value={"a": mock_agent_cls}),
        pytest.raises(RuntimeError, match="did not produce a result"),
    ):
        await run_agent(_env(), ctx)


@pytest.mark.asyncio
@patch("app.workflows.activities.activity")
@patch("app.workflows.activities.time")
async def test_run_agent_runtime_limit(mock_time: MagicMock, mock_activity: MagicMock) -> None:
    ctx = _context(limits=_limits(max_runtime_seconds=10))
    mock_time.monotonic.side_effect = [0.0, 20.0]

    mock_agent = AsyncMock()

    async def slow_analyze(_ctx: object):  # noqa: ANN202
        yield LogEvent(
            timestamp=datetime.now(), level=LogLevel.INFO, message="tick", progress=0.1
        )

    mock_agent.analyze = slow_analyze
    mock_agent_cls = MagicMock(return_value=mock_agent)

    with (
        patch("app.services.agent_registry.get_registry", return_value={"a": mock_agent_cls}),
        pytest.raises(ResourceLimitExceededError, match="Runtime limit"),
    ):
        await run_agent(_env(), ctx)
    mock_agent.terminate.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.workflows.activities.activity")
@patch("app.workflows.activities.time")
async def test_run_agent_token_limit(mock_time: MagicMock, mock_activity: MagicMock) -> None:
    ctx = _context(limits=_limits(max_tokens=100))
    mock_time.monotonic.side_effect = [0.0, 1.0]

    mock_agent = AsyncMock()

    async def greedy_analyze(_ctx: object):  # noqa: ANN202
        yield LogEvent(
            timestamp=datetime.now(), level=LogLevel.INFO, message="big", tokens_used=200
        )

    mock_agent.analyze = greedy_analyze
    mock_agent_cls = MagicMock(return_value=mock_agent)

    with (
        patch("app.services.agent_registry.get_registry", return_value={"a": mock_agent_cls}),
        pytest.raises(ResourceLimitExceededError, match="Token limit"),
    ):
        await run_agent(_env(), ctx)
    mock_agent.terminate.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.workflows.activities.activity")
@patch("app.workflows.activities.time")
async def test_run_agent_cost_warning(mock_time: MagicMock, mock_activity: MagicMock) -> None:
    ctx = _context(limits=_limits(max_cost_usd=1.0))
    mock_time.monotonic.side_effect = [0.0, 1.0]

    expensive_result = AnalysisResult(findings=[], tokens_used=100, cost_usd=99.0, raw_output="ok")
    mock_agent = AsyncMock()

    async def costly_analyze(_ctx: object):  # noqa: ANN202
        yield expensive_result

    mock_agent.analyze = costly_analyze
    mock_agent_cls = MagicMock(return_value=mock_agent)

    with patch("app.services.agent_registry.get_registry", return_value={"a": mock_agent_cls}):
        result = await run_agent(_env(), ctx)

    assert result.cost_usd == 99.0
    mock_activity.logger.warn.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.activities.activity")
async def test_record_session_state(mock_activity: MagicMock) -> None:
    sid = uuid.uuid4()
    mock_analysis = MagicMock()
    mock_repo = AsyncMock()
    mock_repo.get = AsyncMock(return_value=mock_analysis)
    mock_repo.transition = AsyncMock(return_value=mock_analysis)

    mock_db = AsyncMock()

    @asynccontextmanager
    async def fake_factory():  # noqa: ANN202
        yield mock_db

    with (
        patch("app.core.database.async_session_factory", fake_factory),
        patch(
            "app.services.repositories.session.SessionRepository",
            return_value=mock_repo,
        ),
    ):
        await record_session_state(sid, SessionState.RUNNING)

    mock_repo.get.assert_awaited_once_with(sid)
    mock_repo.transition.assert_awaited_once_with(mock_analysis, SessionState.RUNNING)
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.workflows.activities.activity")
async def test_record_session_state_not_found(mock_activity: MagicMock) -> None:
    mock_repo = AsyncMock()
    mock_repo.get = AsyncMock(return_value=None)

    mock_db = AsyncMock()

    @asynccontextmanager
    async def fake_factory():  # noqa: ANN202
        yield mock_db

    with (
        patch("app.core.database.async_session_factory", fake_factory),
        patch(
            "app.services.repositories.session.SessionRepository",
            return_value=mock_repo,
        ),
        pytest.raises(RuntimeError, match="not found"),
    ):
        await record_session_state(uuid.uuid4(), SessionState.FAILED)
