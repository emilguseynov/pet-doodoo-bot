from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

BTN_CREATE_PET = "Создать питомца"
BTN_JOIN_PET = "Присоединиться к питомцу"

BTN_TOILET = "✅ В туалет"
BTN_ACCIDENT = "❌ Не в туалет"
BTN_HISTORY = "📜 История"
BTN_DELETE_LAST = "↩️ Удалить последнее событие"
BTN_INVITE_CODE = "🔑 Показать код приглашения"
BTN_HELP = "❓ Помощь"


def registration_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CREATE_PET)],
            [KeyboardButton(text=BTN_JOIN_PET)],
        ],
        resize_keyboard=True,
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_TOILET), KeyboardButton(text=BTN_ACCIDENT)],
            [KeyboardButton(text=BTN_HISTORY), KeyboardButton(text=BTN_DELETE_LAST)],
            [KeyboardButton(text=BTN_INVITE_CODE), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
