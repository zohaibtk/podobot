from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.types import (
    CaptionStatus,
    CaptionVideoKind,
    EpisodeStatus,
    Platform,
    TranscriptStatus,
    VideoStatus,
)
from app.modules.recordings.schemas import (
    ClipSuggestionResponse,
    EpisodeVideoResponse,
    TranscriptResponse,
)
from app.modules.series.schemas import SeriesResponse


class CaptionPlatformCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    video_kind: CaptionVideoKind
    platform: Platform
    clip_suggestion_id: UUID | None = None


class CaptionUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    caption_text: str = Field(min_length=1)


class EpisodeVideoPlatformCaptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    series_id: UUID
    episode_id: UUID
    episode_video_id: UUID
    clip_suggestion_id: UUID | None = None
    video_kind: CaptionVideoKind
    video_key: str
    platform: Platform
    status: CaptionStatus
    caption_text: str | None = None
    generation_count: int
    generated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    can_schedule: bool
    scheduling_locked_reason: str | None = None


class CaptionShortClipSlotResponse(BaseModel):
    clip_suggestion: ClipSuggestionResponse
    captions: list[EpisodeVideoPlatformCaptionResponse]
    available_platforms: list[Platform]
    complete_caption_count: int


class CaptionEpisodeWorkspaceResponse(BaseModel):
    episode_id: UUID
    episode_number: int
    episode_title: str
    episode_premise: str
    episode_status: EpisodeStatus
    video_status: VideoStatus
    transcript_status: TranscriptStatus | None = None
    transcript_ready: bool
    caption_blockers: list[str]
    video: EpisodeVideoResponse
    transcript: TranscriptResponse | None
    full_episode_captions: list[EpisodeVideoPlatformCaptionResponse]
    full_available_platforms: list[Platform]
    short_clip_slots: list[CaptionShortClipSlotResponse]
    ready_caption_count: int
    total_caption_count: int


class CaptionWorkspaceReadinessResponse(BaseModel):
    total_caption_count: int
    ready_caption_count: int
    full_episode_ready_count: int
    short_clip_ready_count: int
    scheduling_unlocked: bool
    warnings: list[str]


class CaptionWorkspaceResponse(BaseModel):
    series: SeriesResponse
    episodes: list[CaptionEpisodeWorkspaceResponse]
    full_episode_platforms: list[Platform]
    short_clip_platforms: list[Platform]
    readiness: CaptionWorkspaceReadinessResponse
