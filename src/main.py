import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from src.bot.handlers import setup_routers
from src.bot.middlewares.db import DatabaseMiddleware, UserMiddleware
from src.config import settings
from src.db.migrations import run_migrations
from src.services.scenarios import run_timeout_worker

def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True,
    )


_configure_logging()
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Применяем миграции базы данных...")
    await asyncio.to_thread(run_migrations)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.update.middleware(DatabaseMiddleware())
    dispatcher.update.middleware(UserMiddleware())
    dispatcher.include_router(setup_routers())

    timeout_task = asyncio.create_task(run_timeout_worker(bot))
    logger.info("Бот запущен, ждём сообщения...")
    try:
        await dispatcher.start_polling(bot)
    finally:
        timeout_task.cancel()
        with suppress(asyncio.CancelledError):
            await timeout_task


if __name__ == "__main__":
    asyncio.run(main())
