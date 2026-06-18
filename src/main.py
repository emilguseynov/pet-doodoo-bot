import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from src.bot.handlers import setup_routers
from src.bot.middlewares.db import DatabaseMiddleware, UserMiddleware
from src.config import settings
from src.db.migrations import run_migrations

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

    logger.info("Бот запущен, ждём сообщения...")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
