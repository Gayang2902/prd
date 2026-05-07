from fastapi import APIRouter

from app.api.v1.audit import router as audit_router
from app.api.v1.findings import router as findings_router
from app.api.v1.health import router as health_router
from app.api.v1.presets import router as presets_router
from app.api.v1.queue import router as queue_router
from app.api.v1.reports import router as reports_router
from app.api.v1.projects import router as projects_router
from app.api.v1.sessions import router as sessions_router
from app.api.v1.usage import router as usage_router
from app.api.v1.users import router as users_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(projects_router)
api_router.include_router(sessions_router)
api_router.include_router(users_router)
api_router.include_router(findings_router)
api_router.include_router(presets_router)
api_router.include_router(reports_router)
api_router.include_router(queue_router)
api_router.include_router(usage_router)
api_router.include_router(audit_router)
