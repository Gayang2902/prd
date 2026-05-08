import uuid
from typing import Any

from pydantic import BaseModel

from app.models.analysis_session import SessionPriority


class HuntingSessionCreate(BaseModel):
    project_id: uuid.UUID
    preset_id: uuid.UUID
    agent_id: uuid.UUID
    commit_sha: str | None = None
    priority: SessionPriority = SessionPriority.NORMAL
    config: dict[str, Any] = {}


class PhaseUpdate(BaseModel):
    phase: str
    status: str
    data: dict[str, Any] | None = None
