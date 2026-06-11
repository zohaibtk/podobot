"""episode briefs

Revision ID: 0007_episode_briefs
Revises: 0006_episode_outlines
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_episode_briefs"
down_revision: str | None = "0006_episode_outlines"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


brief_kind = postgresql.ENUM("host", "guest", name="brief_kind", create_type=False)
brief_status = postgresql.ENUM(
    "generated",
    "draft",
    "approved",
    name="brief_status",
    create_type=False,
)
brief_version_source = postgresql.ENUM(
    "generation",
    "manual_edit",
    "regeneration",
    name="brief_version_source",
    create_type=False,
)


def upgrade() -> None:
    brief_kind.create(op.get_bind(), checkfirst=True)
    brief_status.create(op.get_bind(), checkfirst=True)
    brief_version_source.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "series",
        sa.Column("briefs_approved_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "episode_briefs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("kind", brief_kind, nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("brief_markdown", sa.Text(), nullable=False),
        sa.Column("status", brief_status, server_default="generated", nullable=False),
        sa.Column("current_version_id", sa.UUID(), nullable=True),
        sa.Column("approved_version_id", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_invalidated_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint(
            "series_id",
            "episode_id",
            "kind",
            name="uq_episode_briefs_episode_kind",
        ),
    )
    op.create_index("ix_episode_briefs_episode_id", "episode_briefs", ["episode_id"])
    op.create_index("ix_episode_briefs_series_id", "episode_briefs", ["series_id"])

    op.create_table(
        "brief_versions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("brief_id", sa.UUID(), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("outline_id", sa.UUID(), nullable=False),
        sa.Column("outline_version_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("brief_markdown", sa.Text(), nullable=False),
        sa.Column("source", brief_version_source, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["brief_id"], ["episode_briefs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["outline_id"], ["episode_outlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["outline_version_id"],
            ["outline_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brief_id", "version_number", name="uq_brief_versions_brief_version"),
    )
    op.create_index("ix_brief_versions_brief_id", "brief_versions", ["brief_id"])
    op.create_index("ix_brief_versions_episode_id", "brief_versions", ["episode_id"])
    op.create_index("ix_brief_versions_outline_id", "brief_versions", ["outline_id"])
    op.create_index(
        "ix_brief_versions_outline_version_id",
        "brief_versions",
        ["outline_version_id"],
    )
    op.create_index("ix_brief_versions_series_id", "brief_versions", ["series_id"])

    op.create_foreign_key(
        "fk_episode_briefs_current_version_id_brief_versions",
        "episode_briefs",
        "brief_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_episode_briefs_approved_version_id_brief_versions",
        "episode_briefs",
        "brief_versions",
        ["approved_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_episode_briefs_approved_version_id_brief_versions",
        "episode_briefs",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_episode_briefs_current_version_id_brief_versions",
        "episode_briefs",
        type_="foreignkey",
    )
    op.drop_index("ix_brief_versions_series_id", table_name="brief_versions")
    op.drop_index("ix_brief_versions_outline_version_id", table_name="brief_versions")
    op.drop_index("ix_brief_versions_outline_id", table_name="brief_versions")
    op.drop_index("ix_brief_versions_episode_id", table_name="brief_versions")
    op.drop_index("ix_brief_versions_brief_id", table_name="brief_versions")
    op.drop_table("brief_versions")
    op.drop_index("ix_episode_briefs_series_id", table_name="episode_briefs")
    op.drop_index("ix_episode_briefs_episode_id", table_name="episode_briefs")
    op.drop_table("episode_briefs")
    op.drop_column("series", "briefs_approved_at")
    brief_version_source.drop(op.get_bind(), checkfirst=True)
    brief_status.drop(op.get_bind(), checkfirst=True)
    brief_kind.drop(op.get_bind(), checkfirst=True)
