import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.finding import RegressionStatus, Severity
from app.models.finding_status import VerificationStatus


class FindingRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    session_id: uuid.UUID
    fingerprint: str
    file_path: str
    line_start: int
    line_end: int
    severity: Severity
    category: str
    title: str
    description: str
    regression_status: RegressionStatus
    extras: dict | None = None
    created_at: datetime


class FindingStatusUpdate(BaseModel):
    status: VerificationStatus
    reason: str | None = None


class FindingStatusRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    finding_id: uuid.UUID
    changed_by: uuid.UUID
    status: VerificationStatus
    reason: str | None
    changed_at: datetime


class CommentCreate(BaseModel):
    content: str


class CommentRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    finding_id: uuid.UUID
    author_id: uuid.UUID
    content: str
    created_at: datetime
