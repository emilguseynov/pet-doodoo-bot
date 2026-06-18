from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import async_session_factory


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with async_session_factory() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        telegram_user: TelegramUser | None = data.get("event_from_user")
        session: AsyncSession | None = data.get("session")

        if telegram_user is None or session is None:
            return await handler(event, data)

        from src.services.users import get_or_create_user

        display_name = telegram_user.full_name or "Пользователь"
        user = await get_or_create_user(
            session,
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            display_name=display_name,
        )
        data["db_user"] = user
        return await handler(event, data)
