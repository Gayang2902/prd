import enum
import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Role(str, enum.Enum):
    ADMIN = "admin"
    LEAD = "lead"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(default=Role.VIEWER)

    projects: Mapped[list["Project"]] = relationship(back_populates="owner")  # noqa: F821
