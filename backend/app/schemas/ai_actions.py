"""Validated shapes for CRM writes proposed by the AI (SEC-05).

LLM output is untrusted: every chat save is validated against one of these
models before it touches the database. Unknown keys are rejected, enums are
closed and money is Decimal, so a bad value becomes a clarification for the
user instead of a CHECK-constraint failure.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.activity import ActivityType
from app.schemas.deal import DealStage

Name = Annotated[str, Field(min_length=1, max_length=255)]
OptionalName = Annotated[str, Field(max_length=255)]
Notes = Annotated[str, Field(max_length=5000)]


class _AIAction(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ContactFields(_AIAction):
    """ADD_CONTACT, and UPDATE_CONTACT where `name` identifies the record."""

    name: Name
    email: EmailStr | Literal[""] = ""
    phone: str = Field("", max_length=50)
    company: OptionalName = ""
    tags: list[Annotated[str, Field(min_length=1, max_length=50)]] = Field(default_factory=list, max_length=20)
    notes: Notes = ""


class DealFields(_AIAction):
    """ADD_DEAL, and UPDATE_DEAL where `title` identifies the record."""

    title: Name
    value: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    stage: DealStage | None = None
    contact_name: OptionalName = ""
    expected_close: date | None = None
    notes: Notes = ""


class ActivityFields(_AIAction):
    """LOG_ACTIVITY."""

    activity_type: ActivityType
    description: Annotated[str, Field(min_length=1, max_length=5000)]
    contact_name: OptionalName = ""
    deal_title: OptionalName = ""


ACTION_MODELS: dict[str, type[_AIAction]] = {
    "ADD_CONTACT": ContactFields,
    "UPDATE_CONTACT": ContactFields,
    "ADD_DEAL": DealFields,
    "UPDATE_DEAL": DealFields,
    "LOG_ACTIVITY": ActivityFields,
}
