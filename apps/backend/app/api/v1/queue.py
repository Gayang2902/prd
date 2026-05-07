from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.analysis_session import SessionState
from app.schemas.analysis_session import SessionRead
from app.services.repositories.session import SessionRepository

router = APIRouter(tags=["queue"])


def _get_repo(session: AsyncSession = Depends(get_session)) -> SessionRepository:
    return SessionRepository(session)


@router.get("/queue", response_model=list[SessionRead])
async def list_queue(
    state: SessionState | None = Query(None),
    repo: SessionRepository = Depends(_get_repo),
) -> list[SessionRead]:
    sessions = await repo.list_queue(state=state)
    return [SessionRead.model_validate(s) for s in sessions]
