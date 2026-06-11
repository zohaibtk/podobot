from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.types import CaptionVideoKind, Platform
from app.modules.schedules.schemas import PublishingAuditLogResponse
from app.schemas.pagination import OffsetPageResponse


class PublishingAnalyticsFiltersResponse(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    platforms: list[Platform] = Field(default_factory=list)
    video_kinds: list[CaptionVideoKind] = Field(default_factory=list)


class PublishingSuccessMetricsResponse(BaseModel):
    total_rows: int
    scheduled_count: int
    published_count: int
    failed_count: int
    cancelled_count: int
    retry_count: int
    success_rate: float
    failure_rate: float
    average_retry_count: float
    audit_event_count: int
    webhook_event_count: int


class ChannelPerformanceResponse(BaseModel):
    channel_id: UUID | None = None
    channel_name: str
    platform: Platform
    scheduled_count: int
    published_count: int
    failed_count: int
    cancelled_count: int
    success_rate: float
    failure_rate: float
    retry_count: int
    is_enabled: bool
    is_queue_paused: bool
    health_status: str


class ContentPerformanceResponse(BaseModel):
    series_id: UUID
    series_name: str
    episode_id: UUID
    episode_title: str
    episode_number: int
    video_kind: CaptionVideoKind
    platforms: list[Platform]
    scheduled_count: int
    published_count: int
    failed_count: int
    success_rate: float
    average_caption_characters: int
    average_caption_generations: float
    trend_score: float


class FailureMetricsResponse(BaseModel):
    reason: str
    count: int
    platforms: list[Platform]
    latest_at: datetime | None = None


class BestPublishingTimeResponse(BaseModel):
    day_of_week: str
    hour: int
    scheduled_count: int
    published_count: int
    failed_count: int
    success_rate: float


class CaptionEffectivenessResponse(BaseModel):
    bucket: str
    label: str
    scheduled_count: int
    published_count: int
    failed_count: int
    success_rate: float
    average_generation_count: float


class ContentTrendResponse(BaseModel):
    period: str
    scheduled_count: int
    published_count: int
    failed_count: int
    success_rate: float


class ExecutiveInsightResponse(BaseModel):
    severity: str
    title: str
    summary: str


class PublishingAnalyticsWorkspaceResponse(BaseModel):
    generated_at: datetime
    filters: PublishingAnalyticsFiltersResponse
    success_metrics: PublishingSuccessMetricsResponse
    channel_performance: list[ChannelPerformanceResponse]
    content_performance: list[ContentPerformanceResponse]
    failure_metrics: list[FailureMetricsResponse]
    best_times: list[BestPublishingTimeResponse]
    caption_effectiveness: list[CaptionEffectivenessResponse]
    trends: list[ContentTrendResponse]
    executive_insights: list[ExecutiveInsightResponse]
    audit_events: list[PublishingAuditLogResponse]


class ChannelPerformanceListResponse(OffsetPageResponse):
    items: list[ChannelPerformanceResponse]


class ContentPerformanceListResponse(OffsetPageResponse):
    items: list[ContentPerformanceResponse]


class PublishingAnalyticsAuditLogListResponse(OffsetPageResponse):
    items: list[PublishingAuditLogResponse]
