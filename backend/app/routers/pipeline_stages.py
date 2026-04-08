"""Pipeline Stages CRUD router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.pipeline import PipelineStage
from app.models.user import User
from app.schemas import PaginatedResponse
from app.schemas.pipeline import PipelineStageCreate, PipelineStageRead, PipelineStageUpdate

router = APIRouter(prefix="/pipeline-stages", tags=["Pipeline Stages"])


@router.get("/", response_model=PaginatedResponse[PipelineStageRead])
async def list_pipeline_stages(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all pipeline stages for the current user."""
    result = await db.execute(
        select(PipelineStage)
        .where(PipelineStage.user_id == user.id)
        .order_by(PipelineStage.position)
    )
    items = result.scalars().all()
    return PaginatedResponse(total=len(items), items=items)


@router.get("/{stage_id}", response_model=PipelineStageRead)
async def get_pipeline_stage(
    stage_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a single pipeline stage."""
    result = await db.execute(
        select(PipelineStage).where(
            PipelineStage.id == stage_id,
            PipelineStage.user_id == user.id,
        )
    )
    stage = result.scalar_one_or_none()
    if not stage:
        raise HTTPException(status_code=404, detail="Pipeline stage not found")
    return stage


@router.post("/", response_model=PipelineStageRead, status_code=status.HTTP_201_CREATED)
async def create_pipeline_stage(
    body: PipelineStageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new pipeline stage."""
    stage = PipelineStage(**body.model_dump(), user_id=user.id)
    db.add(stage)
    await db.commit()
    await db.refresh(stage)
    return stage


@router.patch("/{stage_id}", response_model=PipelineStageRead)
async def update_pipeline_stage(
    stage_id: UUID,
    body: PipelineStageUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a pipeline stage (name and/or position)."""
    result = await db.execute(
        select(PipelineStage).where(
            PipelineStage.id == stage_id,
            PipelineStage.user_id == user.id,
        )
    )
    stage = result.scalar_one_or_none()
    if not stage:
        raise HTTPException(status_code=404, detail="Pipeline stage not found")

    # Update only provided fields
    if body.name is not None:
        stage.name = body.name
    if body.position is not None:
        stage.position = body.position

    await db.commit()
    await db.refresh(stage)
    return stage


@router.delete("/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline_stage(
    stage_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a pipeline stage."""
    result = await db.execute(
        select(PipelineStage).where(
            PipelineStage.id == stage_id,
            PipelineStage.user_id == user.id,
        )
    )
    stage = result.scalar_one_or_none()
    if not stage:
        raise HTTPException(status_code=404, detail="Pipeline stage not found")

    await db.delete(stage)
    await db.commit()
