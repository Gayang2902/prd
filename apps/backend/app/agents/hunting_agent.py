"""Claude Code CLI 기반 헌팅 에이전트 — opentarget/openresearch 스킬 실행."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
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
SKILLS_DIR = Path(os.environ.get("SKILLS_DIR", str(Path.home() / ".claude" / "skills")))

SEVERITY_MAP: dict[str, Severity] = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.INFO,
}


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


def _load_skill(skill_name: str) -> str:
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    if skill_path.exists():
        return skill_path.read_text()
    return ""


def _safe_json(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


class HuntingAgent(BaseAgent):
    """헌팅 에이전트 — Claude Code가 opentarget/openresearch 스킬을 실행."""

    def __init__(self) -> None:
        self._repo_path: str = ""
        self._skill_name: str = ""
        self._skill_content: str = ""

    @classmethod
    def describe(cls) -> AgentMetadata:
        return AgentMetadata(
            name="hunting-agent",
            version="1.0.0",
            supported_languages=["c", "cpp", "rust", "javascript", "typescript", "python"],
            max_input_size_bytes=500_000_000,
            cost_profile={"per_run_usd": 5.0, "model": "claude"},
            description="Claude Code + opentarget/openresearch 스킬 기반 헌팅 에이전트",
        )

    async def prepare(self, context: AnalysisContext) -> None:
        self._repo_path = context.scope.repo_path
        hunting_config = context.preset.ruleset or {}
        self._skill_name = hunting_config.get("skill", "opentarget")
        self._skill_content = _load_skill(self._skill_name)

    async def analyze(self, context: AnalysisContext) -> AsyncIterator[LogEvent | AnalysisResult]:
        hunting_config = context.preset.ruleset or {}
        phase = hunting_config.get("phase", "all")

        yield _log(f"헌팅 시작: {self._skill_name} / phase={phase}", progress=0.05)

        prompt = self._build_prompt(phase, hunting_config)

        cmd = [
            CLAUDE_CMD,
            "-p",
            prompt,
            "--output-format",
            "json",
            "--max-turns",
            "50",
        ]

        yield _log(f"Claude Code 실행: {self._skill_name}", progress=0.10)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._repo_path if os.path.isdir(self._repo_path) else None,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()

        if proc.returncode != 0:
            err = stderr_bytes.decode(errors="replace")
            logger.error("hunting_agent_failed", returncode=proc.returncode, stderr=err[:500])
            yield _log(f"Claude Code 오류 (exit {proc.returncode})", progress=1.0)
            yield AnalysisResult(findings=[], tokens_used=0, cost_usd=0.0, raw_output=err[:5000])
            return

        yield _log("결과 파싱 중", progress=0.80)

        stdout_text = stdout_bytes.decode(errors="replace")
        claude_result = _safe_json(stdout_text)
        result_text = claude_result.get("result", stdout_text)
        cost_usd = claude_result.get("cost_usd", 0.0)

        findings = self._parse_results(result_text)

        yield _log(f"헌팅 완료 — {len(findings)}건 발견", progress=1.0)
        yield AnalysisResult(
            findings=findings,
            tokens_used=0,
            cost_usd=cost_usd,
            raw_output=result_text[:50000],
        )

    async def terminate(self) -> None:
        pass

    def _build_prompt(self, phase: str, config: dict) -> str:
        config_str = json.dumps(config, ensure_ascii=False)
        return (
            f"<skill>\n{self._skill_content}\n</skill>\n\n"
            f"<phase>{phase}</phase>\n"
            f"<config>{config_str}</config>\n\n"
            f"위 스킬을 실행하라. phase가 'all'이면 전체 파이프라인을 순서대로 수행.\n"
            "결과는 반드시 아래 JSON 형식으로 출력:\n\n"
            "```json\n"
            '{"findings": [\n'
            '  {"title": "...", "file_path": "...", "line_start": 0, "line_end": 0,\n'
            '   "severity": "critical|high|medium|low|info", "category": "...",\n'
            '   "description": "...", "code_snippet": "...", "score": 0.0,\n'
            '   "extras": {}}\n'
            "]}\n"
            "```"
        )

    def _parse_results(self, text: str) -> list[AgentFinding]:
        import re

        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if not match:
            try:
                data = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                return []
        else:
            try:
                data = json.loads(match.group(1))
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
            file_path = raw.get("file_path", raw.get("repo", ""))
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
                confidence=float(raw.get("confidence", raw.get("score", 0.7))),
                metadata=raw.get("extras", {}),
            ))

        return findings
