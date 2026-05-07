import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, Role, require_role
from app.core.database import get_session
from app.schemas.finding import (
    CommentCreate,
    CommentRead,
    FindingRead,
    FindingStatusRead,
    FindingStatusUpdate,
)
from app.services.repositories.comment import CommentRepository
from app.services.repositories.finding import FindingRepository

router = APIRouter(tags=["findings"])


def _get_repo(session: AsyncSession = Depends(get_session)) -> FindingRepository:
    return FindingRepository(session)


def _get_comment_repo(session: AsyncSession = Depends(get_session)) -> CommentRepository:
    return CommentRepository(session)


@router.get("/sessions/{session_id}/findings", response_model=list[FindingRead])
async def list_findings(
    session_id: uuid.UUID,
    severity: str | None = Query(None),
    repo: FindingRepository = Depends(_get_repo),
) -> list[FindingRead]:
    findings = await repo.list_by_session(session_id, severity=severity)
    return [FindingRead.model_validate(f) for f in findings]


@router.get("/findings/{finding_id}", response_model=FindingRead)
async def get_finding(
    finding_id: uuid.UUID,
    repo: FindingRepository = Depends(_get_repo),
) -> FindingRead:
    finding = await repo.get(finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return FindingRead.model_validate(finding)


@router.patch("/findings/{finding_id}/status", response_model=FindingStatusRead)
async def update_finding_status(
    finding_id: uuid.UUID,
    payload: FindingStatusUpdate,
    user: CurrentUser,
    _role=require_role(Role.REVIEWER),
    repo: FindingRepository = Depends(_get_repo),
    db: AsyncSession = Depends(get_session),
) -> FindingStatusRead:
    finding = await repo.get(finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    fs = await repo.add_status(
        finding_id=finding_id,
        changed_by=user.id,
        status=payload.status,
        reason=payload.reason,
    )
    await db.commit()
    return FindingStatusRead.model_validate(fs)


@router.get("/findings/{finding_id}/timeline", response_model=list[FindingStatusRead])
async def get_finding_timeline(
    finding_id: uuid.UUID,
    repo: FindingRepository = Depends(_get_repo),
) -> list[FindingStatusRead]:
    history = await repo.get_status_history(finding_id)
    return [FindingStatusRead.model_validate(s) for s in history]


@router.get("/findings/{finding_id}/comments", response_model=list[CommentRead])
async def list_comments(
    finding_id: uuid.UUID,
    repo: CommentRepository = Depends(_get_comment_repo),
) -> list[CommentRead]:
    comments = await repo.list_by_finding(finding_id)
    return [CommentRead.model_validate(c) for c in comments]


@router.post("/findings/{finding_id}/comments", response_model=CommentRead, status_code=201)
async def create_comment(
    finding_id: uuid.UUID,
    payload: CommentCreate,
    user: CurrentUser,
    _role=require_role(Role.REVIEWER),
    repo: CommentRepository = Depends(_get_comment_repo),
    db: AsyncSession = Depends(get_session),
) -> CommentRead:
    comment = await repo.create(
        finding_id=finding_id,
        author_id=user.id,
        content=payload.content,
    )
    await db.commit()
    return CommentRead.model_validate(comment)
