from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.types import (
    BufferAccountStatus,
    BufferPostStatus,
    CaptionVideoKind,
    Platform,
    ScheduleStatus,
)
from app.modules.schedules.schemas import (
    BufferAccountResponse,
    BufferChannelResponse,
    BufferWebhookResponse,
    PublishingAuditLogResponse,
)
from app.schemas.pagination import CursorPageResponse, OffsetPageResponse


class PublishingAnalyticsResponse(BaseModel):
    scheduled_count: int
    published_count: int
    failed_count: int
    cancelled_count: int
    retryable_count: int
    active_channel_count: int
    unhealthy_channel_count: int
    audit_event_count: int
    webhook_event_count: int
    buffer_account_status: BufferAccountStatus | None = None
    warnings: list[str]


class PublishingQueueItemResponse(BaseModel):
    id: UUID
    series_id: UUID
    series_name: str
    episode_id: UUID
    episode_number: int
    episode_title: str
    caption_id: UUID
    video_kind: CaptionVideoKind
    video_key: str
    platform: Platform
    status: ScheduleStatus
    buffer_status: BufferPostStatus
    buffer_post_id: str | None = None
    scheduled_for: datetime
    scheduled_caption_text: str
    failure_reason: str | None = None
    live_url: str | None = None
    retry_count: int
    next_retry_at: datetime | None = None
    last_synced_at: datetime | None = None
    rate_limit_reset_at: datetime | None = None
    channel: BufferChannelResponse | None = None
    latest_audit: PublishingAuditLogResponse | None = None
    created_at: datetime
    updated_at: datetime


class PublishingQueueResponse(OffsetPageResponse):
    items: list[PublishingQueueItemResponse]
    total_count: int
    filters: dict[str, object]


class ChannelHealthCardResponse(BaseModel):
    channel: BufferChannelResponse
    mapped_platforms: list[Platform]
    scheduled_count: int
    published_count: int
    failed_count: int
    health_status: str
    warnings: list[str]


class PublishingTimelineEventResponse(BaseModel):
    id: str
    event_type: str
    title: str
    status: str
    description: str
    occurred_at: datetime
    schedule_id: UUID | None = None
    series_id: UUID | None = None
    platform: Platform | None = None


class PublishingActivityFeedItemResponse(PublishingTimelineEventResponse):
    source: str


class PublishingTimelineResponse(CursorPageResponse):
    items: list[PublishingTimelineEventResponse]


class PublishingActivityFeedResponse(CursorPageResponse):
    items: list[PublishingActivityFeedItemResponse]


class PublishingAuditLogListResponse(CursorPageResponse):
    items: list[PublishingAuditLogResponse]


class PublishingOperationsWorkspaceResponse(BaseModel):
    analytics: PublishingAnalyticsResponse
    queue: PublishingQueueResponse
    failed: PublishingQueueResponse
    retry_center: PublishingQueueResponse
    channel_health: list[ChannelHealthCardResponse]
    timeline: list[PublishingTimelineEventResponse]
    activity_feed: list[PublishingActivityFeedItemResponse]
    audit_logs: list[PublishingAuditLogResponse]
    webhooks: list[BufferWebhookResponse]
    buffer_account: BufferAccountResponse | None = None


class PublishingBulkActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule_ids: list[UUID] = Field(default_factory=list, min_length=1, max_length=100)


class PublishingBulkActionItemResult(BaseModel):
    schedule_id: UUID
    success: bool
    message: str
    status: ScheduleStatus | None = None


class PublishingBulkActionResponse(BaseModel):
    action: str
    requested_count: int
    succeeded_count: int
    failed_count: int
    results: list[PublishingBulkActionItemResult]
    workspace: PublishingOperationsWorkspaceResponse
