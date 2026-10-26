"""Demo router: seed the clinic demo data into the caller's account (same logic as the CLI)."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.recovery import DemoSeedResponse
from app.services.demo_seed import seed_demo_data
from app.services.rate_limit import rate_limit, user_key

router = APIRouter(
    prefix="/demo",
    tags=["Demo"],
    dependencies=[Depends(rate_limit("demo", 5, 3600, user_key))],
)


@router.post("/seed", response_model=DemoSeedResponse)
async def seed_demo(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await seed_demo_data(db, user.id, datetime.now(UTC))
