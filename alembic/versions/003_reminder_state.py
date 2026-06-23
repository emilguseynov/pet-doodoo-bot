"""reminder state

Revision ID: 003
Revises: 002
Create Date: 2026-06-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reminder_state",
        sa.Column("animal_id", sa.Integer(), nullable=False),
        sa.Column("last_event_id", sa.Integer(), nullable=True),
        sa.Column("first_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["animal_id"], ["animals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["last_event_id"],
            ["defecation_events.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("animal_id"),
    )


def downgrade() -> None:
    op.drop_table("reminder_state")
