from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.agent import Agent


class Preset(TimestampMixin, Base):
    __tablename__ = "presets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255))
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"))
    version_sha: Mapped[str] = mapped_column(String(64))
    prompt_template: Mapped[str] = mapped_column(Text, default="")
    ruleset: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=1800)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)

    agent: Mapped[Agent] = relationship(back_populates="presets")  # noqa: F821
