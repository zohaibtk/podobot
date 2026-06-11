from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import (
    BufferAccountStatus,
    BufferPostStatus,
    BufferWebhookStatus,
    CaptionVideoKind,
    Platform,
    PublishingAuditStatus,
    ScheduleStatus,
)
from app.modules.series.models import enum_values


class BufferAccount(Base):
    __tablename__ = "buffer_accounts"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    integration_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    buffer_account_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    organization_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[BufferAccountStatus] = mapped_column(
        Enum(BufferAccountStatus, name="buffer_account_status", values_callable=enum_values),
        nullable=False,
        default=BufferAccountStatus.DISCONNECTED,
        server_default=BufferAccountStatus.DISCONNECTED.value,
        index=True,
    )
    access_token_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scopes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    oauth_state: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    pkce_verifier: Mapped[str | None] = mapped_column(Text, nullable=True)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rate_limit: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class BufferChannel(Base):
    __tablename__ = "buffer_channels"
    __table_args__ = (
        UniqueConstraint("buffer_account_id", "buffer_channel_id", name="uq_buffer_channel"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    buffer_account_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("buffer_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    buffer_channel_id: Mapped[str] = mapped_column(String(180), nullable=False)
    service: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    display_name: Mapped[str] = mapped_column(String(180), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(640), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_queue_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class BufferChannelMapping(Base):
    __tablename__ = "buffer_channel_mappings"
    __table_args__ = (UniqueConstraint("platform", name="uq_buffer_channel_mappings_platform"),)

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform, name="platform", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    buffer_channel_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("buffer_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EpisodeVideoPlatformSchedule(Base):
    __tablename__ = "episode_video_platform_schedules"
    __table_args__ = (
        UniqueConstraint("caption_id", name="uq_schedule_caption"),
        CheckConstraint("retry_count >= 0", name="ck_schedule_retry_count_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    series_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("series.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    episode_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("episodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    episode_video_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("episode_videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    media_asset_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    caption_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("episode_video_platform_captions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clip_suggestion_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("clip_suggestions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    video_kind: Mapped[CaptionVideoKind] = mapped_column(
        Enum(CaptionVideoKind, name="caption_video_kind", values_callable=enum_values),
        nullable=False,
    )
    video_key: Mapped[str] = mapped_column(String(120), nullable=False)
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform, name="platform", values_callable=enum_values),
        nullable=False,
    )
    status: Mapped[ScheduleStatus] = mapped_column(
        Enum(ScheduleStatus, name="schedule_status", values_callable=enum_values),
        nullable=False,
        default=ScheduleStatus.SCHEDULED,
        server_default=ScheduleStatus.SCHEDULED.value,
    )
    buffer_status: Mapped[BufferPostStatus] = mapped_column(
        Enum(BufferPostStatus, name="buffer_post_status", values_callable=enum_values),
        nullable=False,
        default=BufferPostStatus.QUEUED,
        server_default=BufferPostStatus.QUEUED.value,
    )
    buffer_account_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("buffer_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    buffer_channel_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("buffer_channels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    buffer_post_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(220), nullable=True, index=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_caption_text: Mapped[str] = mapped_column(Text, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    live_url: Mapped[str | None] = mapped_column(String(640), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    buffer_last_event_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    rate_limit_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class BufferWebhook(Base):
    __tablename__ = "buffer_webhooks"
    __table_args__ = (UniqueConstraint("event_id", name="uq_buffer_webhooks_event_id"),)

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    event_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    buffer_post_id: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    schedule_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("episode_video_platform_schedules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[BufferWebhookStatus] = mapped_column(
        Enum(BufferWebhookStatus, name="buffer_webhook_status", values_callable=enum_values),
        nullable=False,
        default=BufferWebhookStatus.RECEIVED,
        server_default=BufferWebhookStatus.RECEIVED.value,
        index=True,
    )
    signature_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class PublishingAuditLog(Base):
    __tablename__ = "publishing_audit_logs"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    schedule_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("episode_video_platform_schedules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    buffer_account_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("buffer_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    buffer_channel_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("buffer_channels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    status: Mapped[PublishingAuditStatus] = mapped_column(
        Enum(PublishingAuditStatus, name="publishing_audit_status", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(220), nullable=True)
    request_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    response_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
