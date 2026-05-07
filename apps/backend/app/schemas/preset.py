import uuid
from datetime import datetime

from pydantic import BaseModel


class PresetCreate(BaseModel):
    name: str
    agent_id: uuid.UUID
    version_sha: str
    prompt_template: str = ""
    ruleset: dict = {}
    timeout_seconds: int = 1800
    max_retries: int = 3
    is_shared: bool = False


class PresetUpdate(BaseModel):
    name: str | None = None
    prompt_template: str | None = None
    ruleset: dict | None = None
    timeout_seconds: int | None = None
    max_retries: int | None = None
    is_shared: bool | None = None


class PresetRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    agent_id: uuid.UUID
    version_sha: str
    prompt_template: str
    ruleset: dict
    timeout_seconds: int
    max_retries: int
    is_shared: bool
    created_at: datetime
    updated_at: datetime
