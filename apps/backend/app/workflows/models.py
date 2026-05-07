from uuid import UUID

from pydantic import BaseModel


class EnvHandle(BaseModel):
    session_id: UUID
    pod_name: str
    work_dir: str
