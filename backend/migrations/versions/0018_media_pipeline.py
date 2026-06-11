"""media pipeline hardening

Revision ID: 0018_media_pipeline
Revises: 0017_prompt_template_idx
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_media_pipeline"
down_revision: str | None = "0017_prompt_template_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


media_asset_kind = postgresql.ENUM(
    "video",
    "transcript",
    "thumbnail",
    name="media_asset_kind",
    create_type=False,
)
media_asset_status = postgresql.ENUM(
    "uploaded",
    "processing",
    "ready",
    "failed",
    "archived",
    "deleted",
    name="media_asset_status",
    create_type=False,
)
media_processing_job_status = postgresql.ENUM(
    "queued",
    "running",
    "succeeded",
    "failed",
    name="media_processing_job_status",
    create_type=False,
)
media_processing_job_type = postgresql.ENUM(
    "metadata_extraction",
    "transcript_parsing",
    "thumbnail_generation",
    name="media_processing_job_type",
    create_type=False,
)


def upgrade() -> None:
    media_asset_kind.create(op.get_bind(), checkfirst=True)
    media_asset_status.create(op.get_bind(), checkfirst=True)
    media_processing_job_status.create(op.get_bind(), checkfirst=True)
    media_processing_job_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "media_assets",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("kind", media_asset_kind, nullable=False),
        sa.Column("status", media_asset_status, server_default="uploaded", nullable=False),
        sa.Column("storage_provider", sa.String(length=40), server_default="local", nullable=False),
        sa.Column("storage_key", sa.String(length=760), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=140), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("storage_key", name="uq_media_assets_storage_key"),
    )
    op.create_index("ix_media_assets_episode_id", "media_assets", ["episode_id"])
    op.create_index("ix_media_assets_kind", "media_assets", ["kind"])
    op.create_index("ix_media_assets_series_id", "media_assets", ["series_id"])
    op.create_index("ix_media_assets_status", "media_assets", ["status"])

    op.create_table(
        "media_metadata",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("media_asset_id", sa.UUID(), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("frame_rate", sa.String(length=40), nullable=True),
        sa.Column("codec", sa.String(length=120), nullable=True),
        sa.Column("transcript_cue_count", sa.Integer(), nullable=True),
        sa.Column("transcript_language", sa.String(length=40), nullable=True),
        sa.Column("generated_thumbnail_asset_id", sa.UUID(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["generated_thumbnail_asset_id"],
            ["media_assets.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("media_asset_id", name="uq_media_metadata_media_asset_id"),
    )
    op.create_index("ix_media_metadata_episode_id", "media_metadata", ["episode_id"])
    op.create_index("ix_media_metadata_series_id", "media_metadata", ["series_id"])

    op.create_table(
        "media_processing_jobs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("media_asset_id", sa.UUID(), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("job_type", media_processing_job_type, nullable=False),
        sa.Column("status", media_processing_job_status, server_default="queued", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_media_processing_jobs_episode_id",
        "media_processing_jobs",
        ["episode_id"],
    )
    op.create_index(
        "ix_media_processing_jobs_job_type",
        "media_processing_jobs",
        ["job_type"],
    )
    op.create_index(
        "ix_media_processing_jobs_media_asset_id",
        "media_processing_jobs",
        ["media_asset_id"],
    )
    op.create_index(
        "ix_media_processing_jobs_series_id",
        "media_processing_jobs",
        ["series_id"],
    )
    op.create_index(
        "ix_media_processing_jobs_status",
        "media_processing_jobs",
        ["status"],
    )

    op.create_table(
        "media_audit_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("media_asset_id", sa.UUID(), nullable=True),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("actor", sa.String(length=160), server_default="system", nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_audit_logs_action", "media_audit_logs", ["action"])
    op.create_index("ix_media_audit_logs_episode_id", "media_audit_logs", ["episode_id"])
    op.create_index(
        "ix_media_audit_logs_media_asset_id",
        "media_audit_logs",
        ["media_asset_id"],
    )
    op.create_index("ix_media_audit_logs_series_id", "media_audit_logs", ["series_id"])

    op.add_column("episode_videos", sa.Column("media_asset_id", sa.UUID(), nullable=True))
    op.add_column("transcripts", sa.Column("media_asset_id", sa.UUID(), nullable=True))
    op.add_column("thumbnails", sa.Column("media_asset_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_episode_videos_media_asset_id_media_assets",
        "episode_videos",
        "media_assets",
        ["media_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_transcripts_media_asset_id_media_assets",
        "transcripts",
        "media_assets",
        ["media_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_thumbnails_media_asset_id_media_assets",
        "thumbnails",
        "media_assets",
        ["media_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_episode_videos_media_asset_id", "episode_videos", ["media_asset_id"])
    op.create_index("ix_transcripts_media_asset_id", "transcripts", ["media_asset_id"])
    op.create_index("ix_thumbnails_media_asset_id", "thumbnails", ["media_asset_id"])


def downgrade() -> None:
    op.drop_index("ix_thumbnails_media_asset_id", table_name="thumbnails")
    op.drop_index("ix_transcripts_media_asset_id", table_name="transcripts")
    op.drop_index("ix_episode_videos_media_asset_id", table_name="episode_videos")
    op.drop_constraint(
        "fk_thumbnails_media_asset_id_media_assets",
        "thumbnails",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_transcripts_media_asset_id_media_assets",
        "transcripts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_episode_videos_media_asset_id_media_assets",
        "episode_videos",
        type_="foreignkey",
    )
    op.drop_column("thumbnails", "media_asset_id")
    op.drop_column("transcripts", "media_asset_id")
    op.drop_column("episode_videos", "media_asset_id")

    op.drop_index("ix_media_audit_logs_series_id", table_name="media_audit_logs")
    op.drop_index("ix_media_audit_logs_media_asset_id", table_name="media_audit_logs")
    op.drop_index("ix_media_audit_logs_episode_id", table_name="media_audit_logs")
    op.drop_index("ix_media_audit_logs_action", table_name="media_audit_logs")
    op.drop_table("media_audit_logs")

    op.drop_index("ix_media_processing_jobs_status", table_name="media_processing_jobs")
    op.drop_index("ix_media_processing_jobs_series_id", table_name="media_processing_jobs")
    op.drop_index(
        "ix_media_processing_jobs_media_asset_id",
        table_name="media_processing_jobs",
    )
    op.drop_index("ix_media_processing_jobs_job_type", table_name="media_processing_jobs")
    op.drop_index("ix_media_processing_jobs_episode_id", table_name="media_processing_jobs")
    op.drop_table("media_processing_jobs")

    op.drop_index("ix_media_metadata_series_id", table_name="media_metadata")
    op.drop_index("ix_media_metadata_episode_id", table_name="media_metadata")
    op.drop_table("media_metadata")

    op.drop_index("ix_media_assets_status", table_name="media_assets")
    op.drop_index("ix_media_assets_series_id", table_name="media_assets")
    op.drop_index("ix_media_assets_kind", table_name="media_assets")
    op.drop_index("ix_media_assets_episode_id", table_name="media_assets")
    op.drop_table("media_assets")

    media_processing_job_type.drop(op.get_bind(), checkfirst=True)
    media_processing_job_status.drop(op.get_bind(), checkfirst=True)
    media_asset_status.drop(op.get_bind(), checkfirst=True)
    media_asset_kind.drop(op.get_bind(), checkfirst=True)
