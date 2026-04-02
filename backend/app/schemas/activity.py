"""Activity-related Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ActivityCreate(BaseModel):
    contact_id: UUID | None = None
    deal_id: UUID | None = None
    type: str = "note"
    description: str
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
