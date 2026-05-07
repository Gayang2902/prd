import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid


class VerificationStatus(str, enum.Enum):
    OPEN = "open"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    NEEDS_REVIEW = "needs_review"


class FindingStatus(Base):
    """Append-only 검증 상태 이력. 마지막 행이 현재 상태."""

    __tablename__ = "finding_statuses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    finding_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("findings.id"), index=True)
    changed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[VerificationStatus]
    reason: Mapped[str | None] = mapped_column(Text, default=None)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    finding: Mapped["Finding"] = relationship(back_populates="statuses")  # noqa: F821
    user: Mapped["User"] = relationship()  # noqa: F821
