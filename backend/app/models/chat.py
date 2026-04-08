"""Chat‐related ORM models: sessions, messages, and AI actions."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ChatSession(Base):
    """One continuous conversation between a user and Livo."""

    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Chat")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), onupdate=datetime.utcnow, nullable=False
    )

    # relationships
    user = relationship("User", backref="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", order_by="ChatMessage.created_at")

    __table_args__ = (
        CheckConstraint(
            "status IN ('active','archived','closed')",
            name="ck_chat_sessions_status"
        ),
    )


class ChatMessage(Base):
    """A single message in a chat session — from user or assistant."""

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(30), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    # relationships
    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        CheckConstraint(
            "role IN ('user','assistant')",
            name="ck_chat_messages_role"
        ),
    )


class ChatAction(Base):
    """Records a CRM entity created/updated through chat (audit trail)."""

    __tablename__ = "chat_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)  # "ADD_CONTACT", etc.
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)  # "contact", "deal", "activity"
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    # relationships
    session = relationship("ChatSession", backref="actions")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','confirmed','rejected','completed')",
            name="ck_chat_actions_status"
        ),
        CheckConstraint(
            "entity_type IN ('contact','deal','activity')",
            name="ck_chat_actions_entity_type"
        ),
    )
