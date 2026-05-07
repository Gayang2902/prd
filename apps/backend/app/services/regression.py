"""Regression matching algorithm.

Compares findings between the current session and the most recent prior session
for the same project, using fingerprints to classify each finding:

- NEW: fingerprint not seen in previous session
- RECURRING: fingerprint present in previous session
- RESOLVED: fingerprint in previous session but absent in current (applied to prior findings)
- CARRIED_OVER: same as RECURRING but status was already confirmed/false_positive
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_session import AnalysisSession
from app.models.finding import Finding, RegressionStatus


async def compute_regression_labels(
    db: AsyncSession,
    session_id: uuid.UUID,
    project_id: uuid.UUID,
) -> dict[str, int]:
    current_findings = (
        (await db.execute(select(Finding).where(Finding.session_id == session_id))).scalars().all()
    )

    prev_session = (
        await db.execute(
            select(AnalysisSession)
            .where(
                AnalysisSession.project_id == project_id,
                AnalysisSession.id != session_id,
                AnalysisSession.state == "completed",
            )
            .order_by(AnalysisSession.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if prev_session is None:
        for f in current_findings:
            f.regression_status = RegressionStatus.NEW
        await db.flush()
        return {"new": len(current_findings), "recurring": 0, "resolved": 0, "carried_over": 0}

    prev_findings = (
        (await db.execute(select(Finding).where(Finding.session_id == prev_session.id)))
        .scalars()
        .all()
    )

    prev_fingerprints = {f.fingerprint for f in prev_findings}
    current_fingerprints = {f.fingerprint for f in current_findings}

    counts = {"new": 0, "recurring": 0, "resolved": 0, "carried_over": 0}

    for f in current_findings:
        if f.fingerprint in prev_fingerprints:
            f.regression_status = RegressionStatus.RECURRING
            counts["recurring"] += 1
        else:
            f.regression_status = RegressionStatus.NEW
            counts["new"] += 1

    for f in prev_findings:
        if f.fingerprint not in current_fingerprints:
            f.regression_status = RegressionStatus.RESOLVED
            counts["resolved"] += 1

    await db.flush()
    return counts
