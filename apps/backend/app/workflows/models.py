from uuid import UUID

from pydantic import BaseModel
from securescope_schemas.agent_interface import AnalysisContext, CodeScope


class EnvHandle(BaseModel):
    session_id: UUID
    pod_name: str
    work_dir: str


class HuntingContext(BaseModel):
    session_id: UUID
    session_type: str
    agent_id: UUID | None = None
    scope: CodeScope
    analysis_context: AnalysisContext
