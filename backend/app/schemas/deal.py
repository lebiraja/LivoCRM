"""Deal-related Pydantic schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DealCreate(BaseModel):
    title: str
    contact_id: UUID | None = None
    value: float = 0
    stage: str = "lead"
    status: str = "active"
    expected_close: date | None = None
    notes: str = ""


class DealUpdate(BaseModel):
    title: str | None = None
    contact_id: UUID | None = None
    value: float | None = None
    stage: str | None = None
    status: str | None = None
    expected_close: date | None = None
    notes: str | None = None


class DealRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    contact_id: UUID | None
    title: str
    value: float
    stage: str
    status: str
    expected_close: date | None
    notes: str
    created_at: datetime
    updated_at: datetime
