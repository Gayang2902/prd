import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[User]:
        result = await self._session.execute(select(User).order_by(User.name))
        return list(result.scalars().all())

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, *, email: str, name: str, role: str = "viewer") -> User:
        user = User(email=email, name=name, role=role)
        self._session.add(user)
        await self._session.flush()
        return user
