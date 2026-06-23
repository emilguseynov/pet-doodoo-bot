from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.bot import texts
from src.db.models import (
    AuditLogType,
    DefecationEvent,
    DefecationLocation,
    DefecationType,
    User,
)
from src.services.audit import log_audit
from src.services.reminders import reset_reminder_cycle
from src.utils.event_format import event_title_from_values
from src.utils.users import format_user_mention

RATE_LIMIT_SECONDS = 60
HISTORY_PAGE_SIZE = 5
_USER_EVENT_LOCK_NAMESPACE = 0x505001


def event_title(event: DefecationEvent) -> str:
    return event_title_from_values(event_type=event.type, location=event.location)


def format_event_list(
    events: list[DefecationEvent],
    *,
    viewer: User,
    start_index: int = 1,
) -> str:
    tz = ZoneInfo(viewer.timezone)
    lines: list[str] = []
    for offset, event in enumerate(events):
        index = start_index + offset
        local_time = event.created_at.astimezone(tz)
        timestamp = local_time.strftime("%d.%m.%Y %H:%M")
        author = format_user_mention(event.created_by)
        lines.append(f"{index}. {event_title(event)}\n{timestamp}\n{author}")
    return "\n\n".join(lines)


async def get_recent_events(
    session: AsyncSession,
    *,
    animal_id: int,
    limit: int = 5,
) -> list[DefecationEvent]:
    result = await session.execute(
        select(DefecationEvent)
        .where(DefecationEvent.animal_id == animal_id)
        .options(selectinload(DefecationEvent.created_by))
        .order_by(DefecationEvent.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_last_event_time_for_user(
    session: AsyncSession,
    user_id: int,
) -> datetime | None:
    result = await session.execute(
        select(DefecationEvent.created_at)
        .where(DefecationEvent.created_by_user_id == user_id)
        .order_by(DefecationEvent.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def is_rate_limited(session: AsyncSession, user_id: int) -> bool:
    last_created_at = await get_last_event_time_for_user(session, user_id)
    if last_created_at is None:
        return False
    elapsed = (datetime.now(timezone.utc) - last_created_at).total_seconds()
    return elapsed < RATE_LIMIT_SECONDS


async def _acquire_user_event_lock(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:namespace, :user_id)"),
        {"namespace": _USER_EVENT_LOCK_NAMESPACE, "user_id": user_id},
    )


async def try_create_event(
    session: AsyncSession,
    *,
    user: User,
    animal_id: int,
    event_type: DefecationType,
    location: DefecationLocation,
) -> DefecationEvent | None:
    await _acquire_user_event_lock(session, user.id)
    if await is_rate_limited(session, user.id):
        return None
    return await create_event(
        session,
        user=user,
        animal_id=animal_id,
        event_type=event_type,
        location=location,
    )


async def create_event(
    session: AsyncSession,
    *,
    user: User,
    animal_id: int,
    event_type: DefecationType,
    location: DefecationLocation,
) -> DefecationEvent:
    event = DefecationEvent(
        animal_id=animal_id,
        created_by_user_id=user.id,
        type=event_type.value,
        location=location.value,
    )
    session.add(event)
    await session.flush()
    await session.refresh(event)

    await log_audit(
        session,
        animal_id=animal_id,
        log_type=AuditLogType.EVENT_CREATED,
        payload={
            "event_id": event.id,
            "user_id": user.id,
            "type": event.type,
            "location": event.location,
        },
    )
    await reset_reminder_cycle(session, animal_id=animal_id, last_event=event)
    return event


async def count_events(session: AsyncSession, animal_id: int) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(DefecationEvent)
        .where(DefecationEvent.animal_id == animal_id)
    )
    return result.scalar_one()


async def get_history_page(
    session: AsyncSession,
    *,
    animal_id: int,
    page: int,
) -> tuple[list[DefecationEvent], int]:
    total = await count_events(session, animal_id)
    offset = (page - 1) * HISTORY_PAGE_SIZE
    result = await session.execute(
        select(DefecationEvent)
        .where(DefecationEvent.animal_id == animal_id)
        .options(selectinload(DefecationEvent.created_by))
        .order_by(DefecationEvent.created_at.desc())
        .offset(offset)
        .limit(HISTORY_PAGE_SIZE)
    )
    events = list(result.scalars().all())
    return events, total


async def get_last_event(
    session: AsyncSession,
    *,
    animal_id: int,
) -> DefecationEvent | None:
    events = await get_recent_events(session, animal_id=animal_id, limit=1)
    return events[0] if events else None


async def delete_last_event(
    session: AsyncSession,
    *,
    user: User,
    animal_id: int,
) -> DefecationEvent | None:
    event = await get_last_event(session, animal_id=animal_id)
    if event is None:
        return None

    await log_audit(
        session,
        animal_id=animal_id,
        log_type=AuditLogType.EVENT_DELETED,
        payload={
            "event_id": event.id,
            "user_id": user.id,
            "type": event.type,
            "location": event.location,
        },
    )
    await session.delete(event)
    await session.flush()

    remaining = await get_last_event(session, animal_id=animal_id)
    await reset_reminder_cycle(session, animal_id=animal_id, last_event=remaining)
    return event
