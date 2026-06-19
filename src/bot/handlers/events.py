from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot import texts
from src.bot.keyboards import (
    ACCIDENT_LOCATION_PREFIX,
    BTN_ACCIDENT,
    BTN_HISTORY,
    BTN_TOILET,
    HISTORY_PAGE_PREFIX,
    NOOP_CALLBACK,
    accident_location_keyboard,
    history_keyboard,
    main_menu_keyboard,
    registration_keyboard,
)
from src.db.models import DefecationLocation, DefecationType, User
from src.services.events import (
    HISTORY_PAGE_SIZE,
    create_event,
    format_event_list,
    get_history_page,
    is_rate_limited,
)
from src.services.notifications import notify_animal_members
from src.utils.users import format_user_mention

router = Router()


@router.message(F.text == BTN_TOILET)
async def handle_toilet(
    message: Message,
    session: AsyncSession,
    db_user: User,
    bot: Bot,
) -> None:
    if db_user.membership is None:
        await message.answer(texts.NEED_PET, reply_markup=registration_keyboard())
        return

    if await is_rate_limited(session, db_user.id):
        await message.answer(texts.RATE_LIMITED, reply_markup=main_menu_keyboard())
        return

    animal_id = db_user.membership.animal_id
    await create_event(
        session,
        user=db_user,
        animal_id=animal_id,
        event_type=DefecationType.TOILET,
        location=DefecationLocation.TOILET,
    )

    await message.answer(texts.EVENT_CREATED, reply_markup=main_menu_keyboard())

    mention = format_user_mention(db_user)
    await notify_animal_members(
        bot,
        session,
        animal_id=animal_id,
        text=texts.notify_event_toilet(mention),
        exclude_user_id=db_user.id,
    )


@router.message(F.text == BTN_ACCIDENT)
async def handle_accident(message: Message, db_user: User) -> None:
    if db_user.membership is None:
        await message.answer(texts.NEED_PET, reply_markup=registration_keyboard())
        return

    await message.answer(texts.ACCIDENT_WHERE, reply_markup=accident_location_keyboard())


@router.callback_query(F.data.startswith(f"{ACCIDENT_LOCATION_PREFIX}:"))
async def handle_accident_location(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    bot: Bot,
) -> None:
    if db_user.membership is None:
        await callback.answer()
        if isinstance(callback.message, Message):
            await callback.message.edit_text(texts.NEED_PET)
        return

    location_value = (callback.data or "").split(":", 1)[1]
    try:
        location = DefecationLocation(location_value)
    except ValueError:
        await callback.answer()
        return

    if await is_rate_limited(session, db_user.id):
        await callback.answer()
        if isinstance(callback.message, Message):
            await callback.message.edit_text(texts.RATE_LIMITED)
        return

    animal_id = db_user.membership.animal_id
    await create_event(
        session,
        user=db_user,
        animal_id=animal_id,
        event_type=DefecationType.ACCIDENT,
        location=location,
    )

    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(texts.EVENT_CREATED)

    mention = format_user_mention(db_user)
    await notify_animal_members(
        bot,
        session,
        animal_id=animal_id,
        text=texts.notify_event_accident(mention),
        exclude_user_id=db_user.id,
    )


@router.message(F.text == BTN_HISTORY)
async def handle_history(
    message: Message,
    session: AsyncSession,
    db_user: User,
) -> None:
    if db_user.membership is None:
        await message.answer(texts.NEED_PET, reply_markup=registration_keyboard())
        return

    await _render_history(message, session, db_user, page=1, edit=False)


@router.callback_query(F.data.startswith(f"{HISTORY_PAGE_PREFIX}:"))
async def handle_history_page(
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

    await _render_history(callback.message, session, db_user, page=max(page, 1), edit=True)
    await callback.answer()


@router.callback_query(F.data == NOOP_CALLBACK)
async def handle_noop(callback: CallbackQuery) -> None:
    await callback.answer()


async def _render_history(
    message: Message,
    session: AsyncSession,
    viewer: User,
    *,
    page: int,
    edit: bool,
) -> None:
    animal_id = viewer.membership.animal_id

    events, total = await get_history_page(session, animal_id=animal_id, page=page)

    if total == 0:
        text = texts.HISTORY_EMPTY
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    total_pages = (total + HISTORY_PAGE_SIZE - 1) // HISTORY_PAGE_SIZE
    if page > total_pages:
        page = total_pages
        events, total = await get_history_page(session, animal_id=animal_id, page=page)

    start_index = (page - 1) * HISTORY_PAGE_SIZE + 1
    text = format_event_list(events, viewer=viewer, start_index=start_index)
    keyboard = history_keyboard(page=page, total_pages=total_pages)

    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)
