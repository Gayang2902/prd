"""Report generation for analysis sessions.

Supports Markdown, CSV, and JSON formats.
"""

import csv
import io
import json
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.repositories.finding import FindingRepository


async def generate_report(
    session: AsyncSession,
    session_id: uuid.UUID,
    format: str,
) -> tuple[str, str, str]:
    """Generate a report and return (content, content_type, filename)."""
    repo = FindingRepository(session)
    findings = await repo.list_by_session(session_id)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    sid_short = str(session_id)[:8]

    if format == "markdown":
        return _to_markdown(findings, session_id), "text/markdown", f"report_{sid_short}_{ts}.md"
    elif format == "csv":
        return _to_csv(findings), "text/csv", f"report_{sid_short}_{ts}.csv"
    else:
        return _to_json(findings), "application/json", f"report_{sid_short}_{ts}.json"


def _to_markdown(findings, session_id) -> str:
    lines = [
        f"# SecureScope 분석 리포트",
        f"",
        f"**세션**: `{session_id}`  ",
        f"**생성일**: {datetime.utcnow().isoformat()}  ",
        f"**총 취약점**: {len(findings)}건",
        f"",
        f"---",
        f"",
    ]

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    sorted_findings = sorted(findings, key=lambda f: severity_order.get(f.severity.value, 99))

    for f in sorted_findings:
        lines.extend([
            f"## [{f.severity.value.upper()}] {f.title}",
            f"",
            f"- **카테고리**: {f.category}",
            f"- **파일**: `{f.file_path}:{f.line_start}-{f.line_end}`",
            f"- **회귀 상태**: {f.regression_status.value}",
            f"",
            f"{f.description}",
            f"",
            f"---",
            f"",
        ])

    return "\n".join(lines)


def _to_csv(findings) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "severity", "category", "title", "file_path",
        "line_start", "line_end", "description", "regression_status",
    ])
    for f in findings:
        writer.writerow([
            f.severity.value, f.category, f.title, f.file_path,
            f.line_start, f.line_end, f.description, f.regression_status.value,
        ])
    return output.getvalue()


def _to_json(findings) -> str:
    data = [
        {
            "id": str(f.id),
            "severity": f.severity.value,
            "category": f.category,
            "title": f.title,
            "file_path": f.file_path,
            "line_start": f.line_start,
            "line_end": f.line_end,
            "description": f.description,
            "regression_status": f.regression_status.value,
            "fingerprint": f.fingerprint,
        }
        for f in findings
    ]
    return json.dumps(data, ensure_ascii=False, indent=2)
