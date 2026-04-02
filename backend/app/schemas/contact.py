"""Contact-related Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ContactCreate(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    company: str = ""
    tags: list[str] = []
    notes: str = ""


class ContactUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    tags: list[str] | None = None
    notes: str | None = None


class ContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    email: str
    phone: str
    company: str
    tags: list
    lead_score: int
    notes: str
    created_at: datetime
    updated_at: datetime
