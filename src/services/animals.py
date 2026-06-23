from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import (
    Animal,
    AnimalMember,
    AuditLogType,
    User,
)
from src.services.audit import log_audit
from src.services.users import load_user_with_membership
from src.utils.invite import generate_invite_code, normalize_invite_code

MAX_OWNERS_PER_ANIMAL = 20
PET_NAME_MAX_LENGTH = 100


@dataclass
class LeaveResult:
    animal_id: int


async def get_animal_by_invite_code(
    session: AsyncSession,
    invite_code: str,
) -> Animal | None:
    normalized = normalize_invite_code(invite_code)
    result = await session.execute(
        select(Animal).where(Animal.invite_code == normalized)
    )
    return result.scalar_one_or_none()


async def count_animal_members(session: AsyncSession, animal_id: int) -> int:
    result = await session.execute(
        select(AnimalMember).where(AnimalMember.animal_id == animal_id)
    )
    return len(result.scalars().all())


async def _generate_unique_invite_code(session: AsyncSession) -> str:
    while True:
        code = generate_invite_code()
        existing = await get_animal_by_invite_code(session, code)
        if existing is None:
            return code


async def leave_current_animal(
    session: AsyncSession,
    user: User,
) -> LeaveResult | None:
    from src.services.scenarios import cancel_user_scenario

    await cancel_user_scenario(session, user_id=user.id)

    result = await session.execute(
        select(AnimalMember)
        .where(AnimalMember.user_id == user.id)
        .options(selectinload(AnimalMember.animal))
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        return None

    animal_id = membership.animal_id
    animal = membership.animal

    await log_audit(
        session,
        animal_id=animal_id,
        log_type=AuditLogType.USER_LEFT,
        payload={"user_id": user.id},
    )

    await session.delete(membership)
    await session.flush()

    remaining = await count_animal_members(session, animal_id)
    if remaining == 0:
        await session.delete(animal)

    await load_user_with_membership(session, user.id)
    return LeaveResult(animal_id=animal_id)


async def create_animal(
    session: AsyncSession,
    *,
    user: User,
    name: str,
) -> tuple[Animal, LeaveResult | None]:
    leave_result = await leave_current_animal(session, user)

    animal = Animal(
        name=name,
        invite_code=await _generate_unique_invite_code(session),
    )
    session.add(animal)
    await session.flush()

    session.add(AnimalMember(animal_id=animal.id, user_id=user.id))
    await session.flush()

    await log_audit(
        session,
        animal_id=animal.id,
        log_type=AuditLogType.USER_JOINED,
        payload={"user_id": user.id},
    )

    await load_user_with_membership(session, user.id)
    return animal, leave_result


async def join_animal(
    session: AsyncSession,
    *,
    user: User,
    animal: Animal,
) -> tuple[Animal, LeaveResult | None]:
    if user.membership is not None and user.membership.animal_id == animal.id:
        return animal, None

    members_count = await count_animal_members(session, animal.id)
    if members_count >= MAX_OWNERS_PER_ANIMAL:
        raise ValueError("owner_limit_reached")

    leave_result = await leave_current_animal(session, user)

    session.add(AnimalMember(animal_id=animal.id, user_id=user.id))
    await session.flush()

    await log_audit(
        session,
        animal_id=animal.id,
        log_type=AuditLogType.USER_JOINED,
        payload={"user_id": user.id},
    )

    await load_user_with_membership(session, user.id)
    return animal, leave_result


async def format_recent_events(
    session: AsyncSession,
    *,
    animal_id: int,
    viewer: User,
    limit: int = 5,
) -> str | None:
    from src.services.events import format_event_list, get_recent_events

    events = await get_recent_events(session, animal_id=animal_id, limit=limit)
    if not events:
        return None

    return format_event_list(events, viewer=viewer)
