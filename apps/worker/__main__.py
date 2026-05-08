import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from app.workflows.analysis import AnalysisWorkflow
from app.workflows.hunting import HuntingWorkflow
from app.workflows.activities import (
    cleanup_isolated_env,
    clone_repository,
    post_process_findings,
    post_process_hunting_findings,
    provision_isolated_env,
    record_hunting_phase,
    record_session_state,
    run_agent,
)

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")
TASK_QUEUE = "analysis-queue"


async def main() -> None:
    client = await Client.connect(TEMPORAL_HOST)
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[AnalysisWorkflow, HuntingWorkflow],
        activities=[
            provision_isolated_env,
            clone_repository,
            run_agent,
            post_process_findings,
            post_process_hunting_findings,
            cleanup_isolated_env,
            record_session_state,
            record_hunting_phase,
        ],
    )
    print(f"Worker started on queue={TASK_QUEUE}, temporal={TEMPORAL_HOST}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
