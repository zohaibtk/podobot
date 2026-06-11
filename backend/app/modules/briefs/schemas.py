from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.types import (
    BriefKind,
    BriefStatus,
    BriefVersionSource,
    EpisodeOutlineStatus,
    EpisodeStatus,
)
from app.modules.series.schemas import SeriesResponse

RequiredText = Annotated[str, Field(min_length=1)]


class BriefUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=240)
    brief_markdown: RequiredText


class BriefVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    brief_id: UUID
    series_id: UUID
    episode_id: UUID
    outline_id: UUID
    outline_version_id: UUID
    version_number: int
    title: str
    brief_markdown: str
    source: BriefVersionSource
    created_at: datetime


class EpisodeBriefResponse(BaseModel):
    id: UUID
    series_id: UUID
    episode_id: UUID
    kind: BriefKind
    title: str
    brief_markdown: str
    status: BriefStatus
    current_version_id: UUID | None = None
    approved_version_id: UUID | None = None
    approved_at: datetime | None = None
    approval_invalidated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    profile_id: UUID | None
    profile_name: str | None
    profile_role_title: str | None
    version_count: int
    latest_version_number: int | None
    can_edit: bool
    read_only_reason: str | None
    versions: list[BriefVersionResponse]


class BriefEpisodeRequirementResponse(BaseModel):
    episode_id: UUID
    episode_number: int
    episode_title: str
    host_profile_id: UUID | None
    host_profile_name: str | None
    guest_profile_id: UUID | None
    guest_profile_name: str | None
    outline_id: UUID | None
    outline_status: EpisodeOutlineStatus | None
    outline_current_version_id: UUID | None
    missing_requirements: list[str]
    can_generate: bool


class BriefEpisodeWorkspaceResponse(BaseModel):
    episode_id: UUID
    episode_number: int
    episode_title: str
    episode_premise: str
    episode_status: EpisodeStatus
    requirement: BriefEpisodeRequirementResponse
    host_brief: EpisodeBriefResponse | None
    guest_brief: EpisodeBriefResponse | None
    pair_generated: bool
    pair_approved: bool
    pair_approved_at: datetime | None = None
    approval_invalidated_at: datetime | None = None


class BriefWorkspaceReadinessResponse(BaseModel):
    total_episode_count: int
    generated_episode_count: int
    approved_episode_count: int
    recordings_unlocked: bool
    warnings: list[str]


class BriefWorkspaceResponse(BaseModel):
    series: SeriesResponse
    episodes: list[BriefEpisodeWorkspaceResponse]
    readiness: BriefWorkspaceReadinessResponse
