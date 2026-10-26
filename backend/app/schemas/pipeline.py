"""PipelineStage-related Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

StageName = Annotated[str, Field(min_length=1, max_length=100)]
Position = Annotated[int, Field(ge=0, le=1000)]


class PipelineStageCreate(BaseModel):
    name: StageName
    position: Position = 0


class PipelineStageUpdate(BaseModel):
    name: StageName | None = None
    position: Position | None = None


class PipelineStageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    position: int
    created_at: datetime
