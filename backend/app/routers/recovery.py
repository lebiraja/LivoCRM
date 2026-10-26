"""Recovery router: run the follow-up generator on demand and read the KPI summary."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.recovery import RecoveryRunResponse, RecoverySummary
from app.services.rate_limit import rate_limit, user_key
from app.services.recovery import generate_recovery_tasks, summarize_recovery

router = APIRouter(
    prefix="/recovery",
    tags=["Recovery"],
    dependencies=[Depends(rate_limit("recovery", 30, 60, user_key))],
)


@router.post("/run", response_model=RecoveryRunResponse)
async def run_recovery(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    created = await generate_recovery_tasks(db, user.id, datetime.now(UTC))
    return RecoveryRunResponse(created=created)


@router.get("/summary", response_model=RecoverySummary)
async def recovery_summary(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await summarize_recovery(db, user.id, datetime.now(UTC), days)
