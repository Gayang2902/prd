import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.user import Role, User


async def get_current_user(
    x_user_id: Annotated[str, Header()],
    session: AsyncSession = Depends(get_session),
) -> User:
    """MVP 인증: X-User-Id 헤더로 사용자 식별. SSO 통합(BE-04) 후 JWT로 교체."""
    try:
        user_id = uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID") from None
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

ROLE_HIERARCHY: dict[Role, int] = {
    Role.VIEWER: 0,
    Role.REVIEWER: 1,
    Role.LEAD: 2,
    Role.ADMIN: 3,
}


def require_role(minimum: Role):
    """최소 역할 검사 데코레이터. 역할 계층: VIEWER < REVIEWER < LEAD < ADMIN."""

    async def _check(user: CurrentUser) -> User:
        if ROLE_HIERARCHY.get(user.role, -1) < ROLE_HIERARCHY[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum.value} role or higher",
            )
        return user

    return Depends(_check)
