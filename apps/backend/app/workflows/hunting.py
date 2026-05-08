import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.models.analysis_session import SessionState, SessionType
    from app.workflows.activities import (
        cleanup_isolated_env,
        clone_repository,
        post_process_hunting_findings,
        provision_isolated_env,
        record_hunting_phase,
        record_session_state,
        run_agent,
    )
    from app.workflows.models import EnvHandle, HuntingContext


@workflow.defn(name="HuntingWorkflow")
class HuntingWorkflow:
    @workflow.run
    async def run(self, ctx: HuntingContext) -> str:
        default_retry = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=10),
            maximum_interval=timedelta(minutes=2),
        )
        agent_retry = RetryPolicy(
            maximum_attempts=2,
            initial_interval=timedelta(seconds=30),
        )
        short = timedelta(seconds=10)

        phases = _PHASES_BY_TYPE[ctx.session_type]
        env_handle: EnvHandle | None = None

        try:
            await workflow.execute_activity(
                record_session_state,
                args=[ctx.session_id, SessionState.PREPARING],
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
                args=[ctx.session_id, SessionState.RUNNING],
                start_to_close_timeout=short,
            )

            for phase in phases:
                await workflow.execute_activity(
                    record_hunting_phase,
                    args=[ctx.session_id, phase, "running"],
                    start_to_close_timeout=short,
                )

                result = await workflow.execute_activity(
                    run_agent,
                    args=[env_handle, ctx.analysis_context],
                    start_to_close_timeout=timedelta(
                        seconds=ctx.analysis_context.limits.max_runtime_seconds,
                    ),
                    heartbeat_timeout=timedelta(seconds=60),
                    retry_policy=agent_retry,
                )

                await workflow.execute_activity(
                    record_hunting_phase,
                    args=[ctx.session_id, phase, "done"],
                    start_to_close_timeout=short,
                )

            await workflow.execute_activity(
                record_session_state,
                args=[ctx.session_id, SessionState.POST_PROCESSING],
                start_to_close_timeout=short,
            )
            await workflow.execute_activity(
                post_process_hunting_findings,
                args=[ctx.session_id, result, ctx.session_type],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=default_retry,
            )

            await workflow.execute_activity(
                record_session_state,
                args=[ctx.session_id, SessionState.COMPLETED],
                start_to_close_timeout=short,
            )
            return str(ctx.session_id)

        except asyncio.CancelledError:
            await workflow.execute_activity(
                record_session_state,
                args=[ctx.session_id, SessionState.CANCELED],
                start_to_close_timeout=short,
            )
            raise

        except Exception:
            await workflow.execute_activity(
                record_session_state,
                args=[ctx.session_id, SessionState.FAILED],
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
