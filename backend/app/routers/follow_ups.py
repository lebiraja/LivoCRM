"""Follow-up queue: list pending work, draft and approve messages, or skip them."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import AwareDatetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.appointment import Appointment
from app.models.contact import Contact
from app.models.follow_up import FollowUpTask
from app.models.outbound_message import OutboundMessage
from app.models.user import User
from app.schemas.follow_up import (
    ApproveRequest,
    ApproveResponse,
    FollowUpRead,
    FollowUpStatus,
    OutboundMessageRead,
)
from app.services.draft_service import draft_follow_up
from app.services.ownership import require_owned
from app.services.rate_limit import rate_limit, user_key

router = APIRouter(
    prefix="/follow-ups",
    tags=["Follow-ups"],
    dependencies=[Depends(rate_limit("follow_ups", 120, 60, user_key))],
)


def _read(task: FollowUpTask, contact: Contact) -> FollowUpRead:
    # Validated by Pydantic: the ORM columns are plain strings bounded by CHECK constraints
    return FollowUpRead.model_validate(
        {
            "id": task.id,
            "user_id": task.user_id,
            "contact_id": task.contact_id,
            "appointment_id": task.appointment_id,
            "reason": task.reason,
            "due_at": task.due_at,
            "status": task.status,
            "draft_en": task.draft_en,
            "draft_ta": task.draft_ta,
            "channel": task.channel,
            "created_at": task.created_at,
            "contact_name": contact.name,
            "contact_phone": contact.phone,
        }
    )


async def _claim_pending(db: AsyncSession, task: FollowUpTask, new_status: str) -> bool:
    """Move a pending task to `new_status` in one conditional UPDATE, so two clicks cannot both win."""
    result = await db.execute(
        update(FollowUpTask)
        .where(FollowUpTask.id == task.id, FollowUpTask.status == "pending")
        .values(status=new_status)
    )
    if result.rowcount != 1:
        return False
    task.status = new_status
    return True


@router.get("", response_model=list[FollowUpRead])
async def list_follow_ups(
    status_filter: FollowUpStatus | None = Query(None, alias="status"),
    due_before: AwareDatetime | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(FollowUpTask, Contact)
        .join(Contact, Contact.id == FollowUpTask.contact_id)
        .where(FollowUpTask.user_id == user.id)
    )
    if status_filter is not None:
        stmt = stmt.where(FollowUpTask.status == status_filter)
    if due_before is not None:
        stmt = stmt.where(FollowUpTask.due_at <= due_before)
    rows = (await db.execute(stmt.order_by(FollowUpTask.due_at))).all()
    return [_read(task, contact) for task, contact in rows]


@router.post("/{task_id}/draft", response_model=FollowUpRead)
async def draft_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = await require_owned(db, FollowUpTask, task_id, user)
    contact = await require_owned(db, Contact, task.contact_id, user)
    if task.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Only pending tasks can be drafted")
    starts_at = None
    if task.appointment_id is not None:
        starts_at = await db.scalar(select(Appointment.starts_at).where(Appointment.id == task.appointment_id))
    # Return the connection to the pool before the slow LLM round-trip
    await db.commit()

    draft = await draft_follow_up(name=contact.name, reason=task.reason, starts_at=starts_at)
    task.draft_en = draft.en
    task.draft_ta = draft.ta
    await db.commit()
    return _read(task, contact)


@router.post("/{task_id}/approve", response_model=ApproveResponse)
async def approve_follow_up(
    task_id: UUID,
    body: ApproveRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = await require_owned(db, FollowUpTask, task_id, user)
    contact = await require_owned(db, Contact, task.contact_id, user)
    message_body = body.body or (task.draft_en if body.language == "en" else task.draft_ta)
    if not message_body:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="No draft in this language; draft it or send a body")
    if not await _claim_pending(db, task, "done"):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Task is no longer pending")

    # Simulated channel: the message is recorded, never sent outside the app
    message = OutboundMessage(
        user_id=user.id,
        task_id=task.id,
        contact_id=contact.id,
        channel=task.channel,
        language=body.language,
        body=message_body,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return ApproveResponse(task=_read(task, contact), message=OutboundMessageRead.model_validate(message))


@router.post("/{task_id}/skip", response_model=FollowUpRead)
async def skip_follow_up(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = await require_owned(db, FollowUpTask, task_id, user)
    contact = await require_owned(db, Contact, task.contact_id, user)
    if not await _claim_pending(db, task, "skipped"):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Task is no longer pending")
    await db.commit()
    return _read(task, contact)
