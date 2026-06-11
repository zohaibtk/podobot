from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.types import (
    ClipSuggestionStatus,
    EpisodeStatus,
    MediaAssetKind,
    MediaAssetStatus,
    MediaProcessingJobStatus,
    MediaProcessingJobType,
    ThumbnailStatus,
    TranscriptStatus,
    VideoStatus,
)
from app.modules.series.schemas import SeriesResponse


class SignedMediaURLResponse(BaseModel):
    asset_id: UUID
    url: str
    expires_at: datetime


class MediaAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    series_id: UUID
    episode_id: UUID
    kind: MediaAssetKind
    status: MediaAssetStatus
    storage_provider: str
    storage_key: str
    file_name: str
    content_type: str
    file_size_bytes: int
    checksum_sha256: str
    last_error: str | None = None
    uploaded_at: datetime
    archived_at: datetime | None = None
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    signed_url: str | None = None
    signed_url_expires_at: datetime | None = None


class MediaMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    media_asset_id: UUID
    series_id: UUID
    episode_id: UUID
    duration_seconds: int | None = None
    width: int | None = None
    height: int | None = None
    frame_rate: str | None = None
    codec: str | None = None
    transcript_cue_count: int | None = None
    transcript_language: str | None = None
    generated_thumbnail_asset_id: UUID | None = None
    metadata: dict[str, object]
    extracted_at: datetime
    created_at: datetime
    updated_at: datetime


class MediaProcessingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    media_asset_id: UUID
    series_id: UUID
    episode_id: UUID
    job_type: MediaProcessingJobType
    status: MediaProcessingJobStatus
    attempts: int
    max_attempts: int
    input_payload: dict[str, object]
    output_payload: dict[str, object] | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class EpisodeVideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    series_id: UUID
    episode_id: UUID
    status: VideoStatus
    file_path: str | None = None
    file_name: str | None = None
    content_type: str | None = None
    file_size_bytes: int | None = None
    media_asset_id: UUID | None = None
    media_asset: MediaAssetResponse | None = None
    metadata: MediaMetadataResponse | None = None
    processing_jobs: list[MediaProcessingJobResponse] = Field(default_factory=list)
    uploaded_at: datetime | None = None
    locked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TranscriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    series_id: UUID
    episode_id: UUID
    status: TranscriptStatus
    file_path: str
    file_name: str
    content_type: str
    file_size_bytes: int
    media_asset_id: UUID | None = None
    media_asset: MediaAssetResponse | None = None
    metadata: MediaMetadataResponse | None = None
    processing_jobs: list[MediaProcessingJobResponse] = Field(default_factory=list)
    uploaded_at: datetime
    processed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ThumbnailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    series_id: UUID
    episode_id: UUID
    status: ThumbnailStatus
    is_selected: bool
    file_path: str
    file_name: str
    content_type: str
    file_size_bytes: int
    media_asset_id: UUID | None = None
    media_asset: MediaAssetResponse | None = None
    metadata: MediaMetadataResponse | None = None
    processing_jobs: list[MediaProcessingJobResponse] = Field(default_factory=list)
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime


class ClipSuggestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    series_id: UUID
    episode_id: UUID
    slot_number: int
    title: str
    rationale: str
    start_timecode: str
    end_timecode: str
    clip_file_path: str | None = None
    clip_file_name: str | None = None
    clip_content_type: str | None = None
    clip_file_size_bytes: int | None = None
    clip_media_asset_id: UUID | None = None
    clip_uploaded_at: datetime | None = None
    clip_media_uploaded: bool = False
    status: ClipSuggestionStatus
    created_at: datetime
    updated_at: datetime


class RecordingEpisodeWorkspaceResponse(BaseModel):
    episode_id: UUID
    episode_number: int
    episode_title: str
    episode_premise: str
    episode_status: EpisodeStatus
    brief_pair_approved: bool
    can_upload: bool
    upload_blockers: list[str]
    video: EpisodeVideoResponse
    transcript: TranscriptResponse | None
    thumbnails: list[ThumbnailResponse]
    selected_thumbnail: ThumbnailResponse | None
    clip_suggestions: list[ClipSuggestionResponse]
    video_file_uploaded: bool
    transcript_uploaded: bool
    suggested_short_clip_count: int
    uploaded_short_clip_count: int
    recording_complete: bool
    captions_ready: bool
    recording_locked: bool
    locked_at: datetime | None = None


class RecordingWorkspaceReadinessResponse(BaseModel):
    total_episode_count: int
    complete_episode_count: int
    transcript_ready_episode_count: int
    suggested_short_clip_count: int
    uploaded_short_clip_count: int
    captions_unlocked: bool
    warnings: list[str]


class RecordingWorkspaceResponse(BaseModel):
    series: SeriesResponse
    episodes: list[RecordingEpisodeWorkspaceResponse]
    readiness: RecordingWorkspaceReadinessResponse
