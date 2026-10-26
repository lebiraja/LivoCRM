"""Tenant checks for foreign-key references in request bodies (SEC-09)."""

from __future__ import annotations

from typing import TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.follow_up import FollowUpTask
from app.models.user import User

OwnedModel = TypeVar("OwnedModel", Contact, Deal, Appointment, FollowUpTask)


async def require_owned(db: AsyncSession, model: type[OwnedModel], entity_id: UUID, user: User) -> OwnedModel:
    """Return the referenced row if `user` owns it, else 404 (same answer as a missing id)."""
    row = await db.scalar(select(model).where(model.id == entity_id, model.user_id == user.id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{model.__name__} not found")
    return row
