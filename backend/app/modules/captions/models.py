from datetime import datetime
from uuid import UUID

from sqlalchemy import (
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
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import CaptionStatus, CaptionVideoKind, Platform
from app.modules.series.models import enum_values


class EpisodeVideoPlatformCaption(Base):
    __tablename__ = "episode_video_platform_captions"
    __table_args__ = (
        UniqueConstraint(
            "episode_video_id",
            "video_kind",
            "video_key",
            "platform",
            name="uq_caption_video_kind_key_platform",
        ),
        CheckConstraint(
            "video_kind <> 'full_episode' OR clip_suggestion_id IS NULL",
            name="ck_caption_full_episode_has_no_clip",
        ),
        CheckConstraint(
            "video_kind <> 'short_clip' OR clip_suggestion_id IS NOT NULL",
            name="ck_caption_short_clip_has_clip",
        ),
        CheckConstraint("generation_count >= 0", name="ck_caption_generation_count_nonnegative"),
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
    clip_suggestion_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("clip_suggestions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    video_kind: Mapped[CaptionVideoKind] = mapped_column(
        Enum(
            CaptionVideoKind,
            name="caption_video_kind",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    video_key: Mapped[str] = mapped_column(String(120), nullable=False)
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform, name="platform", values_callable=enum_values),
        nullable=False,
    )
    status: Mapped[CaptionStatus] = mapped_column(
        Enum(CaptionStatus, name="caption_status", values_callable=enum_values),
        nullable=False,
        default=CaptionStatus.NOT_STARTED,
        server_default=CaptionStatus.NOT_STARTED.value,
    )
    caption_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
