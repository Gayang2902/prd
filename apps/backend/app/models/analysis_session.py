from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.finding import Finding
    from app.models.preset import Preset
    from app.models.project import Project


class SessionType(str, enum.Enum):
    STATIC_ANALYSIS = "static_analysis"
    TARGET_DISCOVERY = "target_discovery"
    ZERO_DAY_HUNTING = "zero_day_hunting"


class SessionPriority(str, enum.Enum):
    URGENT = "urgent"
    NORMAL = "normal"
    BACKGROUND = "background"


class SessionState(str, enum.Enum):
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    commit_sha: Mapped[str] = mapped_column(String(40))
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"))
    preset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("presets.id"))
    model_version: Mapped[str] = mapped_column(String(100))
    container_image_sha: Mapped[str | None] = mapped_column(String(100), default=None)
    session_type: Mapped[SessionType] = mapped_column(default=SessionType.STATIC_ANALYSIS)
    state: Mapped[SessionState] = mapped_column(default=SessionState.QUEUED)
    priority: Mapped[SessionPriority] = mapped_column(default=SessionPriority.NORMAL)
    current_phase: Mapped[str | None] = mapped_column(String(50), default=None)
    phase_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    token_usage: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))

    project: Mapped[Project] = relationship(back_populates="sessions")  # noqa: F821
    agent: Mapped[Agent] = relationship()  # noqa: F821
    preset: Mapped[Preset] = relationship()  # noqa: F821
    findings: Mapped[list[Finding]] = relationship(back_populates="session")  # noqa: F821
