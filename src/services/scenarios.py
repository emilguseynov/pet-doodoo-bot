from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.bot import texts
from src.db.models import (
    DefecationLocation,
    DefecationType,
    PendingScenario,
)
from src.db.session import async_session_factory
from src.services.events import try_create_event
from src.services.notifications import notify_animal_members
from src.utils.users import format_user_mention

logger = logging.getLogger(__name__)

SCENARIO_TIMEOUT_SECONDS = 3600
TIMEOUT_CHECK_INTERVAL_SECONDS = 60


async def start_accident_scenario(
    session: AsyncSession,
    *,
    user_id: int,
    animal_id: int,
) -> PendingScenario:
    await cancel_user_scenario(session, user_id=user_id)

    scenario = PendingScenario(user_id=user_id, animal_id=animal_id)
    session.add(scenario)
    await session.flush()
    await session.refresh(scenario)
    return scenario


async def cancel_user_scenario(session: AsyncSession, *, user_id: int) -> None:
    result = await session.execute(
        select(PendingScenario).where(PendingScenario.user_id == user_id)
    )
    scenario = result.scalar_one_or_none()
    if scenario is not None:
        await session.delete(scenario)
        await session.flush()


async def get_user_scenario(
    session: AsyncSession,
    *,
    user_id: int,
    scenario_id: int,
) -> PendingScenario | None:
    result = await session.execute(
        select(PendingScenario).where(
            PendingScenario.id == scenario_id,
            PendingScenario.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def complete_scenario(session: AsyncSession, scenario: PendingScenario) -> None:
    await session.delete(scenario)


async def get_expired_scenarios(session: AsyncSession) -> list[PendingScenario]:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=SCENARIO_TIMEOUT_SECONDS)
    result = await session.execute(
        select(PendingScenario)
        .where(PendingScenario.started_at <= cutoff)
        .options(selectinload(PendingScenario.user))
    )
    return list(result.scalars().all())


async def process_expired_scenarios(session: AsyncSession, *, bot: Bot) -> None:
    expired = await get_expired_scenarios(session)
    for scenario in expired:
        user = scenario.user
        event = await try_create_event(
            session,
            user=user,
            animal_id=scenario.animal_id,
            event_type=DefecationType.ACCIDENT,
            location=DefecationLocation.UNKNOWN,
        )
        if event is None:
            continue
        await complete_scenario(session, scenario)

        mention = format_user_mention(user)
        await notify_animal_members(
            bot,
            session,
            animal_id=scenario.animal_id,
            text=texts.notify_event_accident(mention),
            exclude_user_id=user.id,
        )


async def run_timeout_worker(
    bot: Bot,
    *,
    interval_seconds: int = TIMEOUT_CHECK_INTERVAL_SECONDS,
) -> None:
    while True:
        try:
            async with async_session_factory() as session:
                await process_expired_scenarios(session, bot=bot)
                await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Ошибка при обработке просроченных сценариев")

        await asyncio.sleep(interval_seconds)
