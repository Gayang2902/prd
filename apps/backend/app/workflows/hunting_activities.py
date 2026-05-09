import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from temporalio import activity

from app.core.config import settings

logger = structlog.get_logger()

SKILLS_DIR = Path(os.environ.get("SKILLS_DIR", str(Path.home() / ".claude" / "skills")))
CLAUDE_CMD = os.environ.get("CLAUDE_CMD", settings.claude_cmd)

SKILL_BY_TYPE: dict[str, str] = {
    "target_discovery": "opentarget",
    "zero_day_hunting": "openresearch",
}

PHASE_PROMPTS: dict[str, dict[str, str]] = {
    "target_discovery": {
        "gathering": (
            "Phase 1: 병렬 후보 수집. 3개 검색 경로에서 40~60개 후보 수집." " JSON 배열 출력."
        ),
        "filtering": "Phase 2: 빠른 필터링. 규칙 위반 항목 제거. 남은 후보 JSON 출력.",
        "scoring": "Phase 3: Crackability 스코어링(1~10). 점수순 정렬 JSON 출력.",
        "shortlisting": (
            "Phase 4-6: Patch-diff + 구조 분석 + 최종 선택."
            " primary 1 + backup 2 선정. JSON 출력."
        ),
        "complete": "최종 보고서. 타겟 요약, crackability, 퍼징 전략, 진입점 포함 JSON 출력.",
    },
    "zero_day_hunting": {
        "setup": "Phase 0: 타겟 설정. 공격 표면 식별. 파서/입력/네이티브 바인딩 위치 JSON 출력.",
        "fuzzing": "Phase 1: 병렬 퍼징. Worker당 동시 1개. anomaly JSON 배열 출력.",
        "triage": "Phase 2: Anomaly 트리아지. crash/leak/corruption/auth bypass 분류. JSON 출력.",
        "code_reading": "Phase 3: 코드 리딩. 루트 코즈, 취약점 경로, 영향 범위 JSON 출력.",
        "bypass": "Phase 4: 병렬 Bypass 3-agent. bypass 경로와 성공 여부 JSON 출력.",
        "cross_verify": "Phase 5: 교차 검증. 재현 가능성, 임팩트, severity 확정 JSON 출력.",
        "complete": "Phase 6: 최종 보고서. PoC, 임팩트, 권고사항 JSON 출력.",
    },
}

OUTPUT_SCHEMA = '응답은 JSON만 출력: {"phase": "...", "status": "done", "results": [...]}'


@activity.defn(name="run_hunting_phase")
async def run_hunting_phase(
    session_id: UUID,
    session_type: str,
    phase: str,
    config: dict[str, Any],
    work_dir: str,
    agent_id: str | None = None,
) -> dict[str, Any]:
    skill_name = SKILL_BY_TYPE.get(session_type, "opentarget")
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    skill_content = skill_path.read_text() if skill_path.exists() else ""

    phase_instruction = PHASE_PROMPTS.get(session_type, {}).get(phase, f"Phase '{phase}' 실행.")

    previous = config.get("previous_results", {})
    prev_str = ""
    if previous:
        prev_str = (
            f"\n\n이전 페이즈 결과:\n{json.dumps(previous, ensure_ascii=False, default=str)[:8000]}"
        )

    config_clean = {k: v for k, v in config.items() if k != "previous_results"}

    prompt = f"보안 연구원으로서 {session_type} 분석의 '{phase}' 페이즈를 실행하라.\n\n"
    if skill_content:
        prompt += f"<skill>\n{skill_content}\n</skill>\n\n"
    prompt += (
        f"{phase_instruction}\n\n"
        f"설정: {json.dumps(config_clean, ensure_ascii=False) if config_clean else '{}'}"
        f"{prev_str}\n\n"
        f"{OUTPUT_SCHEMA}"
    )

    cmd = [CLAUDE_CMD, "-p", prompt, "--output-format", "json", "--max-turns", "30"]
    cwd = work_dir if os.path.isdir(work_dir) else None

    activity.logger.info("Running hunting phase", extra={"phase": phase})

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
    except FileNotFoundError:
        activity.logger.error("Claude Code CLI not found")
        return {"phase": phase, "status": "failed", "error": "claude command not found"}

    if proc.returncode != 0:
        err = stderr_bytes.decode(errors="replace")[:2000]
        activity.logger.error(
            "Claude Code CLI failed", extra={"phase": phase, "returncode": proc.returncode}
        )
        return {"phase": phase, "status": "failed", "error": err}

    stdout_text = stdout_bytes.decode(errors="replace")
    try:
        claude_output = json.loads(stdout_text)
        result_text = claude_output.get("result", stdout_text)
    except (json.JSONDecodeError, TypeError):
        result_text = stdout_text

    try:
        parsed: dict[str, Any] = json.loads(result_text)
        return parsed
    except (json.JSONDecodeError, TypeError):
        return {"phase": phase, "status": "done", "raw": result_text[:10000]}


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:64]


