"""Add source and ai_session_id columns to contacts and deals

Revision ID: 0003
Revises: 0002
Create Date: 2025-07-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── contacts ──────────────────────────────────────────────────────────────
    op.add_column(
        "contacts",
        sa.Column("source", sa.String(30), nullable=False, server_default="manual"),
    )
    op.add_column(
        "contacts",
        sa.Column(
            "ai_session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_contacts_ai_session_id", "contacts", ["ai_session_id"], unique=False
    )

    # ── deals ─────────────────────────────────────────────────────────────────
    op.add_column(
        "deals",
        sa.Column("source", sa.String(30), nullable=False, server_default="manual"),
    )
    op.add_column(
        "deals",
        sa.Column(
            "ai_session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_deals_ai_session_id", "deals", ["ai_session_id"], unique=False
    )


def downgrade() -> None:
    # deals
    op.drop_index("ix_deals_ai_session_id", table_name="deals")
    op.drop_column("deals", "ai_session_id")
    op.drop_column("deals", "source")
    # contacts
    op.drop_index("ix_contacts_ai_session_id", table_name="contacts")
    op.drop_column("contacts", "ai_session_id")
    op.drop_column("contacts", "source")
