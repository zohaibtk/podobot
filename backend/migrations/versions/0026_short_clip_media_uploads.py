"""short clip media uploads

Revision ID: 0026_short_clip_media_uploads
Revises: 0025_research_scoring
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_short_clip_media_uploads"
down_revision: str | None = "0025_research_scoring"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("clip_suggestions", sa.Column("clip_file_path", sa.String(640), nullable=True))
    op.add_column("clip_suggestions", sa.Column("clip_file_name", sa.String(255), nullable=True))
    op.add_column(
        "clip_suggestions",
        sa.Column("clip_content_type", sa.String(140), nullable=True),
    )
    op.add_column(
        "clip_suggestions",
        sa.Column("clip_file_size_bytes", sa.BigInteger(), nullable=True),
    )
    op.add_column("clip_suggestions", sa.Column("clip_media_asset_id", sa.UUID(), nullable=True))
    op.add_column(
        "clip_suggestions",
        sa.Column("clip_uploaded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_clip_suggestions_clip_media_asset_id",
        "clip_suggestions",
        "media_assets",
        ["clip_media_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_clip_suggestions_clip_media_asset_id",
        "clip_suggestions",
        ["clip_media_asset_id"],
    )

    op.add_column(
        "episode_video_platform_schedules",
        sa.Column("media_asset_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_episode_video_platform_schedules_media_asset_id",
        "episode_video_platform_schedules",
        "media_assets",
        ["media_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_episode_video_platform_schedules_media_asset_id",
        "episode_video_platform_schedules",
        ["media_asset_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_episode_video_platform_schedules_media_asset_id",
        table_name="episode_video_platform_schedules",
    )
    op.drop_constraint(
        "fk_episode_video_platform_schedules_media_asset_id",
        "episode_video_platform_schedules",
        type_="foreignkey",
    )
    op.drop_column("episode_video_platform_schedules", "media_asset_id")

    op.drop_index("ix_clip_suggestions_clip_media_asset_id", table_name="clip_suggestions")
    op.drop_constraint(
        "fk_clip_suggestions_clip_media_asset_id",
        "clip_suggestions",
        type_="foreignkey",
    )
    op.drop_column("clip_suggestions", "clip_uploaded_at")
    op.drop_column("clip_suggestions", "clip_media_asset_id")
    op.drop_column("clip_suggestions", "clip_file_size_bytes")
    op.drop_column("clip_suggestions", "clip_content_type")
    op.drop_column("clip_suggestions", "clip_file_name")
    op.drop_column("clip_suggestions", "clip_file_path")
