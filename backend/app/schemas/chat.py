"""Pydantic schemas for the chat API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Request schemas ─────────────────────────────────────────────────────────

class ChatMessageSend(BaseModel):
    """POST body for sending a message."""
    message: str = Field(..., min_length=1, max_length=2000)


# ── Response schemas ────────────────────────────────────────────────────────

class ChatMessageRead(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    intent: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionRead(BaseModel):
    id: UUID
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ChatSessionDetail(ChatSessionRead):
    """Full session with messages included."""
    messages: list[ChatMessageRead] = []


class ChatSendResponse(BaseModel):
    """Response after processing a user message."""
    session_id: UUID
    user_message: ChatMessageRead
    ai_message: ChatMessageRead
    session_state: str
    intent: str | None = None
    extracted_data: dict = {}
    missing_fields: list[str] = []
    ready_to_save: bool = False


class ChatActionRead(BaseModel):
    id: UUID
    session_id: UUID
    action_type: str
    entity_type: str
    entity_id: UUID | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
