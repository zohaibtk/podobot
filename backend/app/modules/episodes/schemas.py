from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.types import EpisodeStatus
from app.modules.outlines.schemas import EpisodeOutlineSummaryResponse
from app.modules.series.schemas import SeriesResponse

RequiredText = Annotated[str, Field(min_length=1)]


class EpisodeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: RequiredText = Field(max_length=220)
    premise: RequiredText


class EpisodeUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=220)
    premise: str | None = Field(default=None, min_length=1)


class EpisodeDraftGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    instruction: RequiredText = Field(max_length=1200)
    episode_id: UUID | None = None
    current_title: str | None = Field(default=None, max_length=220)
    current_premise: str | None = Field(default=None, max_length=2000)


class EpisodeDraftGenerationResponse(BaseModel):
    title: str
    premise: str


class EpisodeAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    host_profile_id: UUID | None = None
    guest_profile_id: UUID | None = None
    guest_name_override: str | None = Field(default=None, max_length=180)


class EpisodeReorderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_ids: list[UUID] = Field(min_length=1)


class EpisodeResponse(BaseModel):
    id: UUID
    series_id: UUID
    episode_number: int
    title: str
    premise: str
    status: EpisodeStatus
    host_profile_id: UUID | None
    guest_profile_id: UUID | None
    guest_name_override: str | None
    host_profile_name: str | None
    guest_profile_name: str | None
    effective_host_name: str | None
    effective_guest_name: str | None
    can_edit: bool
    missing_assignments: list[str]
    created_at: datetime
    updated_at: datetime


class PlanLockReadinessResponse(BaseModel):
    is_ready: bool
    missing_episode_count: int
    missing_episode_ids: list[UUID]
    warnings: list[str]


class EpisodePlanWorkspaceResponse(BaseModel):
    series: SeriesResponse
    episodes: list[EpisodeResponse]
    outlines: list[EpisodeOutlineSummaryResponse]
    selected_narrative_id: UUID
    is_locked: bool
    lock_readiness: PlanLockReadinessResponse
