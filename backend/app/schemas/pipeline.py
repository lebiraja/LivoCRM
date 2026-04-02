"""PipelineStage-related Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PipelineStageCreate(BaseModel):
    name: str
    position: int = 0


class PipelineStageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    position: int
    created_at: datetime
