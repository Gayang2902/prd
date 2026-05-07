import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser
from app.core.database import get_session
from app.services.report_generator import generate_report

router = APIRouter(tags=["reports"])


@router.post("/sessions/{session_id}/reports")
async def create_report(
    session_id: uuid.UUID,
    user: CurrentUser,
    format: str = Query("markdown", pattern="^(markdown|csv|json)$"),
    db: AsyncSession = Depends(get_session),
) -> Response:
    content, content_type, filename = await generate_report(db, session_id, format)
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
