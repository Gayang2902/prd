import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import Role, require_role
from app.core.database import get_session
from app.services.audit import list_audit_logs

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str
    detail: str | None
    ip_address: str | None
    created_at: datetime


@router.get("/logs", response_model=list[AuditLogRead])
async def get_audit_logs(
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    _role: Any = require_role(Role.ADMIN),
    db: AsyncSession = Depends(get_session),
) -> list[AuditLogRead]:
    logs = await list_audit_logs(
        db, action=action, resource_type=resource_type, user_id=user_id, limit=limit, offset=offset
    )
    return [AuditLogRead.model_validate(log) for log in logs]
