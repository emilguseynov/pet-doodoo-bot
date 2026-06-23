from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
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
from src.utils.users import format_user_mention

RATE_LIMIT_SECONDS = 60
HISTORY_PAGE_SIZE = 5


def event_title(event: DefecationEvent) -> str:
    if event.type == DefecationType.TOILET:
        return texts.EVENT_TITLE_TOILET
    try:
        location = DefecationLocation(event.location)
    except ValueError:
        return f"{texts.ACCIDENT_TITLE_PREFIX}{event.location}"
    label = texts.LOCATION_LABELS.get(location, event.location)
    return f"{texts.ACCIDENT_TITLE_PREFIX}{label}"


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
