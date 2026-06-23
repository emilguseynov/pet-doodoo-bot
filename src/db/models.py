from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class DefecationType(StrEnum):
    TOILET = "toilet"
    ACCIDENT = "accident"


class DefecationLocation(StrEnum):
    TOILET = "toilet"
    SOFA = "sofa"
    BED = "bed"
    CARPET = "carpet"
    OTHER = "other"
    UNKNOWN = "unknown"


class AuditLogType(StrEnum):
    EVENT_CREATED = "EVENT_CREATED"
    EVENT_DELETED = "EVENT_DELETED"
    NOTIFICATION_SENT = "NOTIFICATION_SENT"
    USER_JOINED = "USER_JOINED"
    USER_LEFT = "USER_LEFT"
    ERROR = "ERROR"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    membership: Mapped[AnimalMember | None] = relationship(
        back_populates="user",
        uselist=False,
        lazy="selectin",
    )
    pending_scenario: Mapped[PendingScenario | None] = relationship(
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    created_events: Mapped[list[DefecationEvent]] = relationship(
        back_populates="created_by",
    )


class Animal(Base):
    __tablename__ = "animals"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    invite_code: Mapped[str] = mapped_column(String(8), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    members: Mapped[list[AnimalMember]] = relationship(
        back_populates="animal",
        cascade="all, delete-orphan",
    )
    events: Mapped[list[DefecationEvent]] = relationship(
        back_populates="animal",
        cascade="all, delete-orphan",
        order_by="DefecationEvent.created_at.desc()",
    )
    audit_logs: Mapped[list[AuditLogEntry]] = relationship(
        back_populates="animal",
        cascade="all, delete-orphan",
    )


class AnimalMember(Base):
    __tablename__ = "animal_members"
    __table_args__ = (
        Index("ix_animal_members_animal_id", "animal_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    animal: Mapped[Animal] = relationship(
        back_populates="members",
        lazy="selectin",
    )
    user: Mapped[User] = relationship(back_populates="membership")


class PendingScenario(Base):
    __tablename__ = "pending_scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
    )
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="pending_scenario", lazy="selectin")


class DefecationEvent(Base):
    __tablename__ = "defecation_events"
    __table_args__ = (
        Index("ix_defecation_events_animal_created", "animal_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"))
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    type: Mapped[str] = mapped_column(String(16))
    location: Mapped[str] = mapped_column(String(16))

    animal: Mapped[Animal] = relationship(back_populates="events")
    created_by: Mapped[User] = relationship(back_populates="created_events")


class AuditLogEntry(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_animal_created", "animal_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    animal: Mapped[Animal] = relationship(back_populates="audit_logs")
