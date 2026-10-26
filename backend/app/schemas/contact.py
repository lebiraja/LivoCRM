"""Contact-related Pydantic schemas."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Name = Annotated[str, Field(min_length=1, max_length=255)]
Email = EmailStr | Literal[""]
Phone = Annotated[str, Field(max_length=50)]
Company = Annotated[str, Field(max_length=255)]
Tags = Annotated[list[Annotated[str, Field(min_length=1, max_length=50)]], Field(max_length=20)]
Notes = Annotated[str, Field(max_length=5000)]


class ContactCreate(BaseModel):
    name: Name
    email: Email = ""
    phone: Phone = ""
    company: Company = ""
    tags: Tags = []
    notes: Notes = ""


class ContactUpdate(BaseModel):
    name: Name | None = None
    email: Email | None = None
    phone: Phone | None = None
    company: Company | None = None
    tags: Tags | None = None
    notes: Notes | None = None

    @field_validator("*")
    @classmethod
    def not_null(cls, value: object) -> object:
        # Fields may be omitted, but every contact column is NOT NULL
        if value is None:
            raise ValueError("may be omitted but not null")
        return value


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
