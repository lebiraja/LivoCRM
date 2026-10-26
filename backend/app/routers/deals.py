"""Deals CRUD router with stage update for Kanban."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.user import User
from app.schemas import PaginatedResponse
from app.schemas.deal import DealCreate, DealStage, DealUpdate, DealRead
from app.services.ownership import require_owned

router = APIRouter(prefix="/deals", tags=["Deals"])


class StageUpdate(BaseModel):
    stage: DealStage


@router.get("/", response_model=PaginatedResponse[DealRead])
async def list_deals(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    stage: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Build base query
    base_stmt = select(Deal).where(Deal.user_id == user.id)
    if stage:
        base_stmt = base_stmt.where(Deal.stage == stage)
    if status_filter:
        base_stmt = base_stmt.where(Deal.status == status_filter)

    # Get total count
    count_stmt = select(func.count()).select_from(Deal).where(Deal.user_id == user.id)
    if stage:
        count_stmt = count_stmt.where(Deal.stage == stage)
    if status_filter:
        count_stmt = count_stmt.where(Deal.status == status_filter)
    total = (await db.execute(count_stmt)).scalar() or 0

    # Get paginated results
    stmt = base_stmt.order_by(Deal.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return PaginatedResponse(total=total, items=items)


@router.get("/{deal_id}", response_model=DealRead)
async def get_deal(
    deal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Deal).where(Deal.id == deal_id, Deal.user_id == user.id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.post("/", response_model=DealRead, status_code=status.HTTP_201_CREATED)
async def create_deal(
    body: DealCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.contact_id:
        await require_owned(db, Contact, body.contact_id, user)
    deal = Deal(**body.model_dump(), user_id=user.id)
    db.add(deal)
    await db.commit()
    await db.refresh(deal)
    return deal


@router.patch("/{deal_id}", response_model=DealRead)
async def update_deal(
    deal_id: UUID,
    body: DealUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Deal).where(Deal.id == deal_id, Deal.user_id == user.id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if body.contact_id:
        await require_owned(db, Contact, body.contact_id, user)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(deal, field, value)
    await db.commit()
    await db.refresh(deal)
    return deal


@router.patch("/{deal_id}/stage", response_model=DealRead)
async def update_deal_stage(
    deal_id: UUID,
    body: StageUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Quick stage update for Kanban drag-and-drop."""
    result = await db.execute(select(Deal).where(Deal.id == deal_id, Deal.user_id == user.id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    deal.stage = body.stage
    # auto-update status based on terminal stages
    if body.stage == "closed_won":
        deal.status = "won"
    elif body.stage == "closed_lost":
        deal.status = "lost"
    await db.commit()
    await db.refresh(deal)
    return deal


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deal(
    deal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Deal).where(Deal.id == deal_id, Deal.user_id == user.id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    await db.delete(deal)
    await db.commit()
