from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot import texts
from src.bot.keyboards import (
    EVENTLOG_PAGE_PREFIX,
    eventlog_keyboard,
    main_menu_keyboard,
    registration_keyboard,
)
from src.db.models import User
from src.services.audit import prepare_audit_log_view

router = Router()


@router.message(Command("eventlog"))
async def cmd_eventlog(
    message: Message,
    session: AsyncSession,
    db_user: User,
) -> None:
    if db_user.membership is None:
        await message.answer(texts.NEED_PET, reply_markup=registration_keyboard())
        return

    await _render_eventlog(message, session, db_user, page=1, edit=False)


@router.callback_query(F.data.startswith(f"{EVENTLOG_PAGE_PREFIX}:"))
async def handle_eventlog_page(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
) -> None:
    if db_user.membership is None or not isinstance(callback.message, Message):
        await callback.answer()
        return

    try:
        page = int((callback.data or "").split(":", 1)[1])
    except ValueError:
        await callback.answer()
        return

    await _render_eventlog(
        callback.message,
        session,
        db_user,
        page=max(page, 1),
        edit=True,
    )
    await callback.answer()


async def _render_eventlog(
    message: Message,
    session: AsyncSession,
    viewer: User,
    *,
    page: int,
    edit: bool,
) -> None:
    animal_id = viewer.membership.animal_id
    text, page, total_pages = await prepare_audit_log_view(
        session,
        animal_id=animal_id,
        page=page,
        viewer=viewer,
    )

    if total_pages == 0:
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text, reply_markup=main_menu_keyboard())
        return

    keyboard = eventlog_keyboard(page=page, total_pages=total_pages)

    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)
