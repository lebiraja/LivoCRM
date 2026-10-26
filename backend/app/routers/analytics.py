"""Analytics router — KPI summaries, win-rate funnel, revenue forecast."""

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.activity import Activity
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary")
async def summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """High-level KPIs: total contacts, deals, activities, pipeline value."""
    # Query contacts count
    contacts_count = (await db.execute(
        select(func.count()).select_from(Contact).where(Contact.user_id == user.id)
    )).scalar() or 0

    # Query activities count
    activities_count = (await db.execute(
        select(func.count()).select_from(Activity).where(Activity.user_id == user.id)
    )).scalar() or 0

    # Combine deals queries into one: count + pipeline_value + won_value
    deals_result = await db.execute(
        select(
            func.count(Deal.id).label("deals_count"),
            func.coalesce(func.sum(case((Deal.status == "active", Deal.value), else_=0)), 0).label("pipeline_value"),
            func.coalesce(func.sum(case((Deal.status == "won", Deal.value), else_=0)), 0).label("won_value"),
        ).where(Deal.user_id == user.id)
    )
    deals_row = deals_result.one()

    return {
        "contacts": contacts_count,
        "deals": deals_row.deals_count or 0,
        "activities": activities_count,
        "pipeline_value": float(deals_row.pipeline_value),
        "won_value": float(deals_row.won_value),
    }


@router.get("/win-rate")
async def win_rate(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Deal stage funnel with counts and win/loss rate."""
    result = await db.execute(
        select(Deal.stage, func.count()).where(Deal.user_id == user.id).group_by(Deal.stage)
    )
    stages = {row[0]: row[1] for row in result.all()}

    won = stages.get("closed_won", 0)
    lost = stages.get("closed_lost", 0)
    total_closed = won + lost
    rate = round(won / total_closed * 100, 1) if total_closed > 0 else 0

    return {"stages": stages, "win_rate": rate, "won": won, "lost": lost}


@router.get("/forecast")
async def forecast(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Weighted revenue forecast based on stage probabilities."""
    stage_weights = {
        "lead": 0.1,
        "qualified": 0.25,
        "proposal": 0.5,
        "negotiation": 0.75,
        "closed_won": 1.0,
        "closed_lost": 0.0,
    }
    result = await db.execute(
        select(Deal.stage, func.sum(Deal.value)).where(
            Deal.user_id == user.id, Deal.status == "active"
        ).group_by(Deal.stage)
    )
    breakdown = {}
    weighted_total = 0.0
    for stage, total in result.all():
        weight = stage_weights.get(stage, 0.1)
        weighted = float(total) * weight
        breakdown[stage] = {"raw": float(total), "weight": weight, "weighted": round(weighted, 2)}
        weighted_total += weighted

    return {"forecast": round(weighted_total, 2), "breakdown": breakdown}
