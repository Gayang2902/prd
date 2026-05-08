import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from securescope_schemas.agent_interface import (
    AnalysisContext,
    CodeScope,
    PresetConfig,
    ResourceLimits,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import Role, require_role
from app.core.database import get_session
from app.core.temporal import get_temporal_client
from app.models.analysis_session import SessionType
from app.schemas.analysis_session import SessionRead
from app.schemas.finding import FindingRead
from app.schemas.hunting import HuntingSessionCreate, PhaseUpdate
from app.services.agent_registry import get_registry
from app.services.repositories.finding import FindingRepository
from app.services.repositories.session import SessionRepository
from app.workflows.models import HuntingContext

router = APIRouter(prefix="/hunting", tags=["hunting"])


def _get_repo(session: AsyncSession = Depends(get_session)) -> SessionRepository:
    return SessionRepository(session)


def _get_finding_repo(session: AsyncSession = Depends(get_session)) -> FindingRepository:
    return FindingRepository(session)


async def _create_hunting_session(
    payload: HuntingSessionCreate,
    session_type: SessionType,
    repo: SessionRepository,
    db: AsyncSession,
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
    initial_phase_data = {"config": payload.config, "phases": {}}
    analysis = await repo.create(
        project_id=payload.project_id,
        commit_sha=payload.commit_sha or "HEAD",
        agent_id=payload.agent_id,
        preset_id=payload.preset_id,
        model_version=f"{meta.name}-{meta.version}",
        priority=payload.priority,
        session_type=session_type,
        phase_data=initial_phase_data,
    )
    await db.commit()

    hunting_ctx = HuntingContext(
        session_id=analysis.id,
        session_type=session_type.value,
        scope=CodeScope(
            repo_path=str(analysis.project_id),
            commit_sha=analysis.commit_sha,
        ),
        analysis_context=AnalysisContext(
            session_id=analysis.id,
            scope=CodeScope(
                repo_path=str(analysis.project_id),
                commit_sha=analysis.commit_sha,
            ),
            preset=PresetConfig(
                id=analysis.preset_id,
                version_sha="latest",
                prompt_template="hunting",
                ruleset=payload.config,
            ),
            limits=ResourceLimits(),
        ),
    )

    client = await get_temporal_client()
    await client.start_workflow(
        "HuntingWorkflow",
        hunting_ctx,
        id=f"hunting-{analysis.id}",
        task_queue="analysis-queue",
    )

    return SessionRead.model_validate(analysis)


@router.post(
    "/target-discovery",
    response_model=SessionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_target_discovery(
    payload: HuntingSessionCreate,
    _user: Any = require_role(Role.REVIEWER),
    repo: SessionRepository = Depends(_get_repo),
    db: AsyncSession = Depends(get_session),
) -> SessionRead:
    return await _create_hunting_session(
        payload, SessionType.TARGET_DISCOVERY, repo, db
    )


@router.post(
    "/zero-day",
    response_model=SessionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_zero_day_hunt(
    payload: HuntingSessionCreate,
    _user: Any = require_role(Role.REVIEWER),
    repo: SessionRepository = Depends(_get_repo),
    db: AsyncSession = Depends(get_session),
) -> SessionRead:
    return await _create_hunting_session(
        payload, SessionType.ZERO_DAY_HUNTING, repo, db
    )


@router.patch(
    "/sessions/{session_id}/phase",
    response_model=SessionRead,
)
async def update_phase(
    session_id: uuid.UUID,
    payload: PhaseUpdate,
    _user: Any = require_role(Role.REVIEWER),
    repo: SessionRepository = Depends(_get_repo),
    db: AsyncSession = Depends(get_session),
) -> SessionRead:
    analysis = await repo.update_phase_data(
        session_id, payload.phase, payload.status, payload.data
    )
    if analysis is None:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.commit()
    return SessionRead.model_validate(analysis)


@router.get(
    "/sessions/{session_id}/targets",
    response_model=list[FindingRead],
)
async def list_target_candidates(
    session_id: uuid.UUID,
    repo: FindingRepository = Depends(_get_finding_repo),
) -> list[FindingRead]:
    findings = await repo.list_by_session(
        session_id, category="target_candidate"
    )
    findings.sort(
        key=lambda f: (f.extras or {}).get("crackability_score", 0),
        reverse=True,
    )
    return [FindingRead.model_validate(f) for f in findings]
