"""Add appointments, follow_up_tasks and outbound_messages (clinic follow-up engine).

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-26 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "appointments",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fee_inr", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="booked"),
        sa.Column("notes", sa.String(500), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('booked','confirmed','completed','no_show','cancelled','rescheduled')",
            name="ck_appointments_status",
        ),
        sa.CheckConstraint("fee_inr >= 0", name="ck_appointments_fee_non_negative"),
    )
    op.create_index("ix_appointments_user_id_starts_at", "appointments", ["user_id", "starts_at"])

    op.create_table(
        "follow_up_tasks",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("appointment_id", UUID(as_uuid=True), sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("reason", sa.String(30), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("draft_en", sa.Text, nullable=True),
        sa.Column("draft_ta", sa.Text, nullable=True),
        sa.Column("channel", sa.String(20), nullable=False, server_default="simulated"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "reason IN ('reminder_24h','reminder_2h','no_show_recovery','lead_followup','manual')",
            name="ck_follow_up_tasks_reason",
        ),
        sa.CheckConstraint("status IN ('pending','done','skipped')", name="ck_follow_up_tasks_status"),
        sa.CheckConstraint("channel IN ('simulated')", name="ck_follow_up_tasks_channel"),
        sa.UniqueConstraint("appointment_id", "reason", name="uq_follow_up_tasks_appointment_reason"),
    )
    op.create_index("ix_follow_up_tasks_user_id_status_due_at", "follow_up_tasks", ["user_id", "status", "due_at"])

    op.create_table(
        "outbound_messages",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("follow_up_tasks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("contact_id", UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False, server_default="simulated"),
        sa.Column("language", sa.String(2), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="sent"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("channel IN ('simulated')", name="ck_outbound_messages_channel"),
        sa.CheckConstraint("language IN ('en','ta')", name="ck_outbound_messages_language"),
        sa.CheckConstraint("status IN ('sent')", name="ck_outbound_messages_status"),
    )


def downgrade() -> None:
    op.drop_table("outbound_messages")
    op.drop_index("ix_follow_up_tasks_user_id_status_due_at", table_name="follow_up_tasks")
    op.drop_table("follow_up_tasks")
    op.drop_index("ix_appointments_user_id_starts_at", table_name="appointments")
    op.drop_table("appointments")
