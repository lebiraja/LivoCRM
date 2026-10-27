"""Re-export all schemas."""

from typing import Generic, TypeVar

from pydantic import BaseModel

from app.schemas.user import LoginRequest, LoginResponse, UserCreate, UserRead
from app.schemas.contact import ContactCreate, ContactUpdate, ContactRead
from app.schemas.deal import DealCreate, DealUpdate, DealRead
from app.schemas.activity import ActivityCreate, ActivityRead
from app.schemas.pipeline import PipelineStageCreate, PipelineStageRead

# Generic paginated response
T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    total: int
    items: list[T]

__all__ = [
    "UserCreate", "UserRead", "LoginResponse", "LoginRequest",
    "ContactCreate", "ContactUpdate", "ContactRead",
    "DealCreate", "DealUpdate", "DealRead",
    "ActivityCreate", "ActivityRead",
    "PipelineStageCreate", "PipelineStageRead",
    "PaginatedResponse",
]
