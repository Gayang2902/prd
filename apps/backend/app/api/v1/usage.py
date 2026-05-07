from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import Role, require_role
from app.core.database import get_session
from app.services.cost_aggregation import cost_by_agent, cost_by_project, cost_daily, cost_summary

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/cost")
async def get_cost_summary(
    since: date | None = Query(None),
    until: date | None = Query(None),
    _role: Any = require_role(Role.VIEWER),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await cost_summary(db, since=since, until=until)


@router.get("/by-project")
async def get_cost_by_project(
    since: date | None = Query(None),
    until: date | None = Query(None),
    _role: Any = require_role(Role.VIEWER),
    db: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    return await cost_by_project(db, since=since, until=until)


@router.get("/by-agent")
async def get_cost_by_agent(
    since: date | None = Query(None),
    until: date | None = Query(None),
    _role: Any = require_role(Role.VIEWER),
    db: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    return await cost_by_agent(db, since=since, until=until)


@router.get("/daily")
async def get_cost_daily(
    since: date | None = Query(None),
    until: date | None = Query(None),
    _role: Any = require_role(Role.VIEWER),
    db: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    return await cost_daily(db, since=since, until=until)
