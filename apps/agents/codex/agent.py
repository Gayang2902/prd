import asyncio
import os
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from securescope_schemas.agent_interface import (
    AgentFinding,
    AgentMetadata,
    AnalysisContext,
    AnalysisResult,
    BaseAgent,
    LogEvent,
    LogLevel,
    Severity,
)

SEVERITY_MAP = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.INFO,
}


class CodexAgent(BaseAgent):
    def __init__(self) -> None:
        self._api_key: str | None = None
        self._process: asyncio.subprocess.Process | None = None

    @classmethod
    def describe(cls) -> AgentMetadata:
        return AgentMetadata(
            name="codex",
            version="0.1.0",
            supported_languages=["python", "javascript", "typescript", "java", "go", "rust"],
            max_input_size_bytes=500_000_000,
            cost_profile={"per_1k_input_tokens": 0.003, "per_1k_output_tokens": 0.012},
            description="Security analysis agent powered by OpenAI Codex CLI.",
        )

    async def prepare(self, context: AnalysisContext) -> None:
        self._api_key = os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            secret = context.secrets.get("OPENAI_API_KEY")
            if secret:
                self._api_key = secret.get_secret_value()

    async def analyze(self, context: AnalysisContext) -> AsyncIterator[LogEvent | AnalysisResult]:
        if not self._api_key:
            yield LogEvent(
                timestamp=datetime.now(timezone.utc),
                level=LogLevel.ERROR,
                message="OPENAI_API_KEY not configured. Cannot run Codex agent.",
            )
            yield AnalysisResult(findings=[], tokens_used=0, cost_usd=0.0, raw_output="No API key")
            return

        yield LogEvent(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            message="Starting Codex security analysis",
            progress=0.0,
        )

        prompt = context.preset.prompt_template or (
            "Perform a thorough security review of this codebase. "
            "For each vulnerability found, output a JSON object with fields: "
            "file_path, line_start, line_end, severity (critical/high/medium/low/info), "
            "category, title, description, code_snippet, suggested_fix, confidence (0-1)."
        )

        try:
            env = {**os.environ, "OPENAI_API_KEY": self._api_key}
            self._process = await asyncio.create_subprocess_exec(
                "codex", "--prompt", prompt,
                "--output-format", "json",
                cwd=context.scope.repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            yield LogEvent(
                timestamp=datetime.now(timezone.utc),
                level=LogLevel.INFO,
                message="Codex process started",
                progress=0.1,
            )

            stdout, stderr = await asyncio.wait_for(
                self._process.communicate(),
                timeout=context.limits.max_runtime_seconds,
            )

            yield LogEvent(
                timestamp=datetime.now(timezone.utc),
                level=LogLevel.INFO,
                message="Codex analysis completed",
                progress=0.9,
            )

            raw = stdout.decode("utf-8", errors="replace")
            findings = self._parse_findings(raw)

            yield AnalysisResult(
                findings=findings,
                tokens_used=0,
                cost_usd=0.0,
                raw_output=raw[:50000],
            )

        except asyncio.TimeoutError:
            if self._process:
                self._process.kill()
            yield LogEvent(
                timestamp=datetime.now(timezone.utc),
                level=LogLevel.ERROR,
                message=f"Codex timed out after {context.limits.max_runtime_seconds}s",
            )
            yield AnalysisResult(findings=[], tokens_used=0, cost_usd=0.0, raw_output="timeout")

        except FileNotFoundError:
            yield LogEvent(
                timestamp=datetime.now(timezone.utc),
                level=LogLevel.ERROR,
                message="codex CLI not found. Install with: npm install -g @openai/codex",
            )
            yield AnalysisResult(findings=[], tokens_used=0, cost_usd=0.0, raw_output="CLI not found")

    async def terminate(self) -> None:
        if self._process and self._process.returncode is None:
            self._process.kill()

    @staticmethod
    def _parse_findings(raw: str) -> list[AgentFinding]:
        import hashlib
        import json

        findings: list[AgentFinding] = []
        try:
            data = json.loads(raw)
            items = data if isinstance(data, list) else data.get("findings", [])
        except (json.JSONDecodeError, AttributeError):
            return findings

        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                fp = hashlib.sha256(
                    f"{item.get('file_path', '')}{item.get('code_snippet', '')}{item.get('category', '')}".encode()
                ).hexdigest()[:16]
                findings.append(AgentFinding(
                    fingerprint=fp,
                    file_path=item.get("file_path", "unknown"),
                    line_start=int(item.get("line_start", 1)),
                    line_end=int(item.get("line_end", 1)),
                    severity=SEVERITY_MAP.get(item.get("severity", "info"), Severity.INFO),
                    category=item.get("category", "Unknown"),
                    title=item.get("title", "Untitled finding"),
                    description=item.get("description", ""),
                    code_snippet=item.get("code_snippet", ""),
                    suggested_fix=item.get("suggested_fix"),
                    confidence=float(item.get("confidence", 0.5)),
                ))
            except (ValueError, TypeError):
                continue

        return findings
