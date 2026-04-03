"""Contact ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    company: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    tags: Mapped[list] = mapped_column(JSON, nullable=False, server_default="[]")
    lead_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
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
    user = relationship("User", back_populates="contacts")
    deals = relationship("Deal", back_populates="contact")
    activities = relationship("Activity", back_populates="contact")

