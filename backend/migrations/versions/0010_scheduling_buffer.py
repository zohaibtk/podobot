"""scheduling buffer

Revision ID: 0010_scheduling_buffer
Revises: 0009_platform_captions
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_scheduling_buffer"
down_revision: str | None = "0009_platform_captions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


caption_video_kind = postgresql.ENUM(
    "full_episode",
    "short_clip",
    name="caption_video_kind",
    create_type=False,
)
platform = postgresql.ENUM(
    "linkedin",
    "facebook",
    "youtube",
    "instagram",
    "tiktok",
    "x",
    name="platform",
    create_type=False,
)
schedule_status = postgresql.ENUM(
    "scheduled",
    "published",
    "failed",
    "cancelled",
    name="schedule_status",
    create_type=False,
)
buffer_post_status = postgresql.ENUM(
    "queued",
    "published",
    "failed",
    "cancelled",
    name="buffer_post_status",
    create_type=False,
)


def upgrade() -> None:
    schedule_status.create(op.get_bind(), checkfirst=True)
    buffer_post_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "episode_video_platform_schedules",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("episode_video_id", sa.UUID(), nullable=False),
        sa.Column("caption_id", sa.UUID(), nullable=False),
        sa.Column("clip_suggestion_id", sa.UUID(), nullable=True),
        sa.Column("video_kind", caption_video_kind, nullable=False),
        sa.Column("video_key", sa.String(length=120), nullable=False),
        sa.Column("platform", platform, nullable=False),
        sa.Column("status", schedule_status, server_default="scheduled", nullable=False),
        sa.Column("buffer_status", buffer_post_status, server_default="queued", nullable=False),
        sa.Column("buffer_post_id", sa.String(length=180), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_caption_text", sa.Text(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("live_url", sa.String(length=640), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "retry_count >= 0",
            name="ck_schedule_retry_count_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["caption_id"],
            ["episode_video_platform_captions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clip_suggestion_id"],
            ["clip_suggestions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["episode_video_id"], ["episode_videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("caption_id", name="uq_schedule_caption"),
    )
    op.create_index(
        "ix_episode_video_platform_schedules_caption_id",
        "episode_video_platform_schedules",
        ["caption_id"],
    )
    op.create_index(
        "ix_episode_video_platform_schedules_clip_suggestion_id",
        "episode_video_platform_schedules",
        ["clip_suggestion_id"],
    )
    op.create_index(
        "ix_episode_video_platform_schedules_episode_id",
        "episode_video_platform_schedules",
        ["episode_id"],
    )
    op.create_index(
        "ix_episode_video_platform_schedules_episode_video_id",
        "episode_video_platform_schedules",
        ["episode_video_id"],
    )
    op.create_index(
        "ix_episode_video_platform_schedules_series_id",
        "episode_video_platform_schedules",
        ["series_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_episode_video_platform_schedules_series_id",
        table_name="episode_video_platform_schedules",
    )
    op.drop_index(
        "ix_episode_video_platform_schedules_episode_video_id",
        table_name="episode_video_platform_schedules",
    )
    op.drop_index(
        "ix_episode_video_platform_schedules_episode_id",
        table_name="episode_video_platform_schedules",
    )
    op.drop_index(
        "ix_episode_video_platform_schedules_clip_suggestion_id",
        table_name="episode_video_platform_schedules",
    )
    op.drop_index(
        "ix_episode_video_platform_schedules_caption_id",
        table_name="episode_video_platform_schedules",
    )
    op.drop_table("episode_video_platform_schedules")

    buffer_post_status.drop(op.get_bind(), checkfirst=True)
    schedule_status.drop(op.get_bind(), checkfirst=True)
