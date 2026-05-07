import enum
import uuid
from datetime import date

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Priority(str, enum.Enum):
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class ProjectStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255))
    gitlab_project_id: Mapped[str] = mapped_column(String(255))
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    priority: Mapped[Priority] = mapped_column(default=Priority.NORMAL)
    status: Mapped[ProjectStatus] = mapped_column(default=ProjectStatus.PENDING)
    deadline: Mapped[date | None] = mapped_column(default=None)

    owner: Mapped["User"] = relationship(back_populates="projects")  # noqa: F821
    sessions: Mapped[list["AnalysisSession"]] = relationship(  # noqa: F821
        back_populates="project"
    )
