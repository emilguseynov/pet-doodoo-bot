from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot import texts
from src.db.models import Animal, DefecationEvent, ReminderState
from src.db.session import async_session_factory
from src.services.notifications import notify_animal_members

logger = logging.getLogger(__name__)

FIRST_REMINDER_SECONDS = 48 * 3600
REPEAT_REMINDER_SECONDS = 8 * 3600
REMINDER_CHECK_INTERVAL_SECONDS = 60


async def get_reminder_state(
    session: AsyncSession,
    animal_id: int,
) -> ReminderState | None:
    result = await session.execute(
        select(ReminderState).where(ReminderState.animal_id == animal_id)
    )
    return result.scalar_one_or_none()


async def reset_reminder_cycle(
    session: AsyncSession,
    *,
    animal_id: int,
    last_event: DefecationEvent | None,
) -> None:
    state = await get_reminder_state(session, animal_id)

    if last_event is None:
        if state is not None:
            await session.delete(state)
        return

    if state is None:
        session.add(
            ReminderState(
                animal_id=animal_id,
                last_event_id=last_event.id,
            )
        )
        return

    state.last_event_id = last_event.id
    state.first_reminder_sent_at = None
    state.last_reminder_sent_at = None


async def _get_animals_with_last_events(
    session: AsyncSession,
) -> list[tuple[Animal, DefecationEvent]]:
    latest_event_ids = (
        select(
            DefecationEvent.animal_id,
            func.max(DefecationEvent.id).label("last_event_id"),
        )
        .group_by(DefecationEvent.animal_id)
        .subquery()
    )
    result = await session.execute(
        select(Animal, DefecationEvent)
        .join(latest_event_ids, Animal.id == latest_event_ids.c.animal_id)
        .join(
            DefecationEvent,
            DefecationEvent.id == latest_event_ids.c.last_event_id,
        )
    )
    return list(result.all())


def _is_first_reminder_due(
    *,
    last_event: DefecationEvent,
    state: ReminderState,
    now: datetime,
) -> bool:
    if state.first_reminder_sent_at is not None:
        return False
    due_at = last_event.created_at + timedelta(seconds=FIRST_REMINDER_SECONDS)
    return now >= due_at


def _is_repeat_reminder_due(
    *,
    state: ReminderState,
    now: datetime,
) -> bool:
    if state.first_reminder_sent_at is None or state.last_reminder_sent_at is None:
        return False
    due_at = state.last_reminder_sent_at + timedelta(seconds=REPEAT_REMINDER_SECONDS)
    return now >= due_at


async def _sync_state_with_last_event(
    session: AsyncSession,
    *,
    animal: Animal,
    last_event: DefecationEvent,
) -> ReminderState:
    state = await get_reminder_state(session, animal.id)
    if state is None:
        state = ReminderState(animal_id=animal.id, last_event_id=last_event.id)
        session.add(state)
        await session.flush()
        return state

    if state.last_event_id != last_event.id:
        state.last_event_id = last_event.id
        state.first_reminder_sent_at = None
        state.last_reminder_sent_at = None

    return state


async def _send_reminder(
    bot: Bot,
    session: AsyncSession,
    *,
    animal: Animal,
    state: ReminderState,
    now: datetime,
    is_first: bool,
) -> None:
    await notify_animal_members(
        bot,
        session,
        animal_id=animal.id,
        text=texts.reminder(animal.name),
    )
    if is_first:
        state.first_reminder_sent_at = now
    state.last_reminder_sent_at = now


async def process_due_reminders(session: AsyncSession, *, bot: Bot) -> None:
    now = datetime.now(timezone.utc)
    animals_with_events = await _get_animals_with_last_events(session)

    for animal, last_event in animals_with_events:
        state = await _sync_state_with_last_event(
            session,
            animal=animal,
            last_event=last_event,
        )

        if _is_first_reminder_due(last_event=last_event, state=state, now=now):
            await _send_reminder(
                bot,
                session,
                animal=animal,
                state=state,
                now=now,
                is_first=True,
            )
        elif _is_repeat_reminder_due(state=state, now=now):
            await _send_reminder(
                bot,
                session,
                animal=animal,
                state=state,
                now=now,
                is_first=False,
            )


async def run_reminder_checks(bot: Bot) -> None:
    try:
        async with async_session_factory() as session:
            await process_due_reminders(session, bot=bot)
            await session.commit()
    except Exception:
        logger.exception("Ошибка при обработке напоминаний")


def setup_reminder_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_reminder_checks,
        trigger="interval",
        seconds=REMINDER_CHECK_INTERVAL_SECONDS,
        args=[bot],
        id="reminder_checks",
        replace_existing=True,
    )
    return scheduler
