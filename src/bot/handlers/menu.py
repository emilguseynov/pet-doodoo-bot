from aiogram import F, Router
from aiogram.types import Message

from src.bot.keyboards import (
    BTN_ACCIDENT,
    BTN_DELETE_LAST,
    BTN_HISTORY,
    BTN_TOILET,
    main_menu_keyboard,
)
from src.db.models import User

router = Router()


@router.message(F.text.in_({BTN_TOILET, BTN_ACCIDENT, BTN_HISTORY, BTN_DELETE_LAST}))
async def stage_two_placeholder(message: Message, db_user: User) -> None:
    keyboard = main_menu_keyboard() if db_user.membership else None
    await message.answer(
        "Эта функция появится на этапе 2.",
        reply_markup=keyboard,
    )
