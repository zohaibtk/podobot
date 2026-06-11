"""media asset library

Revision ID: 0020_media_asset_library
Revises: 0019_buffer_integration
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_media_asset_library"
down_revision: str | None = "0019_buffer_integration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "asset_tags",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=24), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_asset_tags_slug"),
    )
    op.create_index("ix_asset_tags_slug", "asset_tags", ["slug"])

    op.create_table(
        "media_asset_tags",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("media_asset_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.String(length=160), server_default="system", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["asset_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("media_asset_id", "tag_id", name="uq_media_asset_tags_asset_tag"),
    )
    op.create_index("ix_media_asset_tags_media_asset_id", "media_asset_tags", ["media_asset_id"])
    op.create_index("ix_media_asset_tags_tag_id", "media_asset_tags", ["tag_id"])

    op.create_table(
        "asset_usages",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("media_asset_id", sa.UUID(), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=True),
        sa.Column("episode_id", sa.UUID(), nullable=True),
        sa.Column("usage_type", sa.String(length=80), nullable=False),
        sa.Column("usage_label", sa.String(length=220), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=160), server_default="system", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asset_usages_episode_id", "asset_usages", ["episode_id"])
    op.create_index("ix_asset_usages_media_asset_id", "asset_usages", ["media_asset_id"])
    op.create_index("ix_asset_usages_series_id", "asset_usages", ["series_id"])
    op.create_index("ix_asset_usages_usage_type", "asset_usages", ["usage_type"])


def downgrade() -> None:
    op.drop_index("ix_asset_usages_usage_type", table_name="asset_usages")
    op.drop_index("ix_asset_usages_series_id", table_name="asset_usages")
    op.drop_index("ix_asset_usages_media_asset_id", table_name="asset_usages")
    op.drop_index("ix_asset_usages_episode_id", table_name="asset_usages")
    op.drop_table("asset_usages")
    op.drop_index("ix_media_asset_tags_tag_id", table_name="media_asset_tags")
    op.drop_index("ix_media_asset_tags_media_asset_id", table_name="media_asset_tags")
    op.drop_table("media_asset_tags")
    op.drop_index("ix_asset_tags_slug", table_name="asset_tags")
    op.drop_table("asset_tags")
