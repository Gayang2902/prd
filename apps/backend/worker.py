"""Temporal worker — listens on 'analysis-queue' and executes workflows/activities.

Usage:
    cd apps/backend && python worker.py
"""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from app.core.config import settings
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
from app.workflows.analysis import AnalysisWorkflow
from app.workflows.hunting import HuntingWorkflow
from app.workflows.hunting_activities import run_hunting_phase, save_hunting_findings

TASK_QUEUE = "analysis-queue"


async def main() -> None:
    client = await Client.connect(settings.temporal_host)

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[AnalysisWorkflow, HuntingWorkflow],
        activities=[
            provision_isolated_env,
            clone_repository,
            run_agent,
            post_process_findings,
            record_hunting_phase,
            post_process_hunting_findings,
            cleanup_isolated_env,
            record_session_state,
            run_hunting_phase,
            save_hunting_findings,
        ],
    )

    print(f"Worker listening on queue '{TASK_QUEUE}' (temporal: {settings.temporal_host})")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
