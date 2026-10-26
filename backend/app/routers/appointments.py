"""Appointments router: book, list by range and status, and update status, time, fee or notes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import AwareDatetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.appointment import Appointment
from app.models.contact import Contact
from app.models.user import User
from app.schemas.appointment import AppointmentCreate, AppointmentRead, AppointmentStatus, AppointmentUpdate
from app.services.ownership import require_owned
from app.services.rate_limit import rate_limit, user_key

def _read(appointment: Appointment, contact_name: str) -> AppointmentRead:
    return AppointmentRead.model_validate(appointment).model_copy(update={"contact_name": contact_name})


async def _contact_name(db: AsyncSession, contact_id: UUID) -> str:
    return (await db.scalar(select(Contact.name).where(Contact.id == contact_id))) or ""


router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"],
    dependencies=[Depends(rate_limit("appointments", 120, 60, user_key))],
)


@router.get("", response_model=list[AppointmentRead])
async def list_appointments(
    from_: AwareDatetime | None = Query(None, alias="from"),
    to: AwareDatetime | None = None,
    status_filter: AppointmentStatus | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Appointment, Contact.name)
        .join(Contact, Contact.id == Appointment.contact_id)
        .where(Appointment.user_id == user.id)
    )
    if from_ is not None:
        stmt = stmt.where(Appointment.starts_at >= from_)
    if to is not None:
        stmt = stmt.where(Appointment.starts_at <= to)
    if status_filter is not None:
        stmt = stmt.where(Appointment.status == status_filter)
    result = await db.execute(stmt.order_by(Appointment.starts_at))
    return [_read(appointment, name) for appointment, name in result.all()]


@router.post("", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    body: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contact = await require_owned(db, Contact, body.contact_id, user)
    appointment = Appointment(**body.model_dump(), user_id=user.id)
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    return _read(appointment, contact.name)


@router.patch("/{appointment_id}", response_model=AppointmentRead)
async def update_appointment(
    appointment_id: UUID,
    body: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    appointment = await require_owned(db, Appointment, appointment_id, user)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(appointment, field, value)
    await db.commit()
    await db.refresh(appointment)
    return _read(appointment, await _contact_name(db, appointment.contact_id))
