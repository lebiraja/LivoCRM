"""Contacts CRUD router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.contact import Contact
from app.models.user import User
from app.schemas.contact import ContactCreate, ContactUpdate, ContactRead

router = APIRouter(prefix="/contacts", tags=["Contacts"])


@router.get("/", response_model=list[ContactRead])
async def list_contacts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Contact).where(Contact.user_id == user.id)
    if search:
        stmt = stmt.where(Contact.name.ilike(f"%{search}%"))
    stmt = stmt.order_by(Contact.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{contact_id}", response_model=ContactRead)
async def get_contact(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.user_id == user.id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.post("/", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
async def create_contact(
    body: ContactCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contact = Contact(**body.model_dump(), user_id=user.id)
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.patch("/{contact_id}", response_model=ContactRead)
async def update_contact(
    contact_id: UUID,
    body: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.user_id == user.id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.user_id == user.id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    await db.delete(contact)
    await db.commit()
