"""FollowUpTask ORM model: one recovery, reminder or manual action for a clinic contact."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    draft_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_ta: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, server_default="simulated")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "reason IN ('reminder_24h','reminder_2h','no_show_recovery','lead_followup','manual')",
            name="ck_follow_up_tasks_reason",
        ),
        CheckConstraint("status IN ('pending','done','skipped')", name="ck_follow_up_tasks_status"),
        CheckConstraint("channel IN ('simulated')", name="ck_follow_up_tasks_channel"),
        # Generation is idempotent: one task per appointment and reason
        UniqueConstraint("appointment_id", "reason", name="uq_follow_up_tasks_appointment_reason"),
        Index("ix_follow_up_tasks_user_id_status_due_at", "user_id", "status", "due_at"),
    )
