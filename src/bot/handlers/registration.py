from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot import texts
from src.bot.keyboards import (
    BTN_CREATE_PET,
    BTN_JOIN_PET,
    main_menu_keyboard,
    registration_keyboard,
    remove_keyboard,
)
from src.bot.states import RegistrationStates
from src.db.models import User
from src.services.animals import (
    PET_NAME_MAX_LENGTH,
    create_animal,
    format_recent_events,
    get_animal_by_invite_code,
    join_animal,
)
from src.services.notifications import notify_animal_members
from src.utils.users import format_user_mention

router = Router()


async def _notify_left_previous_pet(
    bot: Bot,
    session: AsyncSession,
    *,
    animal_id: int,
    user: User,
) -> None:
    mention = format_user_mention(user)
    await notify_animal_members(
        bot,
        session,
        animal_id=animal_id,
        text=texts.notify_user_left(mention),
    )


@router.message(F.text == BTN_CREATE_PET)
async def start_create_pet(message: Message, state: FSMContext) -> None:
    await state.set_state(RegistrationStates.waiting_for_pet_name)
    await message.answer(
        texts.ENTER_PET_NAME,
        reply_markup=remove_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_pet_name)
async def process_pet_name(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    db_user: User,
    bot: Bot,
) -> None:
    if message.text in {BTN_CREATE_PET, BTN_JOIN_PET}:
        if message.text == BTN_JOIN_PET:
            await state.set_state(RegistrationStates.waiting_for_invite_code)
            await message.answer(texts.ENTER_INVITE_CODE)
        else:
            await message.answer(texts.ENTER_PET_NAME)
        return

    pet_name = (message.text or "").strip()
    if not pet_name:
        await message.answer(texts.PET_NAME_EMPTY)
        return

    if len(pet_name) > PET_NAME_MAX_LENGTH:
        await message.answer(texts.pet_name_too_long(PET_NAME_MAX_LENGTH))
        return

    animal, leave_result = await create_animal(session, user=db_user, name=pet_name)

    if leave_result is not None:
        await _notify_left_previous_pet(
            bot,
            session,
            animal_id=leave_result.animal_id,
            user=db_user,
        )

    await state.clear()
    await message.answer(
        texts.pet_created(animal.invite_code),
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == BTN_JOIN_PET)
async def start_join_pet(message: Message, state: FSMContext) -> None:
    await state.set_state(RegistrationStates.waiting_for_invite_code)
    await message.answer(
        texts.ENTER_INVITE_CODE,
        reply_markup=remove_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_invite_code)
async def process_invite_code(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    db_user: User,
    bot: Bot,
) -> None:
    if message.text in {BTN_CREATE_PET, BTN_JOIN_PET}:
        if message.text == BTN_CREATE_PET:
            await state.set_state(RegistrationStates.waiting_for_pet_name)
            await message.answer(texts.ENTER_PET_NAME)
        else:
            await message.answer(texts.ENTER_INVITE_CODE)
        return

    invite_code = (message.text or "").strip()
    if not invite_code:
        await message.answer(texts.ENTER_INVITE_CODE)
        return

    animal = await get_animal_by_invite_code(session, invite_code)
    if animal is None:
        await message.answer(texts.INVITE_CODE_NOT_FOUND)
        return

    if db_user.membership is not None and db_user.membership.animal_id == animal.id:
        await state.clear()
        await message.answer(
            texts.already_joined(animal.name),
            reply_markup=main_menu_keyboard(),
        )
        return

    try:
        animal, leave_result = await join_animal(session, user=db_user, animal=animal)
    except ValueError as error:
        if str(error) == "owner_limit_reached":
            await state.clear()
            await message.answer(
                texts.OWNER_LIMIT_REACHED,
                reply_markup=registration_keyboard(),
            )
            return
        raise

    if leave_result is not None:
        await _notify_left_previous_pet(
            bot,
            session,
            animal_id=leave_result.animal_id,
            user=db_user,
        )

    mention = format_user_mention(db_user)
    await notify_animal_members(
        bot,
        session,
        animal_id=animal.id,
        text=texts.notify_user_joined(mention),
        exclude_user_id=db_user.id,
    )

    await state.clear()

    response_lines = [texts.joined_pet(animal.name)]
    recent_events = await format_recent_events(
        session,
        animal_id=animal.id,
        viewer=db_user,
        limit=5,
    )
    if recent_events:
        response_lines.append("")
        response_lines.append(recent_events)

    await message.answer(
        "\n".join(response_lines),
        reply_markup=main_menu_keyboard(),
    )
