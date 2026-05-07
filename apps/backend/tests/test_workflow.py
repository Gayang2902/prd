import asyncio
import uuid

import pytest
from temporalio import activity
from temporalio.client import WorkflowFailureError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app.models.analysis_session import SessionState
from app.workflows.analysis import AnalysisWorkflow
from app.workflows.models import EnvHandle
from securescope_schemas.agent_interface import (
    AgentFinding,
    AnalysisContext,
    AnalysisResult,
    CodeScope,
    PresetConfig,
    ResourceLimits,
    Severity,
)


def _make_context(session_id: uuid.UUID | None = None) -> AnalysisContext:
    sid = session_id or uuid.uuid4()
    return AnalysisContext(
        session_id=sid,
        scope=CodeScope(repo_path="/tmp/repo", commit_sha="abc123"),
        preset=PresetConfig(
            id=uuid.uuid4(),
            version_sha="v1",
            prompt_template="analyze",
            ruleset={},
        ),
        limits=ResourceLimits(max_runtime_seconds=300),
    )


def test_env_handle_model():
    sid = uuid.uuid4()
    handle = EnvHandle(
        session_id=sid,
        pod_name=f"securescope-analysis-{sid.hex[:8]}",
        work_dir=f"/tmp/analysis/{sid.hex[:8]}",
    )
    assert handle.session_id == sid
    assert handle.pod_name.startswith("securescope-analysis-")
    data = handle.model_dump()
    assert EnvHandle.model_validate(data) == handle


def _make_happy_activities(recorded_states: list[SessionState]):
    @activity.defn(name="record_session_state")
    async def mock_record(sid, state):
        recorded_states.append(SessionState(state))

    @activity.defn(name="provision_isolated_env")
    async def mock_provision(sid):
        return EnvHandle(session_id=sid, pod_name="test-pod", work_dir="/tmp/test")

    @activity.defn(name="clone_repository")
    async def mock_clone(env, scope):
        pass

    @activity.defn(name="run_agent")
    async def mock_run(env, ctx):
        return AnalysisResult(
            findings=[
                AgentFinding(
                    fingerprint="abc",
                    file_path="t.py",
                    line_start=1,
                    line_end=2,
                    severity=Severity.HIGH,
                    category="Test",
                    title="Test finding",
                    description="Test",
                    code_snippet="x=1",
                    confidence=0.9,
                )
            ],
            tokens_used=100,
            cost_usd=0.01,
            raw_output="mock",
        )

    @activity.defn(name="post_process_findings")
    async def mock_pp(sid, result):
        return 1

    @activity.defn(name="cleanup_isolated_env")
    async def mock_cleanup(env):
        pass

    return [mock_record, mock_provision, mock_clone, mock_run, mock_pp, mock_cleanup]


def test_workflow_e2e_happy_path():
    """Full workflow: PREPARING → RUNNING → POST_PROCESSING → COMPLETED."""

    async def _run():
        session_id = uuid.uuid4()
        ctx = _make_context(session_id)
        recorded: list[SessionState] = []
        activities = _make_happy_activities(recorded)

        env = await WorkflowEnvironment.start_time_skipping()
        async with Worker(
            env.client,
            task_queue="test-q",
            workflows=[AnalysisWorkflow],
            activities=activities,
        ):
            result = await asyncio.wait_for(
                env.client.execute_workflow(
                    AnalysisWorkflow.run,
                    ctx,
                    id=f"analysis-{session_id}",
                    task_queue="test-q",
                ),
                timeout=30,
            )
        await env.shutdown()

        assert result == str(session_id)
        assert recorded == [
            SessionState.PREPARING,
            SessionState.RUNNING,
            SessionState.POST_PROCESSING,
            SessionState.COMPLETED,
        ]

    asyncio.run(_run())


def test_workflow_records_failed_on_error():
    """Workflow records FAILED when an activity raises."""

    async def _run():
        session_id = uuid.uuid4()
        ctx = _make_context(session_id)
        recorded: list[SessionState] = []

        @activity.defn(name="record_session_state")
        async def mock_record(sid, state):
            recorded.append(SessionState(state))

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
            workflows=[AnalysisWorkflow],
            activities=[mock_record, mock_provision, mock_clone, mock_cleanup],
        ):
            with pytest.raises(WorkflowFailureError):
                await asyncio.wait_for(
                    env.client.execute_workflow(
                        AnalysisWorkflow.run,
                        ctx,
                        id=f"analysis-{session_id}",
                        task_queue="test-q",
                    ),
                    timeout=30,
                )
        await env.shutdown()

        assert SessionState.PREPARING in recorded
        assert SessionState.FAILED in recorded

    asyncio.run(_run())
