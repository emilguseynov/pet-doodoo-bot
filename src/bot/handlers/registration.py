from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

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
        text=f"{mention} больше не является владельцем питомца.",
    )


@router.message(F.text == BTN_CREATE_PET)
async def start_create_pet(message: Message, state: FSMContext) -> None:
    await state.set_state(RegistrationStates.waiting_for_pet_name)
    await message.answer(
        "Введите имя питомца:",
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
            await message.answer("Введите код приглашения:")
        else:
            await message.answer("Введите имя питомца:")
        return

    pet_name = (message.text or "").strip()
    if not pet_name:
        await message.answer("Имя не может быть пустым. Введите имя питомца:")
        return

    if len(pet_name) > PET_NAME_MAX_LENGTH:
        await message.answer(
            f"Слишком длинное имя. Максимум {PET_NAME_MAX_LENGTH} символов."
        )
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
        "Питомец создан.\n\n"
        f"Код приглашения:\n<code>{animal.invite_code}</code>",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == BTN_JOIN_PET)
async def start_join_pet(message: Message, state: FSMContext) -> None:
    await state.set_state(RegistrationStates.waiting_for_invite_code)
    await message.answer(
        "Введите код приглашения:",
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
            await message.answer("Введите имя питомца:")
        else:
            await message.answer("Введите код приглашения:")
        return

    invite_code = (message.text or "").strip()
    if not invite_code:
        await message.answer("Введите код приглашения:")
        return

    animal = await get_animal_by_invite_code(session, invite_code)
    if animal is None:
        await message.answer("Код не найден.\nВведите код повторно.")
        return

    if db_user.membership is not None and db_user.membership.animal_id == animal.id:
        await state.clear()
        await message.answer(
            f"Вы уже подключены к питомцу {animal.name}.",
            reply_markup=main_menu_keyboard(),
        )
        return

    try:
        animal, leave_result = await join_animal(session, user=db_user, animal=animal)
    except ValueError as error:
        if str(error) == "owner_limit_reached":
            await state.clear()
            await message.answer(
                "Невозможно присоединиться.\nДостигнут лимит владельцев.",
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
        text=f"{mention} присоединился к питомцу.",
        exclude_user_id=db_user.id,
    )

    await state.clear()

    response_lines = [f"Вы подключены к питомцу {animal.name}."]
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
