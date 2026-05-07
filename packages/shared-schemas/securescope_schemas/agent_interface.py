from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AgentMetadata(BaseModel):
    name: str
    version: str
    supported_languages: list[str]
    max_input_size_bytes: int
    cost_profile: dict
    description: str


class CodeScope(BaseModel):
    repo_path: str
    commit_sha: str
    diff_base_sha: Optional[str] = None
    include_paths: list[str] = Field(default_factory=list)
    exclude_paths: list[str] = Field(default_factory=list)


class PresetConfig(BaseModel):
    id: UUID
    version_sha: str
    prompt_template: str
    ruleset: dict
    timeout_seconds: int = 1800
    max_retries: int = 3


class ResourceLimits(BaseModel):
    max_runtime_seconds: int = 1800
    max_tokens: int = 1_000_000
    max_cost_usd: float = 50.0


class AnalysisContext(BaseModel):
    session_id: UUID
    scope: CodeScope
    preset: PresetConfig
    limits: ResourceLimits
    secrets: dict[str, SecretStr] = Field(default_factory=dict)


class AgentFinding(BaseModel):
    fingerprint: str
    file_path: str
    line_start: int
    line_end: int
    severity: Severity
    category: str
    title: str
    description: str
    code_snippet: str
    suggested_fix: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict = Field(default_factory=dict)


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class LogEvent(BaseModel):
    timestamp: datetime
    level: LogLevel
    message: str
    progress: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    tokens_used: Optional[int] = None


class AnalysisResult(BaseModel):
    findings: list[AgentFinding]
    tokens_used: int
    cost_usd: float
    raw_output: str


class BaseAgent(ABC):
    @classmethod
    @abstractmethod
    def describe(cls) -> AgentMetadata: ...

    @abstractmethod
    async def prepare(self, context: AnalysisContext) -> None: ...

    @abstractmethod
    def analyze(self, context: AnalysisContext) -> AsyncIterator[LogEvent | AnalysisResult]: ...

    @abstractmethod
    async def terminate(self) -> None: ...
