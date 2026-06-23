from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

BTN_CREATE_PET = "Создать питомца"
BTN_JOIN_PET = "Присоединиться к питомцу"

BTN_TOILET = "✅ В туалет"
BTN_ACCIDENT = "❌ Не в туалет"
BTN_HISTORY = "📜 История"
BTN_DELETE_LAST = "↩️ Удалить последнее событие"
BTN_INVITE_CODE = "🔑 Показать код приглашения"
BTN_HELP = "❓ Помощь"

ACCIDENT_LOCATION_PREFIX = "acc_loc"
HISTORY_PAGE_PREFIX = "hist"
EVENTLOG_PAGE_PREFIX = "evlog"
DELETE_CONFIRM_YES = "del_yes"
DELETE_CONFIRM_NO = "del_no"
NOOP_CALLBACK = "noop"

_ACCIDENT_LOCATIONS: list[tuple[str, str]] = [
    ("Диван", "sofa"),
    ("Кровать", "bed"),
    ("Ковёр", "carpet"),
    ("Другое", "other"),
]


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


def accident_location_keyboard(*, scenario_id: int) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=label,
            callback_data=f"{ACCIDENT_LOCATION_PREFIX}:{scenario_id}:{value}",
        )
        for label, value in _ACCIDENT_LOCATIONS
    ]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def history_keyboard(*, page: int, total_pages: int) -> InlineKeyboardMarkup | None:
    if total_pages <= 1:
        return None

    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=f"{HISTORY_PAGE_PREFIX}:{page - 1}",
            )
        )
    nav.append(
        InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data=NOOP_CALLBACK,
        )
    )
    if page < total_pages:
        nav.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"{HISTORY_PAGE_PREFIX}:{page + 1}",
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[nav])


def eventlog_keyboard(*, page: int, total_pages: int) -> InlineKeyboardMarkup | None:
    if total_pages <= 1:
        return None

    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=f"{EVENTLOG_PAGE_PREFIX}:{page - 1}",
            )
        )
    nav.append(
        InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data=NOOP_CALLBACK,
        )
    )
    if page < total_pages:
        nav.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"{EVENTLOG_PAGE_PREFIX}:{page + 1}",
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[nav])


def delete_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data=DELETE_CONFIRM_YES),
                InlineKeyboardButton(text="Нет", callback_data=DELETE_CONFIRM_NO),
            ],
        ]
    )
