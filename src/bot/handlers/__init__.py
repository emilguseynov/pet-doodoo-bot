from aiogram import Router

from src.bot.handlers.eventlog import router as eventlog_router
from src.bot.handlers.events import router as events_router
from src.bot.handlers.registration import router as registration_router
from src.bot.handlers.start import router as start_router


def setup_routers() -> Router:
    root_router = Router()
    root_router.include_router(registration_router)
    root_router.include_router(events_router)
    root_router.include_router(eventlog_router)
    root_router.include_router(start_router)
    return root_router
