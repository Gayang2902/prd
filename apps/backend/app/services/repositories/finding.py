import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.models.finding_status import FindingStatus, VerificationStatus


class FindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_session(
        self,
        session_id: uuid.UUID,
        *,
        severity: str | None = None,
    ) -> list[Finding]:
        stmt = (
            select(Finding)
            .where(Finding.session_id == session_id)
            .order_by(Finding.severity, Finding.file_path)
        )
        if severity is not None:
            stmt = stmt.where(Finding.severity == severity)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, finding_id: uuid.UUID) -> Finding | None:
        return await self._session.get(Finding, finding_id)

    async def add_status(
        self,
        *,
        finding_id: uuid.UUID,
        changed_by: uuid.UUID,
        status: VerificationStatus,
        reason: str | None = None,
    ) -> FindingStatus:
        fs = FindingStatus(
            finding_id=finding_id,
            changed_by=changed_by,
            status=status,
            reason=reason,
        )
        self._session.add(fs)
        await self._session.flush()
        return fs

    async def get_status_history(self, finding_id: uuid.UUID) -> list[FindingStatus]:
        result = await self._session.execute(
            select(FindingStatus)
            .where(FindingStatus.finding_id == finding_id)
            .order_by(FindingStatus.changed_at.desc())
        )
        return list(result.scalars().all())
