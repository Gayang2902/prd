import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from app.models.analysis_session import SessionPriority, SessionState, SessionType


class SessionCreate(BaseModel):
    branch: str
    commit_sha: str | None = None
    diff_base_sha: str | None = None
    preset_id: uuid.UUID
    agent_id: uuid.UUID
    priority: SessionPriority = SessionPriority.NORMAL
    session_type: SessionType = SessionType.STATIC_ANALYSIS


class SessionRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    project_id: uuid.UUID
    commit_sha: str
    agent_id: uuid.UUID
    preset_id: uuid.UUID
    model_version: str
    container_image_sha: str | None
    session_type: SessionType
    state: SessionState
    priority: SessionPriority
    current_phase: str | None
    phase_data: dict[str, Any] | None
    started_at: datetime
    completed_at: datetime | None
    token_usage: int
    cost: Decimal
