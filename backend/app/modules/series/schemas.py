from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.types import DiscoveryStatus, SeriesStage, SeriesStatus
from app.schemas.pagination import OffsetPageResponse

RequiredText = Annotated[str, Field(min_length=1)]


class SeriesCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: RequiredText = Field(max_length=180)
    audience: RequiredText = Field(max_length=240)
    description: RequiredText
    guest_name: str | None = Field(default=None, max_length=180)


class SeriesUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=180)
    audience: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, min_length=1)
    guest_name: str | None = Field(default=None, max_length=180)


class SeriesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    audience: str
    description: str
    guest_name: str | None
    status: SeriesStatus
    discovery_status: DiscoveryStatus
    current_stage: SeriesStage
    episode_plan_generated_at: datetime | None = None
    plan_locked_at: datetime | None = None
    briefs_approved_at: datetime | None = None
    captions_unlocked_at: datetime | None = None
    scheduling_unlocked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SeriesListResponse(OffsetPageResponse):
    items: list[SeriesResponse]
