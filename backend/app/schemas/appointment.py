"""Appointment-related Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

AppointmentStatus = Literal["booked", "confirmed", "completed", "no_show", "cancelled", "rescheduled"]
Money = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
Notes = Annotated[str, Field(max_length=500)]


class AppointmentCreate(BaseModel):
    contact_id: UUID
    starts_at: AwareDatetime
    fee_inr: Money
    notes: Notes = ""


class AppointmentUpdate(BaseModel):
    starts_at: AwareDatetime | None = None
    fee_inr: Money | None = None
    status: AppointmentStatus | None = None
    notes: Notes | None = None

    @field_validator("*")
    @classmethod
    def not_null(cls, value: object) -> object:
        # Fields may be omitted, but every appointment column is NOT NULL
        if value is None:
            raise ValueError("may be omitted but not null")
        return value


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    contact_id: UUID
    contact_name: str = ""
    starts_at: datetime
    fee_inr: Decimal
    status: AppointmentStatus
    notes: str
    created_at: datetime
    updated_at: datetime
