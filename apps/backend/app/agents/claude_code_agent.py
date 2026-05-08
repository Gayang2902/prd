"""Claude Code CLI 직접 실행 헌팅 에이전트 — 하위 프로세스로 claude 호출."""

from __future__ import annotations

import asyncio
import json
import os
import re
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

CLAUDE_CMD = os.environ.get("CLAUDE_CMD", settings.claude_cmd)

SEVERITY_MAP: dict[str, Severity] = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.INFO,
}

HUNTING_PROMPT = """\
You are a security researcher conducting {session_type} analysis.

Target: {repo_path} (commit: {commit_sha})

{phase_instruction}

Configuration:
{config_json}

Output ALL findings as a single JSON block:

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
    "code_snippet": "<relevant code>",
    "confidence": <0.0-1.0>
  }}
]}}
```

Be thorough. Report every confirmed vulnerability or finding.\
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


class ClaudeCodeAgent(BaseAgent):
    """Claude Code CLI를 하위 프로세스로 실행하여 헌팅 수행."""

    def __init__(self) -> None:
        self._repo_path: str = ""
        self._commit_sha: str = "HEAD"

    @classmethod
    def describe(cls) -> AgentMetadata:
        return AgentMetadata(
            name="claude-code",
            version="1.0.0",
            supported_languages=["c", "cpp", "rust", "javascript", "typescript", "python", "java", "go"],
            max_input_size_bytes=500_000_000,
            cost_profile={"per_run_usd": 1.0, "model": "claude-code"},
            description="Claude Code CLI 직접 실행 — 하위 쉘에서 코드 분석 및 헌팅 수행",
        )

    async def prepare(self, context: AnalysisContext) -> None:
        self._repo_path = context.scope.repo_path
        self._commit_sha = context.scope.commit_sha or "HEAD"

    async def analyze(self, context: AnalysisContext) -> AsyncIterator[LogEvent | AnalysisResult]:
        hunting_config = context.preset.ruleset or {}
        session_type = hunting_config.get("session_type", "target_discovery")
        phase = hunting_config.get("phase", "all")

        yield _log(f"Claude Code 헌팅 시작: {session_type} / phase={phase}", progress=0.05)

        phase_instruction = _get_phase_instruction(session_type, phase)
        config_clean = {k: v for k, v in hunting_config.items() if k not in ("skill", "session_type", "phase")}

        prompt = HUNTING_PROMPT.format(
            session_type=session_type,
            repo_path=self._repo_path,
            commit_sha=self._commit_sha,
            phase_instruction=phase_instruction,
            config_json=json.dumps(config_clean, ensure_ascii=False) if config_clean else "{}",
        )

        cmd = [
            CLAUDE_CMD,
            "-p", prompt,
            "--output-format", "json",
            "--max-turns", "30",
        ]

        yield _log("Claude Code 프로세스 실행 중", progress=0.10)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._repo_path if os.path.isdir(self._repo_path) else None,
            )
            stdout_bytes, stderr_bytes = await proc.communicate()
        except FileNotFoundError:
            yield _log("Claude Code CLI를 찾을 수 없음", progress=1.0)
            yield AnalysisResult(findings=[], tokens_used=0, cost_usd=0.0, raw_output="claude command not found")
            return

        if proc.returncode != 0:
            err = stderr_bytes.decode(errors="replace")
            logger.error("claude_code_failed", returncode=proc.returncode, stderr=err[:500])
            yield _log(f"Claude Code 오류 (exit {proc.returncode})", progress=1.0)
            yield AnalysisResult(findings=[], tokens_used=0, cost_usd=0.0, raw_output=err[:50000])
            return

        yield _log("결과 파싱 중", progress=0.80)

        stdout_text = stdout_bytes.decode(errors="replace")
        claude_result = _safe_json(stdout_text)
        result_text = claude_result.get("result", stdout_text)
        cost_usd = claude_result.get("cost_usd", 0.0)

        findings = _parse_findings(result_text)

        yield _log(f"헌팅 완료 — {len(findings)}건 발견", progress=1.0)
        yield AnalysisResult(
            findings=findings,
            tokens_used=0,
            cost_usd=cost_usd,
            raw_output=result_text[:50000],
        )

    async def terminate(self) -> None:
        pass


def _get_phase_instruction(session_type: str, phase: str) -> str:
    if phase == "all":
        return "Execute the full analysis pipeline from start to finish."
    instructions: dict[str, dict[str, str]] = {
        "target_discovery": {
            "gathering": "Phase 1: Gather candidate targets from package registries. Output 40-60 candidates.",
            "filtering": "Phase 2: Filter out inactive/low-risk candidates. Output filtered list.",
            "scoring": "Phase 3: Score remaining candidates by crackability (1-10).",
            "shortlisting": "Phase 4: Select primary + 2 backup targets with fuzzing strategy.",
            "complete": "Final report: summarize targets, scores, and recommended approach.",
        },
        "zero_day_hunting": {
            "setup": "Phase 0: Analyze target, identify attack surface and entry points.",
            "fuzzing": "Phase 1: Fuzz identified entry points, report anomalies.",
            "triage": "Phase 2: Triage anomalies — classify as crash/leak/corruption/bypass.",
            "code_reading": "Phase 3: Deep code reading of triaged anomalies for root cause.",
            "bypass": "Phase 4: Attempt bypass of defense mechanisms.",
            "cross_verify": "Phase 5: Cross-verify findings from multiple perspectives.",
            "complete": "Final report: PoC, impact, remediation for each finding.",
        },
    }
    return instructions.get(session_type, {}).get(phase, f"Execute phase '{phase}'.")


def _parse_findings(text: str) -> list[AgentFinding]:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    raw_json = match.group(1) if match else text

    data: dict[str, Any] = {}
    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        json_match = re.search(r'\{"findings".*\}', text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
            except (json.JSONDecodeError, TypeError):
                return []

    items = data.get("findings", data.get("results", []))
    if not isinstance(items, list):
        return []

    findings: list[AgentFinding] = []
    seen: set[str] = set()
    for raw in items:
        if not isinstance(raw, dict):
            continue
        fp = raw.get("fingerprint", "")
        file_path = raw.get("file_path", "")
        if not fp:
            fp = f"{file_path}:{raw.get('line_start', 0)}:{raw.get('title', '')}"
        if fp in seen:
            continue
        seen.add(fp)

        sev = raw.get("severity", "medium").lower()
        findings.append(AgentFinding(
            fingerprint=fp,
            file_path=file_path,
            line_start=raw.get("line_start", 0),
            line_end=raw.get("line_end", raw.get("line_start", 0)),
            severity=SEVERITY_MAP.get(sev, Severity.MEDIUM),
            category=raw.get("category", "hunting"),
            title=str(raw.get("title", ""))[:200],
            description=str(raw.get("description", ""))[:2000],
            code_snippet=str(raw.get("code_snippet", ""))[:1000],
            confidence=float(raw.get("confidence", 0.7)),
            metadata=raw.get("metadata") or {},
        ))

    return findings


def _safe_json(raw: str) -> dict[str, Any]:
    try:
        result: dict[str, Any] = json.loads(raw)
        return result
    except (json.JSONDecodeError, TypeError):
        return {}
