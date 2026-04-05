"""Deal ORM model."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, server_default="0")
    stage: Mapped[str] = mapped_column(String(30), nullable=False, server_default="lead")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    expected_close: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # ── AI-assisted creation provenance ─────────────────────────────────────
    # "manual" (default) | "ai_chat" — how this record was created
    source: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="manual"
    )
    # FK to chat_sessions.id — populated when source == "ai_chat"
    ai_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), onupdate=datetime.utcnow, nullable=False
    )

    # relationships
    user = relationship("User", back_populates="deals")
    contact = relationship("Contact", back_populates="deals")
    activities = relationship("Activity", back_populates="deal")

