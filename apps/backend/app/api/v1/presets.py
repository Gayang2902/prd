import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, Role, require_role
from app.core.database import get_session
from app.schemas.preset import PresetCreate, PresetRead, PresetUpdate
from app.services.repositories.preset import PresetRepository

router = APIRouter(prefix="/presets", tags=["presets"])


def _get_repo(session: AsyncSession = Depends(get_session)) -> PresetRepository:
    return PresetRepository(session)


@router.get("", response_model=list[PresetRead])
async def list_presets(
    agent_id: uuid.UUID | None = Query(None),
    repo: PresetRepository = Depends(_get_repo),
) -> list[PresetRead]:
    presets = await repo.list(agent_id=agent_id)
    return [PresetRead.model_validate(p) for p in presets]


@router.get("/{preset_id}", response_model=PresetRead)
async def get_preset(
    preset_id: uuid.UUID,
    repo: PresetRepository = Depends(_get_repo),
) -> PresetRead:
    preset = await repo.get(preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail="Preset not found")
    return PresetRead.model_validate(preset)


@router.post("", response_model=PresetRead, status_code=201)
async def create_preset(
    payload: PresetCreate,
    user: CurrentUser,
    _role: Any = require_role(Role.LEAD),
    repo: PresetRepository = Depends(_get_repo),
    db: AsyncSession = Depends(get_session),
) -> PresetRead:
    preset = await repo.create(**payload.model_dump())
    await db.commit()
    return PresetRead.model_validate(preset)


@router.patch("/{preset_id}", response_model=PresetRead)
async def update_preset(
    preset_id: uuid.UUID,
    payload: PresetUpdate,
    user: CurrentUser,
    _role: Any = require_role(Role.LEAD),
    repo: PresetRepository = Depends(_get_repo),
    db: AsyncSession = Depends(get_session),
) -> PresetRead:
    preset = await repo.get(preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail="Preset not found")
    updated = await repo.update(preset, **payload.model_dump(exclude_unset=True))
    await db.commit()
    return PresetRead.model_validate(updated)


@router.delete("/{preset_id}", status_code=204)
async def delete_preset(
    preset_id: uuid.UUID,
    user: CurrentUser,
    _role: Any = require_role(Role.ADMIN),
    repo: PresetRepository = Depends(_get_repo),
    db: AsyncSession = Depends(get_session),
) -> None:
    preset = await repo.get(preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail="Preset not found")
    await repo.delete(preset)
    await db.commit()
