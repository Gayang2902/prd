import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.models.analysis_session import SessionState, SessionType
    from app.workflows.activities import (
        cleanup_isolated_env,
        clone_repository,
        provision_isolated_env,
        record_hunting_phase,
        record_session_state,
    )
    from app.workflows.hunting_activities import run_hunting_phase
    from app.workflows.models import EnvHandle, HuntingContext


_PHASES_BY_TYPE: dict[str, list[str]] = {
    SessionType.TARGET_DISCOVERY.value: [
        "gathering",
        "filtering",
        "scoring",
        "shortlisting",
        "complete",
    ],
    SessionType.ZERO_DAY_HUNTING.value: [
        "setup",
        "fuzzing",
        "triage",
        "code_reading",
        "bypass",
        "cross_verify",
        "complete",
    ],
}

_PHASE_TIMEOUTS: dict[str, int] = {
    "gathering": 2700,
    "filtering": 900,
    "scoring": 1200,
    "shortlisting": 1200,
    "setup": 300,
    "fuzzing": 2700,
    "triage": 600,
    "code_reading": 1800,
    "bypass": 1800,
    "cross_verify": 900,
    "complete": 600,
}


@workflow.defn(name="HuntingWorkflow")
class HuntingWorkflow:
    @workflow.run
    async def run(self, ctx: HuntingContext) -> str:
        default_retry = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=10),
            maximum_interval=timedelta(minutes=2),
        )
        short = timedelta(seconds=10)

        phases = _PHASES_BY_TYPE[ctx.session_type]
        config = ctx.analysis_context.preset.ruleset or {}
        env_handle: EnvHandle | None = None
        phase_results: dict[str, dict] = {}

        try:
            await workflow.execute_activity(
                record_session_state,
                args=[ctx.session_id, SessionState.PREPARING.value],
                start_to_close_timeout=short,
            )
            env_handle = await workflow.execute_activity(
                provision_isolated_env,
                args=[ctx.session_id],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=default_retry,
            )

            await workflow.execute_activity(
                clone_repository,
                args=[env_handle, ctx.scope],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=default_retry,
            )

            await workflow.execute_activity(
                record_session_state,
                args=[ctx.session_id, SessionState.RUNNING.value],
                start_to_close_timeout=short,
            )

            for phase in phases:
                await workflow.execute_activity(
                    record_hunting_phase,
                    args=[ctx.session_id, phase, "running"],
                    start_to_close_timeout=short,
                )

                timeout_sec = _PHASE_TIMEOUTS.get(phase, 1800)
                phase_config = {**config, "previous_results": phase_results}

                result = await workflow.execute_activity(
                    run_hunting_phase,
                    args=[
                        ctx.session_id,
                        ctx.session_type,
                        phase,
                        phase_config,
                        env_handle.work_dir,
                        str(ctx.agent_id) if ctx.agent_id else None,
                    ],
                    start_to_close_timeout=timedelta(seconds=timeout_sec),
                    heartbeat_timeout=timedelta(seconds=120),
                    retry_policy=RetryPolicy(
                        maximum_attempts=2,
                        initial_interval=timedelta(seconds=30),
                    ),
                )

                phase_results[phase] = result

                status = result.get("status", "done") if isinstance(result, dict) else "done"
                await workflow.execute_activity(
                    record_hunting_phase,
                    args=[ctx.session_id, phase, status],
                    start_to_close_timeout=short,
                )

            await workflow.execute_activity(
                record_session_state,
                args=[ctx.session_id, SessionState.POST_PROCESSING.value],
                start_to_close_timeout=short,
            )

            await _save_hunting_results(ctx, phase_results)

            await workflow.execute_activity(
                record_session_state,
                args=[ctx.session_id, SessionState.COMPLETED.value],
                start_to_close_timeout=short,
            )
            return str(ctx.session_id)

        except asyncio.CancelledError:
            await workflow.execute_activity(
                record_session_state,
                args=[ctx.session_id, SessionState.CANCELED.value],
                start_to_close_timeout=short,
            )
            raise

        except Exception:
            await workflow.execute_activity(
                record_session_state,
                args=[ctx.session_id, SessionState.FAILED.value],
                start_to_close_timeout=short,
            )
            raise

        finally:
            if env_handle is not None:
                try:
                    await workflow.execute_activity(
                        cleanup_isolated_env,
                        args=[env_handle],
                        start_to_close_timeout=timedelta(minutes=2),
                        retry_policy=RetryPolicy(maximum_attempts=5),
                    )
                except Exception:
                    workflow.logger.error("Cleanup failed", exc_info=True)


async def _save_hunting_results(ctx: HuntingContext, phase_results: dict) -> None:
    from app.workflows.hunting_activities import save_hunting_findings

    await workflow.execute_activity(
        save_hunting_findings,
        args=[ctx.session_id, ctx.session_type, phase_results],
        start_to_close_timeout=timedelta(minutes=2),
        retry_policy=RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=10),
        ),
    )
