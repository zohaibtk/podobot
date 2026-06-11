from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.types import (
    BufferAccountStatus,
    BufferPostStatus,
    BufferWebhookStatus,
    CaptionStatus,
    CaptionVideoKind,
    EpisodeStatus,
    Platform,
    PublishingAuditStatus,
    ScheduleStatus,
)
from app.modules.recordings.schemas import ClipSuggestionResponse
from app.modules.series.schemas import SeriesResponse


class ScheduleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    caption_id: UUID
    scheduled_for: datetime


class BulkScheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scheduled_for: datetime
    caption_ids: list[UUID] | None = None
    spacing_minutes: int = Field(default=0, ge=0, le=1440)


class ScheduleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    scheduled_for: datetime | None = None
    scheduled_caption_text: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def require_change(self) -> "ScheduleUpdateRequest":
        if self.scheduled_for is None and self.scheduled_caption_text is None:
            raise ValueError("scheduled_for or scheduled_caption_text is required")
        return self


class ScheduleRescheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    scheduled_for: datetime
    scheduled_caption_text: str | None = Field(default=None, min_length=1)


class BufferOAuthStartResponse(BaseModel):
    authorization_url: str
    state: str
    is_configured: bool


class BufferOAuthCallbackResponse(BaseModel):
    success: bool
    message: str


class BufferChannelMappingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel_id: UUID


class BufferWebhookEventRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    event_id: str | None = None
    type: str | None = None
    event_type: str | None = None
    post_id: str | None = None
    status: str | None = None
    message: str | None = None
    live_url: str | None = None


class BufferAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    integration_id: UUID | None = None
    buffer_account_id: str | None = None
    organization_id: str | None = None
    name: str
    status: BufferAccountStatus
    scopes: list[str]
    token_expires_at: datetime | None = None
    connected_at: datetime | None = None
    last_synced_at: datetime | None = None
    rate_limit: dict[str, object]
    created_at: datetime
    updated_at: datetime


class BufferChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    buffer_account_id: UUID
    buffer_channel_id: str
    service: str
    name: str
    display_name: str
    avatar_url: str | None = None
    is_enabled: bool
    is_queue_paused: bool
    raw_payload: dict[str, object]
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class BufferChannelMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    platform: Platform
    buffer_channel_id: UUID
    is_active: bool
    channel: BufferChannelResponse | None = None
    created_at: datetime
    updated_at: datetime


class PublishingAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    schedule_id: UUID | None = None
    buffer_account_id: UUID | None = None
    buffer_channel_id: UUID | None = None
    action: str
    status: PublishingAuditStatus
    idempotency_key: str | None = None
    request_payload: dict[str, object]
    response_payload: dict[str, object]
    error_message: str | None = None
    created_at: datetime


class BufferWebhookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: str | None = None
    event_type: str
    buffer_post_id: str | None = None
    schedule_id: UUID | None = None
    status: BufferWebhookStatus
    signature_valid: bool
    payload: dict[str, object]
    received_at: datetime
    processed_at: datetime | None = None
    created_at: datetime


class BufferWorkspaceResponse(BaseModel):
    account: BufferAccountResponse | None = None
    channels: list[BufferChannelResponse]
    mappings: list[BufferChannelMappingResponse]
    audit_logs: list[PublishingAuditLogResponse]
    webhooks: list[BufferWebhookResponse]
    required: bool = True
    warnings: list[str]


class EpisodeVideoPlatformScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    series_id: UUID
    episode_id: UUID
    episode_video_id: UUID
    media_asset_id: UUID | None = None
    caption_id: UUID
    clip_suggestion_id: UUID | None = None
    video_kind: CaptionVideoKind
    video_key: str
    platform: Platform
    status: ScheduleStatus
    buffer_status: BufferPostStatus
    buffer_account_id: UUID | None = None
    buffer_channel_id: UUID | None = None
    buffer_post_id: str | None = None
    idempotency_key: str | None = None
    scheduled_for: datetime
    scheduled_caption_text: str
    failure_reason: str | None = None
    live_url: str | None = None
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    cancelled_at: datetime | None = None
    last_synced_at: datetime | None = None
    next_retry_at: datetime | None = None
    buffer_last_event_id: str | None = None
    rate_limit_reset_at: datetime | None = None
    retry_count: int
    channel: BufferChannelResponse | None = None
    audit_logs: list[PublishingAuditLogResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ScheduleRowResponse(BaseModel):
    caption_id: UUID
    series_id: UUID
    episode_id: UUID
    episode_video_id: UUID
    clip_suggestion_id: UUID | None = None
    video_kind: CaptionVideoKind
    video_key: str
    platform: Platform
    caption_status: CaptionStatus
    caption_text: str | None = None
    schedule: EpisodeVideoPlatformScheduleResponse | None = None
    is_captioned: bool
    media_ready: bool
    schedule_ready: bool
    media_file_name: str | None = None
    can_create_schedule: bool
    can_reschedule: bool
    schedule_locked_reason: str | None = None


class ScheduleShortClipSlotResponse(BaseModel):
    clip_suggestion: ClipSuggestionResponse
    rows: list[ScheduleRowResponse]
    scheduled_count: int
    published_count: int
    failed_count: int


class ScheduleEpisodeWorkspaceResponse(BaseModel):
    episode_id: UUID
    episode_number: int
    episode_title: str
    episode_premise: str
    episode_status: EpisodeStatus
    full_episode_rows: list[ScheduleRowResponse]
    short_clip_slots: list[ScheduleShortClipSlotResponse]
    eligible_count: int
    scheduled_count: int
    published_count: int
    failed_count: int
    locked_count: int


class BulkScheduleResultResponse(BaseModel):
    requested_count: int
    scheduled_count: int
    failed_count: int
    skipped_count: int


class ScheduleWorkspaceReadinessResponse(BaseModel):
    total_row_count: int
    eligible_row_count: int
    scheduled_row_count: int
    published_row_count: int
    failed_row_count: int
    locked_row_count: int
    bulk_schedulable_count: int
    warnings: list[str]


class ScheduleWorkspaceResponse(BaseModel):
    series: SeriesResponse
    episodes: list[ScheduleEpisodeWorkspaceResponse]
    readiness: ScheduleWorkspaceReadinessResponse
    buffer: BufferWorkspaceResponse | None = None
    bulk_result: BulkScheduleResultResponse | None = None
