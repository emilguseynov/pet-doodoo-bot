from __future__ import annotations

from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot import texts
from src.db.models import AuditLogEntry, AuditLogType, User
from src.utils.event_format import event_title_from_values
from src.utils.users import format_user_mention

AUDIT_LOG_PAGE_SIZE = 5


async def log_audit(
    session: AsyncSession,
    *,
    animal_id: int,
    log_type: AuditLogType,
    payload: dict | None = None,
) -> None:
    from src.db.models import AuditLogEntry

    session.add(
        AuditLogEntry(
            animal_id=animal_id,
            type=log_type.value,
            payload=payload or {},
        )
    )


async def log_error(
    session: AsyncSession,
    *,
    animal_id: int,
    message: str,
    details: dict | None = None,
) -> None:
    payload = {"message": message, **(details or {})}
    await log_audit(session, animal_id=animal_id, log_type=AuditLogType.ERROR, payload=payload)


def _collect_user_ids(entries: list[AuditLogEntry]) -> set[int]:
    user_ids: set[int] = set()
    for entry in entries:
        payload = entry.payload or {}
        for key in ("user_id", "recipient_user_id"):
            value = payload.get(key)
            if isinstance(value, int):
                user_ids.add(value)
    return user_ids


async def _load_users_by_id(
    session: AsyncSession,
    user_ids: set[int],
) -> dict[int, User]:
    if not user_ids:
        return {}
    result = await session.execute(select(User).where(User.id.in_(user_ids)))
    return {user.id: user for user in result.scalars().all()}


def _format_user_ref(user_id: int, users_by_id: dict[int, User]) -> str:
    user = users_by_id.get(user_id)
    if user is None:
        return f"user#{user_id}"
    return format_user_mention(user)


def _format_entry_details(
    entry: AuditLogEntry,
    *,
    users_by_id: dict[int, User],
) -> str:
    payload = entry.payload or {}
    log_type = entry.type

    if log_type == AuditLogType.EVENT_CREATED:
        user_id = payload.get("user_id")
        title = event_title_from_values(
            event_type=str(payload.get("type", "")),
            location=str(payload.get("location", "")),
        )
        if isinstance(user_id, int):
            return f"{_format_user_ref(user_id, users_by_id)} — {title}"
        return title

    if log_type == AuditLogType.EVENT_DELETED:
        user_id = payload.get("user_id")
        title = event_title_from_values(
            event_type=str(payload.get("type", "")),
            location=str(payload.get("location", "")),
        )
        if isinstance(user_id, int):
            return f"{_format_user_ref(user_id, users_by_id)} — {title}"
        return title

    if log_type == AuditLogType.USER_JOINED:
        user_id = payload.get("user_id")
        if isinstance(user_id, int):
            return texts.audit_user_joined(_format_user_ref(user_id, users_by_id))
        return texts.AUDIT_TYPE_USER_JOINED

    if log_type == AuditLogType.USER_LEFT:
        user_id = payload.get("user_id")
        if isinstance(user_id, int):
            return texts.audit_user_left(_format_user_ref(user_id, users_by_id))
        return texts.AUDIT_TYPE_USER_LEFT

    if log_type == AuditLogType.NOTIFICATION_SENT:
        recipient_id = payload.get("recipient_user_id")
        if isinstance(recipient_id, int):
            return texts.audit_notification_sent(
                _format_user_ref(recipient_id, users_by_id),
            )
        return texts.AUDIT_TYPE_NOTIFICATION_SENT

    if log_type == AuditLogType.ERROR:
        message = payload.get("message")
        if isinstance(message, str) and message:
            return texts.audit_error(message)
        return texts.AUDIT_TYPE_ERROR

    return entry.type


def format_audit_log_list(
    entries: list[AuditLogEntry],
    *,
    viewer: User,
    users_by_id: dict[int, User],
    start_index: int = 1,
) -> str:
    tz = ZoneInfo(viewer.timezone)
    lines: list[str] = []
    for offset, entry in enumerate(entries):
        index = start_index + offset
        local_time = entry.created_at.astimezone(tz)
        timestamp = local_time.strftime("%d.%m.%Y %H:%M")
        type_label = texts.AUDIT_TYPE_LABELS.get(entry.type, entry.type)
        details = _format_entry_details(entry, users_by_id=users_by_id)
        lines.append(f"{index}. {type_label}\n{timestamp}\n{details}")
    return "\n\n".join(lines)


async def count_audit_entries(session: AsyncSession, animal_id: int) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(AuditLogEntry)
        .where(AuditLogEntry.animal_id == animal_id)
    )
    return result.scalar_one()


async def get_audit_log_page(
    session: AsyncSession,
    *,
    animal_id: int,
    page: int,
) -> tuple[list[AuditLogEntry], int]:
    total = await count_audit_entries(session, animal_id)
    offset = (page - 1) * AUDIT_LOG_PAGE_SIZE
    result = await session.execute(
        select(AuditLogEntry)
        .where(AuditLogEntry.animal_id == animal_id)
        .order_by(AuditLogEntry.created_at.desc())
        .offset(offset)
        .limit(AUDIT_LOG_PAGE_SIZE)
    )
    entries = list(result.scalars().all())
    return entries, total


async def prepare_audit_log_view(
    session: AsyncSession,
    *,
    animal_id: int,
    page: int,
    viewer: User,
) -> tuple[str, int, int]:
    """Возвращает (текст, текущая страница, всего страниц)."""
    entries, total = await get_audit_log_page(session, animal_id=animal_id, page=page)

    if total == 0:
        return texts.EVENTLOG_EMPTY, 1, 0

    total_pages = (total + AUDIT_LOG_PAGE_SIZE - 1) // AUDIT_LOG_PAGE_SIZE
    if page > total_pages:
        page = total_pages
        entries, total = await get_audit_log_page(session, animal_id=animal_id, page=page)

    users_by_id = await _load_users_by_id(session, _collect_user_ids(entries))
    start_index = (page - 1) * AUDIT_LOG_PAGE_SIZE + 1
    text = format_audit_log_list(
        entries,
        viewer=viewer,
        users_by_id=users_by_id,
        start_index=start_index,
    )
    return text, page, total_pages
