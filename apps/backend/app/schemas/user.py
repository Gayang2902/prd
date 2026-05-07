import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.user import Role


class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    name: str
    role: Role
    created_at: datetime
