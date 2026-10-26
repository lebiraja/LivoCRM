"""Deal-related Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

DealStage = Literal["lead", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"]
DealStatus = Literal["active", "won", "lost"]
Title = Annotated[str, Field(min_length=1, max_length=255)]
# Matches the Numeric(12, 2) column
Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Notes = Annotated[str, Field(max_length=5000)]


class DealCreate(BaseModel):
    title: Title
    contact_id: UUID | None = None
    value: Money = Decimal(0)
    stage: DealStage = "lead"
    status: DealStatus = "active"
    expected_close: date | None = None
    notes: Notes = ""


class DealUpdate(BaseModel):
    title: Title | None = None
    contact_id: UUID | None = None
    value: Money | None = None
    stage: DealStage | None = None
    status: DealStatus | None = None
    expected_close: date | None = None
    notes: Notes | None = None

    @field_validator("title", "value", "stage", "status", "notes")
    @classmethod
    def not_null(cls, value: object) -> object:
        # Fields may be omitted, but these columns are NOT NULL
        if value is None:
            raise ValueError("may be omitted but not null")
        return value


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
