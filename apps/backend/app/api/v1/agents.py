from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.agent import Agent

router = APIRouter(tags=["agents"])


@router.get("/agents")
async def list_agents(db: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await db.execute(select(Agent))
    agents = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "version": a.version,
            "description": (a.metadata_ or {}).get("description", ""),
        }
        for a in agents
    ]
