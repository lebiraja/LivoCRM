"""AI router — lead scoring and AI-generated insights."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.contact import Contact
from app.models.activity import Activity
from app.models.deal import Deal
from app.models.user import User
from app.services.bedrock_service import get_insights, llm_slots
from app.services.lead_scoring import score_contact

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/score/{contact_id}")
async def lead_score(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Score a contact using the offline ML model."""
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.user_id == user.id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Gather activity stats
    activity_count = (await db.execute(
        select(func.count()).select_from(Activity).where(Activity.contact_id == contact_id)
    )).scalar() or 0

    contact_data = {
        "company": contact.company,
        "phone": contact.phone,
        "email": contact.email,
        "tags": contact.tags,
        "notes": contact.notes,
        "activity_count": activity_count,
    }
    result = score_contact(contact_data)
    return {"contact_id": str(contact_id), **result}


@router.post("/insights")
async def insights(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate CRM insights with Bedrock and deterministic fallback."""
    contacts = (await db.execute(
        select(func.count()).select_from(Contact).where(Contact.user_id == user.id)
    )).scalar() or 0

    deals = (await db.execute(
        select(func.count()).select_from(Deal).where(Deal.user_id == user.id)
    )).scalar() or 0

    activities = (await db.execute(
        select(func.count()).select_from(Activity).where(Activity.user_id == user.id)
    )).scalar() or 0

    pipeline_value = (await db.execute(
        select(func.coalesce(func.sum(Deal.value), 0)).where(
            Deal.user_id == user.id, Deal.status == "active"
        )
    )).scalar() or 0

    proposal_deals = (await db.execute(
        select(func.count()).select_from(Deal).where(
            Deal.user_id == user.id, Deal.stage == "proposal", Deal.status == "active"
        )
    )).scalar() or 0

    metrics = {
        "contacts": int(contacts),
        "deals": int(deals),
        "activities": int(activities),
        "pipeline_value": float(pipeline_value),
        "proposal_deals": int(proposal_deals),
    }

    async with llm_slots:
        insights, generated_by = await asyncio.to_thread(get_insights, metrics)
    return {"insights": insights, "generated_by": generated_by}
