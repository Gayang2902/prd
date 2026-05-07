"""K8s Job provisioning — MVP-α mock implementation.

Production version will use kubernetes_asyncio to create/manage analysis Pods.
"""

import uuid

import structlog

from app.workflows.models import EnvHandle

logger = structlog.get_logger()


async def create_analysis_pod(session_id: uuid.UUID) -> EnvHandle:
    pod_name = f"securescope-analysis-{session_id.hex[:8]}"
    work_dir = f"/tmp/analysis/{session_id.hex[:8]}"
    logger.info("mock_k8s.create_pod", pod_name=pod_name)
    return EnvHandle(session_id=session_id, pod_name=pod_name, work_dir=work_dir)


async def delete_analysis_pod(env: EnvHandle) -> None:
    logger.info("mock_k8s.delete_pod", pod_name=env.pod_name)
