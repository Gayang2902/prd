from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_session import AnalysisSession


async def cost_summary(
    db: AsyncSession,
    *,
    since: date | None = None,
    until: date | None = None,
) -> dict:
    stmt = select(
        func.count(AnalysisSession.id).label("total_sessions"),
        func.coalesce(func.sum(AnalysisSession.token_usage), 0).label("total_tokens"),
        func.coalesce(func.sum(AnalysisSession.cost), Decimal("0")).label("total_cost"),
    ).where(AnalysisSession.state == "completed")

    if since:
        stmt = stmt.where(
            AnalysisSession.started_at >= datetime(since.year, since.month, since.day, tzinfo=UTC)
        )
    if until:
        stmt = stmt.where(
            AnalysisSession.started_at < datetime(until.year, until.month, until.day, tzinfo=UTC)
        )

    row = (await db.execute(stmt)).one()
    return {
        "total_sessions": row.total_sessions,
        "total_tokens": row.total_tokens,
        "total_cost": row.total_cost,
    }


async def cost_by_project(
    db: AsyncSession,
    *,
    since: date | None = None,
    until: date | None = None,
) -> list[dict]:
    stmt = (
        select(
            AnalysisSession.project_id,
            func.count(AnalysisSession.id).label("sessions"),
            func.coalesce(func.sum(AnalysisSession.token_usage), 0).label("tokens"),
            func.coalesce(func.sum(AnalysisSession.cost), Decimal("0")).label("cost"),
        )
        .where(AnalysisSession.state == "completed")
        .group_by(AnalysisSession.project_id)
        .order_by(func.sum(AnalysisSession.cost).desc())
    )

    if since:
        stmt = stmt.where(
            AnalysisSession.started_at >= datetime(since.year, since.month, since.day, tzinfo=UTC)
        )
    if until:
        stmt = stmt.where(
            AnalysisSession.started_at < datetime(until.year, until.month, until.day, tzinfo=UTC)
        )

    rows = (await db.execute(stmt)).all()
    return [
        {
            "project_id": str(r.project_id),
            "sessions": r.sessions,
            "tokens": r.tokens,
            "cost": r.cost,
        }
        for r in rows
    ]


async def cost_by_agent(
    db: AsyncSession,
    *,
    since: date | None = None,
    until: date | None = None,
) -> list[dict]:
    stmt = (
        select(
            AnalysisSession.model_version,
            func.count(AnalysisSession.id).label("sessions"),
            func.coalesce(func.sum(AnalysisSession.token_usage), 0).label("tokens"),
            func.coalesce(func.sum(AnalysisSession.cost), Decimal("0")).label("cost"),
        )
        .where(AnalysisSession.state == "completed")
        .group_by(AnalysisSession.model_version)
        .order_by(func.sum(AnalysisSession.cost).desc())
    )

    if since:
        stmt = stmt.where(
            AnalysisSession.started_at >= datetime(since.year, since.month, since.day, tzinfo=UTC)
        )
    if until:
        stmt = stmt.where(
            AnalysisSession.started_at < datetime(until.year, until.month, until.day, tzinfo=UTC)
        )

    rows = (await db.execute(stmt)).all()
    return [
        {
            "model_version": r.model_version,
            "sessions": r.sessions,
            "tokens": r.tokens,
            "cost": r.cost,
        }
        for r in rows
    ]


async def cost_daily(
    db: AsyncSession,
    *,
    since: date | None = None,
    until: date | None = None,
) -> list[dict]:
    day_col = func.date(AnalysisSession.started_at).label("day")
    stmt = (
        select(
            day_col,
            func.count(AnalysisSession.id).label("sessions"),
            func.coalesce(func.sum(AnalysisSession.token_usage), 0).label("tokens"),
            func.coalesce(func.sum(AnalysisSession.cost), Decimal("0")).label("cost"),
        )
        .where(AnalysisSession.state == "completed")
        .group_by(day_col)
        .order_by(day_col.asc())
    )

    if since:
        stmt = stmt.where(
            AnalysisSession.started_at >= datetime(since.year, since.month, since.day, tzinfo=UTC)
        )
    if until:
        stmt = stmt.where(
            AnalysisSession.started_at < datetime(until.year, until.month, until.day, tzinfo=UTC)
        )

    rows = (await db.execute(stmt)).all()
    return [
        {"date": str(r.day), "sessions": r.sessions, "tokens": r.tokens, "cost": r.cost}
        for r in rows
    ]
