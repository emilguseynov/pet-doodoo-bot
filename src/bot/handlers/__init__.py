from aiogram import Router

from src.bot.handlers.menu import router as menu_router
from src.bot.handlers.registration import router as registration_router
from src.bot.handlers.start import router as start_router


def setup_routers() -> Router:
    root_router = Router()
    root_router.include_router(registration_router)
    root_router.include_router(menu_router)
    root_router.include_router(start_router)
    return root_router
