from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot import texts
from src.bot.keyboards import (
    BTN_HELP,
    BTN_INVITE_CODE,
    main_menu_keyboard,
    registration_keyboard,
)
from src.db.models import User

router = Router()


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    db_user: User,
) -> None:
    await state.clear()

    if db_user.membership is not None:
        animal_name = db_user.membership.animal.name
        await message.answer(
            texts.welcome_back(animal_name),
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(
        texts.WELCOME_NEW,
        reply_markup=registration_keyboard(),
    )


@router.message(F.text == BTN_INVITE_CODE)
async def show_invite_code(message: Message, db_user: User) -> None:
    if db_user.membership is None:
        await message.answer(
            texts.NEED_PET,
            reply_markup=registration_keyboard(),
        )
        return

    await message.answer(
        texts.invite_code(db_user.membership.animal.invite_code),
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == BTN_HELP)
async def show_help(message: Message, db_user: User) -> None:
    keyboard = (
        main_menu_keyboard()
        if db_user.membership is not None
        else registration_keyboard()
    )
    await message.answer(texts.HELP, reply_markup=keyboard)
