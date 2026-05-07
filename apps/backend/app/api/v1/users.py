from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, Role, require_role
from app.core.database import get_session
from app.schemas.user import UserCreate, UserRead
from app.services.repositories.user import UserRepository

router = APIRouter(prefix="/users", tags=["users"])


def _get_repo(session: AsyncSession = Depends(get_session)) -> UserRepository:
    return UserRepository(session)


@router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.get("", response_model=list[UserRead])
async def list_users(
    _user=require_role(Role.LEAD),
    repo: UserRepository = Depends(_get_repo),
) -> list[UserRead]:
    users = await repo.list()
    return [UserRead.model_validate(u) for u in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    _user=require_role(Role.ADMIN),
    repo: UserRepository = Depends(_get_repo),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    existing = await repo.get_by_email(payload.email)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = await repo.create(email=payload.email, name=payload.name, role=payload.role.value)
    await session.commit()
    return UserRead.model_validate(user)
