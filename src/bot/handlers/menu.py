from aiogram import F, Router
from aiogram.types import Message

from src.bot import texts
from src.bot.keyboards import BTN_DELETE_LAST, main_menu_keyboard
from src.db.models import User

router = Router()


@router.message(F.text == BTN_DELETE_LAST)
async def delete_last_placeholder(message: Message, db_user: User) -> None:
    keyboard = main_menu_keyboard() if db_user.membership else None
    await message.answer(
        texts.FEATURE_COMING_SOON,
        reply_markup=keyboard,
    )
