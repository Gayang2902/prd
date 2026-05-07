import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.models.analysis_session import SessionState
    from app.workflows.activities import (
        cleanup_isolated_env,
        clone_repository,
        post_process_findings,
        provision_isolated_env,
        record_session_state,
        run_agent,
    )
    from app.workflows.models import EnvHandle
    from securescope_schemas.agent_interface import AnalysisContext


@workflow.defn(name="AnalysisWorkflow")
class AnalysisWorkflow:
    @workflow.run
    async def run(self, ctx: AnalysisContext) -> str:
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
            result = await workflow.execute_activity(
                run_agent,
                args=[env_handle, ctx],
                start_to_close_timeout=timedelta(seconds=ctx.limits.max_runtime_seconds),
                heartbeat_timeout=timedelta(seconds=60),
                retry_policy=agent_retry,
            )

            await workflow.execute_activity(
                record_session_state,
                args=[ctx.session_id, SessionState.POST_PROCESSING],
                start_to_close_timeout=short,
            )
            await workflow.execute_activity(
                post_process_findings,
                args=[ctx.session_id, result],
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
