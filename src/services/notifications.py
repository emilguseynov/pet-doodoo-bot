from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import AnimalMember, AuditLogType, User
from src.services.audit import log_audit, log_error

logger = logging.getLogger(__name__)


async def get_animal_members(
    session: AsyncSession,
    animal_id: int,
) -> list[AnimalMember]:
    result = await session.execute(
        select(AnimalMember)
        .where(AnimalMember.animal_id == animal_id)
        .options(selectinload(AnimalMember.user))
    )
    return list(result.scalars().all())


async def notify_animal_members(
    bot: Bot,
    session: AsyncSession,
    *,
    animal_id: int,
    text: str,
    exclude_user_id: int | None = None,
) -> None:
    members = await get_animal_members(session, animal_id)

    for member in members:
        if exclude_user_id is not None and member.user_id == exclude_user_id:
            continue

        try:
            await bot.send_message(chat_id=member.user.telegram_id, text=text)
            await log_audit(
                session,
                animal_id=animal_id,
                log_type=AuditLogType.NOTIFICATION_SENT,
                payload={
                    "recipient_user_id": member.user_id,
                    "text": text,
                },
            )
        except TelegramAPIError as error:
            logger.warning(
                "Не удалось отправить уведомление user_id=%s: %s",
                member.user_id,
                error,
            )
            await log_error(
                session,
                animal_id=animal_id,
                message="notification_delivery_failed",
                details={
                    "recipient_user_id": member.user_id,
                    "error": str(error),
                    "text": text,
                },
            )
