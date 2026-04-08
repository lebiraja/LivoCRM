"""Database seeding service for default data initialization."""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.pipeline import PipelineStage


# Default pipeline stages for new users
DEFAULT_STAGES = [
    ("Lead", 0),
    ("Qualified", 1),
    ("Proposal", 2),
    ("Negotiation", 3),
    ("Closed Won", 4),
    ("Closed Lost", 5),
]


async def seed_default_pipeline_stages(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Create default pipeline stages for a new user if they don't exist."""
    # Check if user already has stages
    result = await db.execute(
        select(PipelineStage).where(PipelineStage.user_id == user_id).limit(1)
    )
    if result.scalar():
        return  # User already has stages

    # Create default stages
    for name, position in DEFAULT_STAGES:
        stage = PipelineStage(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            position=position,
        )
        db.add(stage)

    await db.commit()
