import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.project import Priority, ProjectStatus


class ProjectCreate(BaseModel):
    name: str
    gitlab_project_id: str
    priority: Priority = Priority.NORMAL
    deadline: date | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    priority: Priority | None = None
    status: ProjectStatus | None = None
    deadline: date | None = None


class ProjectRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    gitlab_project_id: str
    owner_id: uuid.UUID
    priority: Priority
    status: ProjectStatus
    deadline: date | None
    created_at: datetime
    updated_at: datetime
