import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preset import Preset


class PresetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, *, agent_id: uuid.UUID | None = None) -> list[Preset]:
        stmt = select(Preset).order_by(Preset.name)
        if agent_id is not None:
            stmt = stmt.where(Preset.agent_id == agent_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, preset_id: uuid.UUID) -> Preset | None:
        return await self._session.get(Preset, preset_id)

    async def create(self, **kwargs) -> Preset:
        preset = Preset(**kwargs)
        self._session.add(preset)
        await self._session.flush()
        return preset

    async def update(self, preset: Preset, **kwargs) -> Preset:
        for key, value in kwargs.items():
            if value is not None:
                setattr(preset, key, value)
        await self._session.flush()
        return preset

    async def delete(self, preset: Preset) -> None:
        await self._session.delete(preset)
        await self._session.flush()
