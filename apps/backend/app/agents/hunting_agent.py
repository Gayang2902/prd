"""Anthropic API 직접 호출 헌팅 에이전트 — opentarget/openresearch 스킬 실행."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from anthropic import AsyncAnthropic
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

logger = structlog.get_logger()

SKILLS_DIR = Path(os.environ.get("SKILLS_DIR", str(Path.home() / ".claude" / "skills")))
MODEL = os.environ.get("HUNTING_MODEL", "claude-sonnet-4-20250514")
MAX_TOKENS = 16384

SEVERITY_MAP: dict[str, Severity] = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.INFO,
}

SKILL_BY_TYPE: dict[str, str] = {
    "opentarget": "opentarget",
    "openresearch": "openresearch",
    "target_discovery": "opentarget",
    "zero_day_hunting": "openresearch",
}

PHASE_PROMPTS: dict[str, dict[str, str]] = {
    "target_discovery": {
        "gathering": (
            "Phase 1 실행: 병렬 후보 수집.\n"
            "Centralized MAS 패턴으로 3개 검색 경로에서 40~60개 후보를 수집.\n"
            "에코시스템별 결과를 JSON 배열로 출력."
        ),
        "filtering": (
            "Phase 2 실행: 빠른 필터링.\n"
            "수집된 후보에서 규칙 위반 항목 제거. "
            "외부 입력 없음, 비활성, 대형 프레임워크 필터.\n"
            "남은 후보 목록을 JSON으로 출력."
        ),
        "scoring": (
            "Phase 3 실행: Crackability 스코어링.\n"
            "남은 후보에 crackability 점수(1~10). "
            "네이티브 코드 가산, 보안 강화 감점, 단독 관리자 가산.\n"
            "점수순 정렬 JSON 출력."
        ),
        "shortlisting": (
            "Phase 4-6 실행: Patch-diff 분석 + 구조 분석 + 최종 선택.\n"
            "상위 후보의 최근 패치를 분석하고 퍼징 전략 수립.\n"
            "primary 1개 + backup 2개 선정.\n"
            "최종 shortlist를 JSON으로 출력."
        ),
        "complete": (
            "최종 보고서 작성. 선정된 타겟의 요약, crackability 점수, "
            "추천 퍼징 전략, 진입점을 포함한 JSON 보고서 출력."
        ),
    },
    "zero_day_hunting": {
        "setup": (
            "Phase 0 실행: 타겟 설정.\n"
            "타겟 저장소 분석, 공격 표면 식별.\n"
            "파서, 입력 처리, 네이티브 바인딩 위치를 JSON 출력."
        ),
        "fuzzing": (
            "Phase 1 실행: 병렬 퍼징.\n"
            "Centralized MAS 패턴으로 3개 Worker 동시 퍼징.\n"
            "Worker당 동시 퍼징 1개, 메모리 가드 필수.\n"
            "발견된 anomaly를 JSON 배열로 출력."
        ),
        "triage": (
            "Phase 2 실행: Anomaly 트리아지.\n"
            "퍼징 anomaly 분류: crash/leak/corruption/auth bypass.\n"
            "유효 anomaly 목록을 JSON 출력."
        ),
        "code_reading": (
            "Phase 3 실행: SAS 코드 리딩.\n"
            "트리아지된 anomaly의 루트 코즈 코드 분석.\n"
            "취약점 경로, 영향 범위, 선행 조건을 JSON 출력."
        ),
        "bypass": (
            "Phase 4 실행: 병렬 Bypass.\n"
            "방어 메커니즘 발견 시 3-agent 우회 시도.\n"
            "각 bypass 경로와 성공 여부를 JSON 출력."
        ),
        "cross_verify": (
            "Phase 5 실행: CCG 교차 검증.\n"
            "다중 관점 검증. 재현 가능성, 임팩트, severity 확정.\n"
            "검증 결과를 JSON 출력."
        ),
        "complete": (
            "Phase 6 실행: 최종 보고서.\n"
            "검증된 finding의 PoC, 임팩트, 권고사항 포함 JSON 출력."
        ),
    },
}

OUTPUT_SCHEMA = (
    "응답은 반드시 아래 JSON 형식만 출력하라. 설명 텍스트 없이 JSON만:\n"
    '{"findings": [\n'
    '  {"title": "...", "file_path": "...", "line_start": 0, "line_end": 0,\n'
    '   "severity": "critical|high|medium|low|info", "category": "...",\n'
    '   "description": "...", "code_snippet": "...", "score": 0.0}\n'
    "]}"
)


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
    resolved = SKILL_BY_TYPE.get(skill_name, skill_name)
    skill_path = SKILLS_DIR / resolved / "SKILL.md"
    if skill_path.exists():
        return skill_path.read_text()
    return ""


class HuntingAgent(BaseAgent):
    """Anthropic API 직접 호출로 opentarget/openresearch 스킬 실행."""

    def __init__(self) -> None:
        self._client: AsyncAnthropic | None = None
        self._skill_name: str = ""
        self._skill_content: str = ""

    @classmethod
    def describe(cls) -> AgentMetadata:
        return AgentMetadata(
            name="hunting-agent",
            version="1.0.0",
            supported_languages=["c", "cpp", "rust", "javascript", "typescript", "python"],
            max_input_size_bytes=500_000_000,
            cost_profile={"per_run_usd": 5.0, "model": MODEL},
            description="Anthropic API 직접 호출 — opentarget/openresearch 스킬 기반 헌팅",
        )

    async def prepare(self, context: AnalysisContext) -> None:
        self._client = AsyncAnthropic()
        hunting_config = context.preset.ruleset or {}
        self._skill_name = hunting_config.get("skill", "opentarget")
        self._skill_content = _load_skill(self._skill_name)

    async def analyze(self, context: AnalysisContext) -> AsyncIterator[LogEvent | AnalysisResult]:
        assert self._client is not None
        hunting_config = context.preset.ruleset or {}
        session_type = hunting_config.get("session_type", "target_discovery")
        phase = hunting_config.get("phase", "all")

        yield _log(f"헌팅 시작: {self._skill_name} / phase={phase}", progress=0.05)

        system_prompt = (
            f"너는 보안 연구원이다. 아래 스킬의 지침을 정확히 따라 실행하라.\n\n"
            f"{self._skill_content}"
        )

        user_prompt = self._build_user_prompt(session_type, phase, hunting_config)

        yield _log(f"Anthropic API 호출: {MODEL}", progress=0.10)

        total_tokens = 0
        all_text = ""

        try:
            response = await self._client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            all_text = response.content[0].text if response.content else ""
            total_tokens = response.usage.input_tokens + response.usage.output_tokens
        except Exception as e:
            logger.error("anthropic_api_error", error=str(e))
            yield _log(f"API 오류: {e}", progress=1.0)
            yield AnalysisResult(findings=[], tokens_used=0, cost_usd=0.0, raw_output=str(e))
            return

        yield _log("결과 파싱 중", progress=0.80, tokens=total_tokens)

        findings = _parse_findings(all_text)
        cost_usd = _estimate_cost(total_tokens)

        yield _log(f"헌팅 완료 — {len(findings)}건 발견", progress=1.0, tokens=total_tokens)
        yield AnalysisResult(
            findings=findings,
            tokens_used=total_tokens,
            cost_usd=cost_usd,
            raw_output=all_text[:50000],
        )

    async def terminate(self) -> None:
        self._client = None

    def _build_user_prompt(self, session_type: str, phase: str, config: dict) -> str:
        config_clean = {k: v for k, v in config.items() if k not in ("skill", "session_type", "phase", "previous_results")}
        config_str = json.dumps(config_clean, ensure_ascii=False) if config_clean else "{}"

        if phase == "all":
            phase_instruction = "전체 파이프라인을 Phase 0부터 순서대로 실행하라."
        else:
            phase_instruction = PHASE_PROMPTS.get(session_type, {}).get(phase, f"Phase '{phase}'를 실행하라.")

        previous = config.get("previous_results", {})
        prev_str = ""
        if previous:
            prev_str = f"\n\n<previous_results>\n{json.dumps(previous, ensure_ascii=False, default=str)[:8000]}\n</previous_results>"

        return (
            f"<config>{config_str}</config>\n"
            f"<phase>{phase}</phase>\n"
            f"{prev_str}\n\n"
            f"{phase_instruction}\n\n"
            f"{OUTPUT_SCHEMA}"
        )


def _estimate_cost(total_tokens: int) -> float:
    return round(total_tokens * 0.000015, 4)


def _parse_findings(text: str) -> list[AgentFinding]:
    import re

    data: dict[str, Any] = {}
    json_match = re.search(r"\{[\s\S]*\"findings\"[\s\S]*\}", text)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    if not data:
        try:
            data = json.loads(text)
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
