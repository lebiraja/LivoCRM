"""Activities CRUD router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.activity import Activity
from app.models.user import User
from app.schemas import PaginatedResponse
from app.schemas.activity import ActivityCreate, ActivityRead

router = APIRouter(prefix="/activities", tags=["Activities"])


@router.get("/", response_model=PaginatedResponse[ActivityRead])
async def list_activities(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    contact_id: UUID | None = None,
    deal_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Build base query
    base_stmt = select(Activity).where(Activity.user_id == user.id)
    if contact_id:
        base_stmt = base_stmt.where(Activity.contact_id == contact_id)
    if deal_id:
        base_stmt = base_stmt.where(Activity.deal_id == deal_id)

    # Get total count
    count_stmt = select(func.count()).select_from(Activity).where(Activity.user_id == user.id)
    if contact_id:
        count_stmt = count_stmt.where(Activity.contact_id == contact_id)
    if deal_id:
        count_stmt = count_stmt.where(Activity.deal_id == deal_id)
    total = (await db.execute(count_stmt)).scalar() or 0

    # Get paginated results
    stmt = base_stmt.order_by(Activity.occurred_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return PaginatedResponse(total=total, items=items)


@router.get("/{activity_id}", response_model=ActivityRead)
async def get_activity(
    activity_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Activity).where(Activity.id == activity_id, Activity.user_id == user.id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.post("/", response_model=ActivityRead, status_code=status.HTTP_201_CREATED)
async def create_activity(
    body: ActivityCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    activity = Activity(**body.model_dump(), user_id=user.id)
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_activity(
    activity_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Activity).where(Activity.id == activity_id, Activity.user_id == user.id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    await db.delete(activity)
    await db.commit()
