import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectStatus
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        status: ProjectStatus | None = None,
        owner_id: uuid.UUID | None = None,
    ) -> list[Project]:
        stmt = select(Project).order_by(Project.created_at.desc())
        if status is not None:
            stmt = stmt.where(Project.status == status)
        if owner_id is not None:
            stmt = stmt.where(Project.owner_id == owner_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, project_id: uuid.UUID) -> Project | None:
        return await self._session.get(Project, project_id)

    async def create(self, payload: ProjectCreate, owner_id: uuid.UUID) -> Project:
        project = Project(**payload.model_dump(), owner_id=owner_id)
        self._session.add(project)
        await self._session.flush()
        return project

    async def update(self, project: Project, payload: ProjectUpdate) -> Project:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        await self._session.flush()
        return project
