"""Activity-related Pydantic schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ActivityType = Literal["call", "email", "meeting", "note", "task"]


class ActivityCreate(BaseModel):
    contact_id: UUID | None = None
    deal_id: UUID | None = None
    type: ActivityType = "note"
    description: str = Field(min_length=1, max_length=5000)
    occurred_at: datetime


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    contact_id: UUID | None
    deal_id: UUID | None
    type: str
    description: str
    occurred_at: datetime
    created_at: datetime
