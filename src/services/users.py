from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import AnimalMember, User

_USER_LOAD_OPTIONS = (
    selectinload(User.membership).selectinload(AnimalMember.animal),
)


async def load_user_with_membership(session: AsyncSession, user_id: int) -> User:
    result = await session.execute(
        select(User)
        .where(User.id == user_id)
        .options(*_USER_LOAD_OPTIONS)
    )
    return result.scalar_one()


async def get_or_create_user(
    session: AsyncSession,
    *,
    telegram_id: int,
    username: str | None,
    display_name: str,
) -> User:
    result = await session.execute(
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(*_USER_LOAD_OPTIONS)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            display_name=display_name,
        )
        session.add(user)
        await session.flush()
        return await load_user_with_membership(session, user.id)

    user.username = username
    user.display_name = display_name
    return user
