"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2025-04-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Users ──
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("plan", sa.String(20), nullable=False, server_default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── Contacts ──
    op.create_table(
        "contacts",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, server_default=""),
        sa.Column("phone", sa.String(50), nullable=False, server_default=""),
        sa.Column("company", sa.String(255), nullable=False, server_default=""),
        sa.Column("tags", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("lead_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── Deals ──
    op.create_table(
        "deals",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("contact_id", UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("value", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("stage", sa.String(30), nullable=False, server_default="lead"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("expected_close", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── Activities ──
    op.create_table(
        "activities",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("contact_id", UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("deal_id", UUID(as_uuid=True), sa.ForeignKey("deals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(20), nullable=False, server_default="note"),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── Pipeline Stages ──
    op.create_table(
        "pipeline_stages",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("pipeline_stages")
    op.drop_table("activities")
    op.drop_table("deals")
    op.drop_table("contacts")
    op.drop_table("users")
