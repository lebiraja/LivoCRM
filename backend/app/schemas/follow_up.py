"""Follow-up task and outbound message Pydantic schemas."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

FollowUpReason = Literal["reminder_24h", "reminder_2h", "no_show_recovery", "lead_followup", "manual"]
FollowUpStatus = Literal["pending", "done", "skipped"]
Language = Literal["en", "ta"]
Draft = Annotated[str, Field(min_length=1, max_length=500)]
MessageBody = Annotated[str, Field(min_length=1, max_length=1000)]


class FollowUpRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    contact_id: UUID
    appointment_id: UUID | None
    reason: FollowUpReason
    due_at: datetime
    status: FollowUpStatus
    draft_en: str | None
    draft_ta: str | None
    channel: str
    created_at: datetime
    contact_name: str
    contact_phone: str


class ApproveRequest(BaseModel):
    language: Language
    body: MessageBody | None = None


class OutboundMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    task_id: UUID
    contact_id: UUID
    channel: str
    language: Language
    body: str
    status: str
    created_at: datetime


class ApproveResponse(BaseModel):
    task: FollowUpRead
    message: OutboundMessageRead
