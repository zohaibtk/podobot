"""recordings uploads

Revision ID: 0008_recordings_uploads
Revises: 0007_episode_briefs
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_recordings_uploads"
down_revision: str | None = "0007_episode_briefs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


video_status = postgresql.ENUM(
    "missing",
    "uploaded",
    "complete",
    "locked",
    "failed",
    name="video_status",
    create_type=False,
)
transcript_status = postgresql.ENUM(
    "uploaded",
    "processed",
    "failed",
    name="transcript_status",
    create_type=False,
)
thumbnail_status = postgresql.ENUM(
    "uploaded",
    "selected",
    name="thumbnail_status",
    create_type=False,
)
clip_suggestion_status = postgresql.ENUM(
    "suggested",
    "approved",
    "rejected",
    name="clip_suggestion_status",
    create_type=False,
)


def upgrade() -> None:
    video_status.create(op.get_bind(), checkfirst=True)
    transcript_status.create(op.get_bind(), checkfirst=True)
    thumbnail_status.create(op.get_bind(), checkfirst=True)
    clip_suggestion_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "series",
        sa.Column("captions_unlocked_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "episode_videos",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("status", video_status, server_default="missing", nullable=False),
        sa.Column("file_path", sa.String(length=640), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=140), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("episode_id"),
    )
    op.create_index("ix_episode_videos_series_id", "episode_videos", ["series_id"])

    op.create_table(
        "transcripts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("status", transcript_status, server_default="processed", nullable=False),
        sa.Column("file_path", sa.String(length=640), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=140), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("episode_id"),
    )
    op.create_index("ix_transcripts_series_id", "transcripts", ["series_id"])

    op.create_table(
        "thumbnails",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("status", thumbnail_status, server_default="uploaded", nullable=False),
        sa.Column("is_selected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("file_path", sa.String(length=640), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=140), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_thumbnails_episode_id", "thumbnails", ["episode_id"])
    op.create_index("ix_thumbnails_series_id", "thumbnails", ["series_id"])

    op.create_table(
        "clip_suggestions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("slot_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("start_timecode", sa.String(length=16), nullable=False),
        sa.Column("end_timecode", sa.String(length=16), nullable=False),
        sa.Column("status", clip_suggestion_status, server_default="suggested", nullable=False),
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
        sa.CheckConstraint("slot_number > 0", name="ck_clip_suggestions_slot_positive"),
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("episode_id", "slot_number", name="uq_clip_suggestions_episode_slot"),
    )
    op.create_index("ix_clip_suggestions_episode_id", "clip_suggestions", ["episode_id"])
    op.create_index("ix_clip_suggestions_series_id", "clip_suggestions", ["series_id"])


def downgrade() -> None:
    op.drop_index("ix_clip_suggestions_series_id", table_name="clip_suggestions")
    op.drop_index("ix_clip_suggestions_episode_id", table_name="clip_suggestions")
    op.drop_table("clip_suggestions")
    op.drop_index("ix_thumbnails_series_id", table_name="thumbnails")
    op.drop_index("ix_thumbnails_episode_id", table_name="thumbnails")
    op.drop_table("thumbnails")
    op.drop_index("ix_transcripts_series_id", table_name="transcripts")
    op.drop_table("transcripts")
    op.drop_index("ix_episode_videos_series_id", table_name="episode_videos")
    op.drop_table("episode_videos")
    op.drop_column("series", "captions_unlocked_at")

    clip_suggestion_status.drop(op.get_bind(), checkfirst=True)
    thumbnail_status.drop(op.get_bind(), checkfirst=True)
    transcript_status.drop(op.get_bind(), checkfirst=True)
    video_status.drop(op.get_bind(), checkfirst=True)
