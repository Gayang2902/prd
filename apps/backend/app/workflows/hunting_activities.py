import asyncio
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import structlog
from temporalio import activity

from app.core.config import settings

logger = structlog.get_logger()

CLAUDE_CMD = os.environ.get("CLAUDE_CMD", settings.claude_cmd)
SKILLS_DIR = Path(os.environ.get("SKILLS_DIR", str(Path.home() / ".claude" / "skills")))

SKILL_BY_TYPE: dict[str, str] = {
    "target_discovery": "opentarget",
    "zero_day_hunting": "openresearch",
}

PHASE_PROMPTS: dict[str, dict[str, str]] = {
    "target_discovery": {
        "gathering": (
            "Phase 1 실행: 병렬 후보 수집. "
            "Centralized MAS 패턴으로 3개 검색 경로에서 40~60개 후보를 수집하라. "
            "에코시스템별 결과를 JSON 배열로 출력."
        ),
        "filtering": (
            "Phase 2 실행: 빠른 필터링. "
            "수집된 후보에서 규칙 위반 항목을 제거하라. "
            "외부 입력 없음, 비활성, 대형 프레임워크 등을 필터. "
            "남은 후보 목록을 JSON으로 출력."
        ),
        "scoring": (
            "Phase 3 실행: Crackability 스코어링. "
            "남은 후보 각각에 crackability 점수(1~10)를 매겨라. "
            "네이티브 코드 가산, 보안 강화 감점, 단독 관리자 가산. "
            "점수순 정렬 JSON 출력."
        ),
        "shortlisting": (
            "Phase 4-6 실행: Patch-diff 분석 + 구조 분석 + 최종 선택. "
            "상위 후보의 최근 패치를 분석하고 퍼징 전략을 수립하라. "
            "primary 1개 + backup 2개를 선정. "
            "최종 shortlist를 JSON으로 출력."
        ),
        "complete": (
            "최종 보고서 작성. 선정된 타겟의 요약, crackability 점수, "
            "추천 퍼징 전략, 진입점을 포함한 JSON 보고서 출력."
        ),
    },
    "zero_day_hunting": {
        "setup": (
            "Phase 0 실행: 타겟 설정. "
            "타겟 저장소를 분석하고 공격 표면을 식별하라. "
            "파서, 입력 처리, 네이티브 바인딩 위치를 JSON으로 출력."
        ),
        "fuzzing": (
            "Phase 1 실행: 병렬 퍼징. "
            "Centralized MAS 패턴으로 3개 Worker가 동시 퍼징. "
            "Worker당 동시 퍼징 1개, 메모리 가드 필수. "
            "발견된 anomaly를 JSON 배열로 출력."
        ),
        "triage": (
            "Phase 2 실행: Anomaly 트리아지. "
            "퍼징에서 발견된 anomaly를 분류하라. "
            "crash/leak/corruption/auth bypass 여부 판단. "
            "유효 anomaly 목록을 JSON으로 출력."
        ),
        "code_reading": (
            "Phase 3 실행: SAS 코드 리딩 (Opus 단독). "
            "트리아지된 anomaly의 루트 코즈를 코드에서 분석하라. "
            "취약점 경로, 영향 범위, 선행 조건을 JSON으로 출력."
        ),
        "bypass": (
            "Phase 4 실행: 병렬 Bypass. "
            "방어 메커니즘 발견 시 Centralized MAS 3-agent로 우회 시도. "
            "각 bypass 경로와 성공 여부를 JSON으로 출력."
        ),
        "cross_verify": (
            "Phase 5 실행: CCG 교차 검증. "
            "Decentralized 패턴으로 다중 관점 검증. "
            "각 finding의 재현 가능성, 임팩트, severity를 확정. "
            "검증 결과를 JSON으로 출력."
        ),
        "complete": (
            "Phase 6 실행: 최종 보고서. "
            "검증된 finding의 PoC, 임팩트, 권고사항을 포함한 "
            "JSON 보고서 출력."
        ),
    },
}


def _build_prompt(session_type: str, phase: str, config: dict) -> str:
    skill_name = SKILL_BY_TYPE[session_type]
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    skill_content = ""
    if skill_path.exists():
        skill_content = skill_path.read_text()

    phase_instruction = PHASE_PROMPTS.get(session_type, {}).get(phase, "")
    config_str = json.dumps(config, ensure_ascii=False) if config else "{}"

    return (
        f"<skill>\n{skill_content}\n</skill>\n\n"
        f"<phase>{phase}</phase>\n"
        f"<config>{config_str}</config>\n\n"
        f"{phase_instruction}\n\n"
        "응답은 반드시 JSON 형식으로. "
        '최상위에 "phase", "status", "results" 키를 포함하라.'
    )


@activity.defn(name="run_hunting_phase")
async def run_hunting_phase(
    session_id: UUID,
    session_type: str,
    phase: str,
    config: dict,
    work_dir: str,
) -> dict:
    prompt = _build_prompt(session_type, phase, config)

    cmd = [
        CLAUDE_CMD,
        "-p",
        prompt,
        "--output-format",
        "json",
        "--max-turns",
        "50",
    ]

    activity.logger.info(
        "Running hunting phase",
        extra={"session_type": session_type, "phase": phase},
    )

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=work_dir,
    )
    stdout_bytes, stderr_bytes = await proc.communicate()

    if proc.returncode != 0:
        err = stderr_bytes.decode(errors="replace")
        activity.logger.error(
            "Hunting phase failed",
            extra={"phase": phase, "returncode": proc.returncode, "stderr": err[:500]},
        )
        return {"phase": phase, "status": "failed", "error": err[:2000]}

    stdout_text = stdout_bytes.decode(errors="replace")
    try:
        result = json.loads(stdout_text)
        if "result" in result:
            inner = result["result"]
            try:
                return json.loads(inner) if isinstance(inner, str) else inner
            except (json.JSONDecodeError, TypeError):
                return {"phase": phase, "status": "done", "raw": inner[:10000]}
        return result
    except json.JSONDecodeError:
        return {"phase": phase, "status": "done", "raw": stdout_text[:10000]}


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:64]


@activity.defn(name="save_hunting_findings")
async def save_hunting_findings(
    session_id: UUID,
    session_type: str,
    phase_results: dict,
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
                    severity = Severity(sev_str) if sev_str in Severity.__members__.values() else Severity.MEDIUM
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
                            "anomaly_type": item.get("anomaly_type", ""),
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
