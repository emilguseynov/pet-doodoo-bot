from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import AuditLogType, User


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
