"""Единый источник всех пользовательских текстов бота.

Формулировки зафиксированы в TECHNICAL_REQUIREMENTS.md — менять их
только синхронно с ТЗ.
"""

from __future__ import annotations

from src.db.models import DefecationLocation

# --- Старт и регистрация ---

WELCOME_NEW = "Привет! Чтобы начать, создайте питомца или присоединитесь по коду."
NEED_PET = "Сначала создайте питомца или присоединитесь по коду."
ENTER_PET_NAME = "Введите имя питомца:"
ENTER_INVITE_CODE = "Введите код приглашения:"
PET_NAME_EMPTY = "Имя не может быть пустым. Введите имя питомца:"
OWNER_LIMIT_REACHED = "Невозможно присоединиться.\nДостигнут лимит владельцев."
INVITE_CODE_NOT_FOUND = "Код не найден.\nВведите код повторно."

HELP = (
    "Этот бот помогает нескольким владельцам вести журнал "
    "дефекации питомца и получать напоминания.\n\n"
    "✅ В туалет — записать успешный поход в туалет.\n"
    "❌ Не в туалет — записать промах и указать место.\n"
    "📜 История — посмотреть журнал событий.\n"
    "↩️ Удалить последнее событие — удалить последнюю запись в журнале.\n"
    "🔑 Показать код приглашения — пригласить других владельцев.\n\n"
    "/eventlog — технический журнал изменений (не отображается в меню)."
)


def welcome_back(animal_name: str) -> str:
    return f"С возвращением! Питомец: <b>{animal_name}</b>"


def invite_code(code: str) -> str:
    return f"Код приглашения:\n<code>{code}</code>"


def pet_name_too_long(max_length: int) -> str:
    return f"Слишком длинное имя. Максимум {max_length} символов."


def pet_created(code: str) -> str:
    return f"Питомец создан.\n\nКод приглашения:\n<code>{code}</code>"


def already_joined(animal_name: str) -> str:
    return f"Вы уже подключены к питомцу {animal_name}."


def joined_pet(animal_name: str) -> str:
    return f"Вы подключены к питомцу {animal_name}."


# --- Уведомления владельцам ---

def notify_user_joined(mention: str) -> str:
    return f"{mention} присоединился к питомцу."


def notify_user_left(mention: str) -> str:
    return f"{mention} больше не является владельцем питомца."


def notify_event_toilet(mention: str) -> str:
    return f"{mention} сообщил о дефекации питомца."


def notify_event_accident(mention: str) -> str:
    return f"{mention} сообщил о дефекации питомца вне туалета."


def reminder(animal_name: str) -> str:
    return f"Давно не было записей о дефекации питомца {animal_name}."


# --- События и история ---

EVENT_CREATED = "Событие создано."
ACCIDENT_WHERE = "Где произошло?"
RATE_LIMITED = "Невозможно добавить событие.\nПопробуйте позже."
HISTORY_EMPTY = "История пуста."
DELETE_CONFIRM = "Удалить последнее событие?"
DELETE_NO_EVENTS = "Нет событий для удаления."
SCENARIO_ALREADY_COMPLETED = "Этот сценарий уже завершен."

# --- Event Log ---

EVENTLOG_EMPTY = "Журнал изменений пуст."

AUDIT_TYPE_EVENT_CREATED = "Событие создано"
AUDIT_TYPE_EVENT_DELETED = "Событие удалено"
AUDIT_TYPE_NOTIFICATION_SENT = "Уведомление отправлено"
AUDIT_TYPE_USER_JOINED = "Владелец присоединился"
AUDIT_TYPE_USER_LEFT = "Владелец покинул питомца"
AUDIT_TYPE_ERROR = "Ошибка"

AUDIT_TYPE_LABELS: dict[str, str] = {
    "EVENT_CREATED": AUDIT_TYPE_EVENT_CREATED,
    "EVENT_DELETED": AUDIT_TYPE_EVENT_DELETED,
    "NOTIFICATION_SENT": AUDIT_TYPE_NOTIFICATION_SENT,
    "USER_JOINED": AUDIT_TYPE_USER_JOINED,
    "USER_LEFT": AUDIT_TYPE_USER_LEFT,
    "ERROR": AUDIT_TYPE_ERROR,
}


def audit_user_joined(mention: str) -> str:
    return f"{mention} присоединился"


def audit_user_left(mention: str) -> str:
    return f"{mention} покинул питомца"


def audit_notification_sent(mention: str) -> str:
    return f"→ {mention}"


def audit_error(message: str) -> str:
    return message


EVENT_TITLE_TOILET = "✅ В туалет"
ACCIDENT_TITLE_PREFIX = "❌ "

LOCATION_LABELS: dict[DefecationLocation, str] = {
    DefecationLocation.TOILET: "В туалет",
    DefecationLocation.SOFA: "Диван",
    DefecationLocation.BED: "Кровать",
    DefecationLocation.CARPET: "Ковёр",
    DefecationLocation.OTHER: "Другое",
    DefecationLocation.UNKNOWN: "Неизвестно",
}


# --- Заглушки нереализованных функций ---

FEATURE_COMING_SOON = "Эта функция появится на следующем этапе."
