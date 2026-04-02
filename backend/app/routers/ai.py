"""AI router — lead scoring and AI-generated insights."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.contact import Contact
from app.models.activity import Activity
from app.models.user import User
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
    """Placeholder for AI-generated CRM insights (Bedrock integration)."""
    return {
        "insights": [
            "You have 3 contacts without recent activity — consider a follow-up.",
            "Your win rate improved 5% over the last 30 days.",
            "Pipeline value is concentrated in the 'proposal' stage.",
        ],
        "generated_by": "placeholder",
    }
