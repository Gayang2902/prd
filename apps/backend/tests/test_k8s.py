"""Tests for K8s mock service."""

import uuid

from app.services.k8s import create_analysis_pod, delete_analysis_pod
from app.workflows.models import EnvHandle


async def test_create_analysis_pod() -> None:
    sid = uuid.uuid4()
    handle = await create_analysis_pod(sid)
    assert isinstance(handle, EnvHandle)
    assert handle.session_id == sid
    assert sid.hex[:8] in handle.pod_name
    assert sid.hex[:8] in handle.work_dir


async def test_delete_analysis_pod() -> None:
    handle = EnvHandle(session_id=uuid.uuid4(), pod_name="test-pod", work_dir="/tmp/test")
    await delete_analysis_pod(handle)