@activity.defn(name="save_hunting_findings")
async def save_hunting_findings(
    session_id: UUID,
    session_type: str,
    phase_results: dict[str, Any],
) -> int:
    from app.core.database import async_session_factory
    from app.models.analysis_session import AnalysisSession
    from app.models.finding import Finding, RegressionStatus, Severity

    count = 0
    async with async_session_factory() as session:
        if session_type == "target_discovery":
            shortlist = phase_results.get("complete", phase_results.get("shortlisting", {}))
            candidates = shortlist.get("results", []) if isinstance(shortlist, dict) else []
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                title = item.get("name", item.get("repo", "unknown target"))
                fp = _fingerprint(f"target:{title}")
                finding = Finding(
                    session_id=session_id,
                    fingerprint=fp,
                    file_path=item.get("repo_url", item.get("repo", "")),
                    line_start=0,
                    line_end=0,
                    severity=Severity.INFO,
                    category="target_candidate",
                    title=title,
                    description=item.get("reason", item.get("description", "")),
                    regression_status=RegressionStatus.NEW,
                    extras={
                        "crackability_score": item.get("crackability_score", item.get("score", 0)),
                        "language": item.get("language", ""),
                        "fuzzing_strategy": item.get("fuzzing_strategy", ""),
                        "entry_point": item.get("entry_point", ""),
                        "role": item.get("role", "primary"),
                    },
                )
                session.add(finding)
                count += 1
        else:
            for phase_name, phase_data in phase_results.items():
                if not isinstance(phase_data, dict):
                    continue
                results = phase_data.get("results", [])
                if not isinstance(results, list):
                    continue
                for item in results:
                    if not isinstance(item, dict):
                        continue
                    title = item.get("title", item.get("id", f"finding-{phase_name}"))
                    fp = _fingerprint(f"zeroday:{title}:{item.get('file_path', '')}")
                    sev_str = item.get("severity", "medium").lower()
                    try:
                        severity = Severity(sev_str)
                    except ValueError:
                        severity = Severity.MEDIUM
                    finding = Finding(
                        session_id=session_id,
                        fingerprint=fp,
                        file_path=item.get("file_path", ""),
                        line_start=item.get("line_start", 0),
                        line_end=item.get("line_end", 0),
                        severity=severity,
                        category=item.get("category", phase_name),
                        title=title,
                        description=item.get("description", ""),
                        regression_status=RegressionStatus.NEW,
                        extras={
                            "phase": phase_name,
                            "poc_code": item.get("poc_code", ""),
                            "bypass_attempts": item.get("bypass_attempts", []),
                            "cross_verified": item.get("cross_verified", False),
                            "impact": item.get("impact", ""),
                        },
                    )
                    session.add(finding)
                    count += 1

        analysis = await session.get(AnalysisSession, session_id)
        if analysis is not None:
            analysis.phase_data = {
                **(analysis.phase_data or {}),
                "results_summary": {
                    "total_findings": count,
                    "phases_completed": list(phase_results.keys()),
                },
            }

        await session.commit()

    activity.logger.info(
        "Saved hunting findings",
        extra={"count": count, "session_type": session_type},
    )
    return count
