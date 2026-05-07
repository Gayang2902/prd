import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment


class CommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_finding(self, finding_id: uuid.UUID) -> list[Comment]:
        result = await self._session.execute(
            select(Comment)
            .where(Comment.finding_id == finding_id)
            .order_by(Comment.created_at.asc())
        )
        return list(result.scalars().all())

    async def create(
        self, *, finding_id: uuid.UUID, author_id: uuid.UUID, content: str
    ) -> Comment:
        comment = Comment(finding_id=finding_id, author_id=author_id, content=content)
        self._session.add(comment)
        await self._session.flush()
        return comment
