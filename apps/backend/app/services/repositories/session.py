import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_session import AnalysisSession, SessionPriority, SessionState, SessionType

VALID_TRANSITIONS: dict[SessionState, set[SessionState]] = {
    SessionState.QUEUED: {SessionState.PREPARING, SessionState.CANCELED},
    SessionState.PREPARING: {SessionState.RUNNING, SessionState.FAILED, SessionState.CANCELED},
    SessionState.RUNNING: {
        SessionState.POST_PROCESSING,
        SessionState.FAILED,
        SessionState.CANCELED,
    },
    SessionState.POST_PROCESSING: {SessionState.COMPLETED, SessionState.FAILED},
    SessionState.COMPLETED: set(),
    SessionState.FAILED: set(),
    SessionState.CANCELED: set(),
}


class InvalidStateTransitionError(Exception):
    pass


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_project(self, project_id: uuid.UUID) -> list[AnalysisSession]:
        result = await self._session.execute(
            select(AnalysisSession)
            .where(AnalysisSession.project_id == project_id)
            .order_by(AnalysisSession.started_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, session_id: uuid.UUID) -> AnalysisSession | None:
        return await self._session.get(AnalysisSession, session_id)

    async def list_queue(
        self,
        *,
        state: SessionState | None = None,
    ) -> list[AnalysisSession]:
        priority_order = [
            SessionPriority.URGENT,
            SessionPriority.NORMAL,
            SessionPriority.BACKGROUND,
        ]
        stmt = select(AnalysisSession).where(
            AnalysisSession.state.in_(
                [
                    SessionState.QUEUED,
                    SessionState.PREPARING,
                    SessionState.RUNNING,
                    SessionState.POST_PROCESSING,
                ]
            )
        )
        if state is not None:
            stmt = stmt.where(AnalysisSession.state == state)
        from sqlalchemy import case

        stmt = stmt.order_by(
            case(
                {p: i for i, p in enumerate(priority_order)},
                value=AnalysisSession.priority,
            ),
            AnalysisSession.started_at.asc(),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_type(
        self, project_id: uuid.UUID, session_type: SessionType
    ) -> list[AnalysisSession]:
        result = await self._session.execute(
            select(AnalysisSession)
            .where(
                AnalysisSession.project_id == project_id,
                AnalysisSession.session_type == session_type,
            )
            .order_by(AnalysisSession.started_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        *,
        project_id: uuid.UUID,
        commit_sha: str,
        agent_id: uuid.UUID,
        preset_id: uuid.UUID,
        model_version: str,
        priority: SessionPriority = SessionPriority.NORMAL,
        session_type: SessionType = SessionType.STATIC_ANALYSIS,
        phase_data: dict | None = None,
    ) -> AnalysisSession:
        analysis = AnalysisSession(
            project_id=project_id,
            commit_sha=commit_sha,
            agent_id=agent_id,
            preset_id=preset_id,
            model_version=model_version,
            priority=priority,
            session_type=session_type,
            phase_data=phase_data,
        )
        self._session.add(analysis)
        await self._session.flush()
        return analysis

    async def update_phase_data(
        self,
        session_id: uuid.UUID,
        phase: str,
        phase_status: str,
        data: dict | None = None,
    ) -> AnalysisSession | None:
        analysis = await self.get(session_id)
        if analysis is None:
            return None
        pd = dict(analysis.phase_data or {})
        phases = pd.setdefault("phases", {})
        phases[phase] = {"status": phase_status, **(data or {})}
        pd["current_phase"] = phase
        analysis.phase_data = pd
        analysis.current_phase = phase
        await self._session.flush()
        return analysis

    async def transition(
        self, analysis: AnalysisSession, new_state: SessionState
    ) -> AnalysisSession:
        if analysis.state == new_state:
            return analysis
        allowed = VALID_TRANSITIONS.get(analysis.state, set())
        if new_state not in allowed:
            raise InvalidStateTransitionError(
                f"Cannot transition from {analysis.state} to {new_state}"
            )
        analysis.state = new_state
        await self._session.flush()
        return analysis
