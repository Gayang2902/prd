import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.analysis_session import AnalysisSession
from app.models.finding import Finding, RegressionStatus
from app.models.project import ProjectStatus
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.repositories.project import ProjectRepository


class RegressionSummary(BaseModel):
    session_id: uuid.UUID
    commit_sha: str
    started_at: str
    new: int
    recurring: int
    resolved: int
    total: int


router = APIRouter(prefix="/projects", tags=["projects"])


def _get_repo(session: AsyncSession = Depends(get_session)) -> ProjectRepository:
    return ProjectRepository(session)


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    status_filter: ProjectStatus | None = Query(None, alias="status"),
    owner_id: uuid.UUID | None = Query(None),
    repo: ProjectRepository = Depends(_get_repo),
) -> list[ProjectRead]:
    projects = await repo.list(status=status_filter, owner_id=owner_id)
    return [ProjectRead.model_validate(p) for p in projects]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    repo: ProjectRepository = Depends(_get_repo),
    session: AsyncSession = Depends(get_session),
) -> ProjectRead:
    # TODO: owner_id를 SSO 인증 사용자로 교체 (BE-04 완료 후)
    user = (await session.execute(select(User).limit(1))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=400, detail="No users exist yet")
    project = await repo.create(payload, owner_id=user.id)
    await session.commit()
    return ProjectRead.model_validate(project)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: uuid.UUID,
    repo: ProjectRepository = Depends(_get_repo),
) -> ProjectRead:
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectRead.model_validate(project)


@router.get("/{project_id}/regression-history", response_model=list[RegressionSummary])
async def get_regression_history(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> list[RegressionSummary]:
    sessions_result = await db.execute(
        select(AnalysisSession)
        .where(
            AnalysisSession.project_id == project_id,
            AnalysisSession.state == "completed",
        )
        .order_by(AnalysisSession.started_at.asc())
    )
    sessions = sessions_result.scalars().all()

    summaries: list[RegressionSummary] = []
    for s in sessions:
        counts_result = await db.execute(
            select(
                Finding.regression_status,
                func.count(Finding.id),
            )
            .where(Finding.session_id == s.id)
            .group_by(Finding.regression_status)
        )
        count_map = {row[0]: row[1] for row in counts_result.all()}
        new = count_map.get(RegressionStatus.NEW, 0)
        recurring = count_map.get(RegressionStatus.RECURRING, 0)
        resolved = count_map.get(RegressionStatus.RESOLVED, 0)
        summaries.append(
            RegressionSummary(
                session_id=s.id,
                commit_sha=s.commit_sha,
                started_at=s.started_at.isoformat(),
                new=new,
                recurring=recurring,
                resolved=resolved,
                total=new + recurring,
            )
        )

    return summaries


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    repo: ProjectRepository = Depends(_get_repo),
    session: AsyncSession = Depends(get_session),
) -> ProjectRead:
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    project = await repo.update(project, payload)
    await session.commit()
    return ProjectRead.model_validate(project)
