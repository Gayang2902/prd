import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import Role, require_role
from app.core.database import get_session
from app.models.analysis_session import SessionState
from app.schemas.analysis_session import SessionCreate, SessionRead
from app.services.agent_registry import get_registry
from app.services.repositories.session import SessionRepository

router = APIRouter(tags=["sessions"])


def _get_repo(session: AsyncSession = Depends(get_session)) -> SessionRepository:
    return SessionRepository(session)


@router.get(
    "/projects/{project_id}/sessions",
    response_model=list[SessionRead],
)
async def list_sessions(
    project_id: uuid.UUID,
    repo: SessionRepository = Depends(_get_repo),
) -> list[SessionRead]:
    sessions = await repo.list_by_project(project_id)
    return [SessionRead.model_validate(s) for s in sessions]


@router.post(
    "/projects/{project_id}/sessions",
    response_model=SessionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_session(
    project_id: uuid.UUID,
    payload: SessionCreate,
    _user=require_role(Role.REVIEWER),
    repo: SessionRepository = Depends(_get_repo),
    db: AsyncSession = Depends(get_session),
) -> SessionRead:
    registry = get_registry()
    agent_cls = None
    for cls in registry.values():
        meta = cls.describe()
        if meta.name:
            agent_cls = cls
            break
    if agent_cls is None:
        raise HTTPException(status_code=400, detail="No agents available")

    meta = agent_cls.describe()
    analysis = await repo.create(
        project_id=project_id,
        commit_sha=payload.commit_sha or "HEAD",
        agent_id=payload.agent_id,
        preset_id=payload.preset_id,
        model_version=f"{meta.name}-{meta.version}",
        priority=payload.priority,
    )
    await db.commit()
    return SessionRead.model_validate(analysis)


@router.get("/sessions/{session_id}", response_model=SessionRead)
async def get_session_detail(
    session_id: uuid.UUID,
    repo: SessionRepository = Depends(_get_repo),
) -> SessionRead:
    analysis = await repo.get(session_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionRead.model_validate(analysis)


@router.post("/sessions/{session_id}/cancel", response_model=SessionRead)
async def cancel_session(
    session_id: uuid.UUID,
    _user=require_role(Role.REVIEWER),
    repo: SessionRepository = Depends(_get_repo),
    db: AsyncSession = Depends(get_session),
) -> SessionRead:
    analysis = await repo.get(session_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        analysis = await repo.transition(analysis, SessionState.CANCELED)
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    await db.commit()
    return SessionRead.model_validate(analysis)


@router.get("/sessions/{session_id}/logs")
async def stream_session_logs(
    session_id: uuid.UUID,
    repo: SessionRepository = Depends(_get_repo),
) -> StreamingResponse:
    analysis = await repo.get(session_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        state = analysis.state.value
        ts = datetime.now(UTC).isoformat()
        yield f'event: state\ndata: {{"state": "{state}", "ts": "{ts}"}}\n\n'

        if analysis.state in (
            SessionState.COMPLETED,
            SessionState.FAILED,
            SessionState.CANCELED,
        ):
            yield f'event: done\ndata: {{"state": "{state}", "ts": "{ts}"}}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
