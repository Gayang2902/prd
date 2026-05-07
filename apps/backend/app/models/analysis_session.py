import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid


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
    state: Mapped[SessionState] = mapped_column(default=SessionState.QUEUED)
    priority: Mapped[SessionPriority] = mapped_column(default=SessionPriority.NORMAL)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    token_usage: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))

    project: Mapped["Project"] = relationship(back_populates="sessions")  # noqa: F821
    agent: Mapped["Agent"] = relationship()  # noqa: F821
    preset: Mapped["Preset"] = relationship()  # noqa: F821
    findings: Mapped[list["Finding"]] = relationship(back_populates="session")  # noqa: F821
