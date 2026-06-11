from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.types import EpisodeOutlineStatus, OutlineVersionSource
from app.modules.series.schemas import SeriesResponse
from app.schemas.pagination import OffsetPageResponse

RequiredText = Annotated[str, Field(min_length=1)]


class OutlineUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=220)
    outline_markdown: RequiredText


class OutlineRegenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    instruction: str | None = Field(default=None, max_length=600)


class OutlineVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    outline_id: UUID
    series_id: UUID
    episode_id: UUID
    version_number: int
    title: str
    outline_markdown: str
    source: OutlineVersionSource
    created_at: datetime


class OutlineVersionListResponse(OffsetPageResponse):
    items: list[OutlineVersionResponse]


class EpisodeOutlineSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    series_id: UUID
    episode_id: UUID
    title: str
    outline_markdown: str
    status: EpisodeOutlineStatus
    current_version_id: UUID | None = None
    approved_version_id: UUID | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class EpisodeOutlineResponse(EpisodeOutlineSummaryResponse):
    episode_number: int
    episode_title: str
    episode_premise: str
    version_count: int
    latest_version_number: int | None
    can_edit: bool
    read_only_reason: str | None
    is_ready_for_brief: bool
    versions: list[OutlineVersionResponse]


class OutlineWorkspaceReadinessResponse(BaseModel):
    total_outline_count: int
    approved_outline_count: int
    is_ready_for_briefs: bool
    warnings: list[str]


class OutlineWorkspaceResponse(BaseModel):
    series: SeriesResponse
    outlines: list[EpisodeOutlineResponse]
    readiness: OutlineWorkspaceReadinessResponse
