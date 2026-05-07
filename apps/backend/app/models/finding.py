import enum
import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RegressionStatus(str, enum.Enum):
    NEW = "new"
    RECURRING = "recurring"
    RESOLVED = "resolved"
    CARRIED_OVER = "carried_over"


class Finding(TimestampMixin, Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_sessions.id"), index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    file_path: Mapped[str] = mapped_column(String(1000))
    line_start: Mapped[int] = mapped_column(Integer)
    line_end: Mapped[int] = mapped_column(Integer)
    severity: Mapped[Severity]
    category: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    regression_status: Mapped[RegressionStatus] = mapped_column(
        default=RegressionStatus.NEW
    )

    session: Mapped["AnalysisSession"] = relationship(  # noqa: F821
        back_populates="findings"
    )
    statuses: Mapped[list["FindingStatus"]] = relationship(  # noqa: F821
        back_populates="finding"
    )
    comments: Mapped[list["Comment"]] = relationship(back_populates="finding")  # noqa: F821
