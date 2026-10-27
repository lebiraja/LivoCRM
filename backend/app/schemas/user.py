"""User-related Pydantic schemas."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, field_validator

# Emails are stored and compared lower-cased (unique index on lower(email))
NormalizedEmail = Annotated[EmailStr, AfterValidator(str.lower)]


class UserCreate(BaseModel):
    email: NormalizedEmail
    password: str
    full_name: str = Field("", max_length=255)

    @field_validator("password")
    @classmethod
    def password_length(cls, value: str) -> str:
        # bcrypt only uses the first 72 bytes, so longer passwords are rejected, not truncated
        if not 10 <= len(value.encode("utf-8")) <= 72:
            raise ValueError("Password must be 10 to 72 bytes long")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    plan: str
    created_at: datetime


class LoginResponse(BaseModel):
    authenticated: bool = True


class LoginRequest(BaseModel):
    email: NormalizedEmail
    password: str
