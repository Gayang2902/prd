import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Preset(TimestampMixin, Base):
    __tablename__ = "presets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255))
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"))
    version_sha: Mapped[str] = mapped_column(String(64))
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)

    agent: Mapped["Agent"] = relationship(back_populates="presets")  # noqa: F821
