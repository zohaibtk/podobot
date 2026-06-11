"""platform captions

Revision ID: 0009_platform_captions
Revises: 0008_recordings_uploads
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_platform_captions"
down_revision: str | None = "0008_recordings_uploads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


caption_status = postgresql.ENUM(
    "not_started",
    "ready",
    "failed",
    name="caption_status",
    create_type=False,
)
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


def upgrade() -> None:
    caption_status.create(op.get_bind(), checkfirst=True)
    caption_video_kind.create(op.get_bind(), checkfirst=True)
    platform.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "series",
        sa.Column("scheduling_unlocked_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "episode_video_platform_captions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("episode_video_id", sa.UUID(), nullable=False),
        sa.Column("clip_suggestion_id", sa.UUID(), nullable=True),
        sa.Column("video_kind", caption_video_kind, nullable=False),
        sa.Column("video_key", sa.String(length=120), nullable=False),
        sa.Column("platform", platform, nullable=False),
        sa.Column("status", caption_status, server_default="not_started", nullable=False),
        sa.Column("caption_text", sa.Text(), nullable=True),
        sa.Column("generation_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
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
            "video_kind <> 'full_episode' OR clip_suggestion_id IS NULL",
            name="ck_caption_full_episode_has_no_clip",
        ),
        sa.CheckConstraint(
            "video_kind <> 'short_clip' OR clip_suggestion_id IS NOT NULL",
            name="ck_caption_short_clip_has_clip",
        ),
        sa.CheckConstraint(
            "generation_count >= 0",
            name="ck_caption_generation_count_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["clip_suggestion_id"],
            ["clip_suggestions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["episode_video_id"], ["episode_videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "episode_video_id",
            "video_kind",
            "video_key",
            "platform",
            name="uq_caption_video_kind_key_platform",
        ),
    )
    op.create_index(
        "ix_episode_video_platform_captions_clip_suggestion_id",
        "episode_video_platform_captions",
        ["clip_suggestion_id"],
    )
    op.create_index(
        "ix_episode_video_platform_captions_episode_id",
        "episode_video_platform_captions",
        ["episode_id"],
    )
    op.create_index(
        "ix_episode_video_platform_captions_episode_video_id",
        "episode_video_platform_captions",
        ["episode_video_id"],
    )
    op.create_index(
        "ix_episode_video_platform_captions_series_id",
        "episode_video_platform_captions",
        ["series_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_episode_video_platform_captions_series_id",
        table_name="episode_video_platform_captions",
    )
    op.drop_index(
        "ix_episode_video_platform_captions_episode_video_id",
        table_name="episode_video_platform_captions",
    )
    op.drop_index(
        "ix_episode_video_platform_captions_episode_id",
        table_name="episode_video_platform_captions",
    )
    op.drop_index(
        "ix_episode_video_platform_captions_clip_suggestion_id",
        table_name="episode_video_platform_captions",
    )
    op.drop_table("episode_video_platform_captions")
    op.drop_column("series", "scheduling_unlocked_at")

    platform.drop(op.get_bind(), checkfirst=True)
    caption_video_kind.drop(op.get_bind(), checkfirst=True)
    caption_status.drop(op.get_bind(), checkfirst=True)
