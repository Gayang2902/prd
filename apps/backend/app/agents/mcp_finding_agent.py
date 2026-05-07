"""Claude Code CLI 기반 취약점 분석 에이전트 — finding-mcp를 MCP 서버로 활용."""

from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import structlog
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

from app.core.config import settings

logger = structlog.get_logger()

FINDING_MCP_CMD = os.environ.get("FINDING_MCP_CMD", settings.finding_mcp_cmd)
CLAUDE_CMD = os.environ.get("CLAUDE_CMD", settings.claude_cmd)

SEVERITY_MAP: dict[str, Severity] = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.INFO,
}

ANALYSIS_PROMPT = """\
You are a security analyst. Use the finding-mcp tools to thoroughly analyze \
the repository at {repo_path} for vulnerabilities.

Steps:
1. get_repo_info — understand the codebase
2. list_entry_points — find user-facing entry points
3. list_dangerous_sinks — find dangerous sinks (exec, query, eval, etc.)
4. run_taint_analysis — run Semgrep taint analysis, then get_taint_paths / \
get_taint_path_detail for each finding
5. trace_call_chain — trace data flows from entry points to dangerous sinks
6. check_auth_coverage — find unprotected routes

After analysis, output ALL findings as a single JSON block:

```json
{{"findings": [
  {{
    "fingerprint": "<unique-id>",
    "file_path": "<path>",
    "line_start": <int>,
    "line_end": <int>,
    "severity": "critical|high|medium|low|info",
    "category": "<category>",
    "title": "<short title>",
    "description": "<detail>",
    "code_snippet": "<code>",
    "confidence": <0.0-1.0>
  }}
]}}
```

Be thorough. Report every confirmed vulnerability.\
"""


def _now() -> datetime:
    return datetime.now(UTC)


def _log(msg: str, progress: float | None = None, tokens: int | None = None) -> LogEvent:
    return LogEvent(
        timestamp=_now(),
        level=LogLevel.INFO,
        message=msg,
        progress=progress,
        tokens_used=tokens,
    )


def _map_severity(raw: str) -> Severity:
    return SEVERITY_MAP.get(raw.lower(), Severity.MEDIUM)


def _parse_findings_json(text: str) -> list[dict[str, Any]]:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not match:
        return []
    try:
        data: dict[str, Any] = json.loads(match.group(1))
        items = data.get("findings", [])
        if isinstance(items, list):
            return items
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _raw_to_finding(raw: dict[str, Any]) -> AgentFinding | None:
    fp = raw.get("fingerprint", "")
    file_path = raw.get("file_path", "")
    if not fp and not file_path:
        return None
    return AgentFinding(
        fingerprint=fp or f"{file_path}:{raw.get('line_start', 0)}",
        file_path=file_path,
        line_start=raw.get("line_start", 1),
        line_end=raw.get("line_end", raw.get("line_start", 1)),
        severity=_map_severity(raw.get("severity", "medium")),
        category=raw.get("category", "unknown"),
        title=str(raw.get("title", ""))[:200],
        description=str(raw.get("description", ""))[:2000],
        code_snippet=str(raw.get("code_snippet", ""))[:1000],
        confidence=float(raw.get("confidence", 0.7)),
        metadata=raw.get("metadata") or {},
    )


class McpFindingAgent(BaseAgent):
    """취약점 분석 에이전트 — Claude Code가 finding-mcp 도구를 자율적으로 활용."""

    def __init__(self) -> None:
        self._mcp_config_path: str | None = None
        self._repo_path: str = ""

    @classmethod
    def describe(cls) -> AgentMetadata:
        return AgentMetadata(
            name="mcp-finding-agent",
            version="0.2.0",
            supported_languages=["java", "php", "javascript", "typescript"],
            max_input_size_bytes=500_000_000,
            cost_profile={"per_run_usd": 0.05, "model": "claude"},
            description=(
                "Claude Code + finding-mcp 기반 자율 분석 에이전트"
                " — 코드베이스를 탐색하고 취약점을 자동 발견"
            ),
        )

    async def prepare(self, context: AnalysisContext) -> None:
        self._repo_path = context.scope.repo_path
        config = {
            "mcpServers": {
                "finding-mcp": {
                    "command": FINDING_MCP_CMD,
                    "args": [self._repo_path],
                }
            }
        }
        fd, path = tempfile.mkstemp(suffix=".json", prefix="mcp_config_")
        with os.fdopen(fd, "w") as f:
            json.dump(config, f)
        self._mcp_config_path = path

    async def analyze(self, context: AnalysisContext) -> AsyncIterator[LogEvent | AnalysisResult]:
        assert self._mcp_config_path is not None

        yield _log("Claude Code 분석 시작", progress=0.05)

        prompt = ANALYSIS_PROMPT.format(repo_path=self._repo_path)
        cmd = [
            CLAUDE_CMD,
            "-p",
            prompt,
            "--output-format",
            "json",
            "--mcp-config",
            self._mcp_config_path,
            "--max-turns",
            "50",
        ]

        yield _log("Claude Code 실행 중", progress=0.10)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._repo_path,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()

        if proc.returncode != 0:
            err = stderr_bytes.decode(errors="replace")
            logger.error("claude_code_failed", returncode=proc.returncode, stderr=err)
            yield _log(f"Claude Code 오류 (exit {proc.returncode})", progress=1.0)
            yield AnalysisResult(findings=[], tokens_used=0, cost_usd=0.0, raw_output=err)
            return

        yield _log("Claude Code 응답 파싱 중", progress=0.80)

        stdout_text = stdout_bytes.decode(errors="replace")
        claude_result = _safe_json(stdout_text)
        result_text = claude_result.get("result", stdout_text)
        cost_usd = claude_result.get("cost_usd", 0.0)

        raw_findings = _parse_findings_json(result_text)
        findings: list[AgentFinding] = []
        seen: set[str] = set()
        for raw in raw_findings:
            af = _raw_to_finding(raw)
            if af and af.fingerprint not in seen:
                seen.add(af.fingerprint)
                findings.append(af)

        yield _log(
            f"분석 완료 — 총 {len(findings)}건 취약점 발견",
            progress=1.0,
        )

        yield AnalysisResult(
            findings=findings,
            tokens_used=0,
            cost_usd=cost_usd,
            raw_output=result_text[:50000],
        )

    async def terminate(self) -> None:
        if self._mcp_config_path and os.path.exists(self._mcp_config_path):
            os.unlink(self._mcp_config_path)
            self._mcp_config_path = None


# ── Helper ─────────────────────────────────────────────────


def _safe_json(raw: str) -> dict[str, Any]:
    try:
        result: dict[str, Any] = json.loads(raw)
        return result
    except (json.JSONDecodeError, TypeError):
        return {}
