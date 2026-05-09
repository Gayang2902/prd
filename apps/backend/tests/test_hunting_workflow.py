"""Tests for HuntingWorkflow and hunting activities."""

import asyncio
import uuid

import pytest
from securescope_schemas.agent_interface import (
    AnalysisContext,
    CodeScope,
    PresetConfig,
    ResourceLimits,
)
from temporalio import activity
from temporalio.client import WorkflowFailureError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app.models.analysis_session import SessionState
from app.workflows.hunting import HuntingWorkflow
from app.workflows.models import EnvHandle, HuntingContext


def _make_hunting_context(
    session_id: uuid.UUID | None = None,
    session_type: str = "target_discovery",
) -> HuntingContext:
    sid = session_id or uuid.uuid4()
    return HuntingContext(
        session_id=sid,
        session_type=session_type,
        scope=CodeScope(repo_path="/tmp/repo", commit_sha="abc123"),
        analysis_context=AnalysisContext(
            session_id=sid,
            scope=CodeScope(repo_path="/tmp/repo", commit_sha="abc123"),
            preset=PresetConfig(
                id=uuid.uuid4(),
                version_sha="v1",
                prompt_template="hunting",
                ruleset={"skill": "opentarget"},
            ),
            limits=ResourceLimits(),
        ),
    )


def _make_hunting_activities(recorded_states, recorded_phases):
    @activity.defn(name="record_session_state")
    async def mock_record(sid, state):
        recorded_states.append(SessionState(state))

    @activity.defn(name="record_hunting_phase")
    async def mock_phase(sid, phase, status):
        recorded_phases.append((phase, status))

    @activity.defn(name="provision_isolated_env")
    async def mock_provision(sid):
        return EnvHandle(session_id=sid, pod_name="test-pod", work_dir="/tmp/test")

    @activity.defn(name="clone_repository")
    async def mock_clone(env, scope):
        pass

    @activity.defn(name="run_hunting_phase")
    async def mock_run_phase(sid, stype, phase, config, work_dir, agent_id=None):
        return {"phase": phase, "status": "done", "results": [{"name": f"target-{phase}"}]}

    @activity.defn(name="save_hunting_findings")
    async def mock_save(sid, stype, results):
        return len(results)

    @activity.defn(name="cleanup_isolated_env")
    async def mock_cleanup(env):
        pass

    return [
        mock_record,
        mock_phase,
        mock_provision,
        mock_clone,
        mock_run_phase,
        mock_save,
        mock_cleanup,
    ]


def test_hunting_workflow_target_discovery():
    """Full target discovery: PREPARING → RUNNING → phases → POST_PROCESSING → COMPLETED."""

    async def _run():
        session_id = uuid.uuid4()
        ctx = _make_hunting_context(session_id, "target_discovery")
        recorded_states: list[SessionState] = []
        recorded_phases: list[tuple[str, str]] = []
        activities = _make_hunting_activities(recorded_states, recorded_phases)

        env = await WorkflowEnvironment.start_time_skipping()
        async with Worker(
            env.client,
            task_queue="test-q",
            workflows=[HuntingWorkflow],
            activities=activities,
        ):
            result = await asyncio.wait_for(
                env.client.execute_workflow(
                    HuntingWorkflow.run,
                    ctx,
                    id=f"hunting-{session_id}",
                    task_queue="test-q",
                ),
                timeout=30,
            )
        await env.shutdown()

        assert result == str(session_id)
        assert recorded_states == [
            SessionState.PREPARING,
            SessionState.RUNNING,
            SessionState.POST_PROCESSING,
            SessionState.COMPLETED,
        ]
        phase_names = [p for p, _ in recorded_phases]
        assert "gathering" in phase_names
        assert "complete" in phase_names

    asyncio.run(_run())


def test_hunting_workflow_zero_day():
    """Full zero-day hunting workflow."""

    async def _run():
        session_id = uuid.uuid4()
        ctx = _make_hunting_context(session_id, "zero_day_hunting")
        recorded_states: list[SessionState] = []
        recorded_phases: list[tuple[str, str]] = []
        activities = _make_hunting_activities(recorded_states, recorded_phases)

        env = await WorkflowEnvironment.start_time_skipping()
        async with Worker(
            env.client,
            task_queue="test-q",
            workflows=[HuntingWorkflow],
            activities=activities,
        ):
            result = await asyncio.wait_for(
                env.client.execute_workflow(
                    HuntingWorkflow.run,
                    ctx,
                    id=f"hunting-{session_id}",
                    task_queue="test-q",
                ),
                timeout=30,
            )
        await env.shutdown()

        assert result == str(session_id)
        assert SessionState.COMPLETED in recorded_states
        phase_names = [p for p, _ in recorded_phases]
        assert "fuzzing" in phase_names
        assert "cross_verify" in phase_names

    asyncio.run(_run())


def test_hunting_workflow_failure():
    """Workflow records FAILED when a phase raises."""

    async def _run():
        session_id = uuid.uuid4()
        ctx = _make_hunting_context(session_id, "target_discovery")
        recorded_states: list[SessionState] = []
        recorded_phases: list[tuple[str, str]] = []

        @activity.defn(name="record_session_state")
        async def mock_record(sid, state):
            recorded_states.append(SessionState(state))

        @activity.defn(name="record_hunting_phase")
        async def mock_phase(sid, phase, status):
            recorded_phases.append((phase, status))

        @activity.defn(name="provision_isolated_env")
        async def mock_provision(sid):
            return EnvHandle(session_id=sid, pod_name="test-pod", work_dir="/tmp/test")

        @activity.defn(name="clone_repository")
        async def mock_clone(env, scope):
            raise RuntimeError("Clone failed")

        @activity.defn(name="cleanup_isolated_env")
        async def mock_cleanup(env):
            pass

        env = await WorkflowEnvironment.start_time_skipping()
        async with Worker(
            env.client,
            task_queue="test-q",
            workflows=[HuntingWorkflow],
            activities=[mock_record, mock_phase, mock_provision, mock_clone, mock_cleanup],
        ):
            with pytest.raises(WorkflowFailureError):
                await asyncio.wait_for(
                    env.client.execute_workflow(
                        HuntingWorkflow.run,
                        ctx,
                        id=f"hunting-{session_id}",
                        task_queue="test-q",
                    ),
                    timeout=30,
                )
        await env.shutdown()

        assert SessionState.FAILED in recorded_states

    asyncio.run(_run())
