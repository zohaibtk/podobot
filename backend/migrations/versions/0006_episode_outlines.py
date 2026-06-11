"""episode outlines

Revision ID: 0006_episode_outlines
Revises: 0005_profile_library
Create Date: 2026-06-06
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_episode_outlines"
down_revision: str | None = "0005_profile_library"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


outline_version_source = postgresql.ENUM(
    "lock_generated",
    "manual_edit",
    "regeneration",
    name="outline_version_source",
    create_type=False,
)


def upgrade() -> None:
    op.execute("ALTER TYPE episode_outline_status ADD VALUE IF NOT EXISTS 'draft'")
    op.execute("ALTER TYPE episode_outline_status ADD VALUE IF NOT EXISTS 'approved'")
    outline_version_source.create(op.get_bind(), checkfirst=True)

    op.rename_table("episode_outline_placeholders", "episode_outlines")
    op.execute(
        "ALTER TABLE episode_outlines "
        "RENAME CONSTRAINT pk_episode_outline_placeholders TO pk_episode_outlines"
    )
    op.execute(
        "ALTER TABLE episode_outlines "
        "RENAME CONSTRAINT uq_episode_outline_placeholders_episode_id "
        "TO uq_episode_outlines_episode_id"
    )
    op.execute(
        "ALTER TABLE episode_outlines "
        "RENAME CONSTRAINT fk_episode_outline_placeholders_episode_id_episodes "
        "TO fk_episode_outlines_episode_id_episodes"
    )
    op.execute(
        "ALTER TABLE episode_outlines "
        "RENAME CONSTRAINT fk_episode_outline_placeholders_series_id_series "
        "TO fk_episode_outlines_series_id_series"
    )
    op.execute(
        "ALTER INDEX ix_episode_outline_placeholders_series_id "
        "RENAME TO ix_episode_outlines_series_id"
    )

    op.alter_column(
        "episode_outlines",
        "status",
        server_default="generated",
        existing_type=postgresql.ENUM(name="episode_outline_status"),
    )
    op.add_column("episode_outlines", sa.Column("current_version_id", sa.UUID(), nullable=True))
    op.add_column("episode_outlines", sa.Column("approved_version_id", sa.UUID(), nullable=True))
    op.add_column("episode_outlines", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "outline_versions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("outline_id", sa.UUID(), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("outline_markdown", sa.Text(), nullable=False),
        sa.Column("source", outline_version_source, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["outline_id"], ["episode_outlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("outline_id", "version_number", name="uq_outline_versions_outline_version"),
    )
    op.create_index("ix_outline_versions_episode_id", "outline_versions", ["episode_id"])
    op.create_index("ix_outline_versions_outline_id", "outline_versions", ["outline_id"])
    op.create_index("ix_outline_versions_series_id", "outline_versions", ["series_id"])

    op.execute(
        """
        WITH version_rows AS (
            SELECT
                gen_random_uuid() AS id,
                id AS outline_id,
                series_id,
                episode_id,
                1 AS version_number,
                title,
                outline_markdown,
                'lock_generated'::outline_version_source AS source
            FROM episode_outlines
        ),
        inserted AS (
            INSERT INTO outline_versions (
                id,
                outline_id,
                series_id,
                episode_id,
                version_number,
                title,
                outline_markdown,
                source
            )
            SELECT
                id,
                outline_id,
                series_id,
                episode_id,
                version_number,
                title,
                outline_markdown,
                source
            FROM version_rows
            RETURNING id, outline_id
        )
        UPDATE episode_outlines
        SET current_version_id = inserted.id,
            status = 'generated'
        FROM inserted
        WHERE episode_outlines.id = inserted.outline_id
        """
    )

    op.create_foreign_key(
        "fk_episode_outlines_current_version_id_outline_versions",
        "episode_outlines",
        "outline_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_episode_outlines_approved_version_id_outline_versions",
        "episode_outlines",
        "outline_versions",
        ["approved_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_episode_outlines_approved_version_id_outline_versions",
        "episode_outlines",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_episode_outlines_current_version_id_outline_versions",
        "episode_outlines",
        type_="foreignkey",
    )
    op.drop_index("ix_outline_versions_series_id", table_name="outline_versions")
    op.drop_index("ix_outline_versions_outline_id", table_name="outline_versions")
    op.drop_index("ix_outline_versions_episode_id", table_name="outline_versions")
    op.drop_table("outline_versions")
    op.drop_column("episode_outlines", "approved_at")
    op.drop_column("episode_outlines", "approved_version_id")
    op.drop_column("episode_outlines", "current_version_id")
    op.alter_column(
        "episode_outlines",
        "status",
        server_default="placeholder",
        existing_type=postgresql.ENUM(name="episode_outline_status"),
    )
    op.execute("ALTER INDEX ix_episode_outlines_series_id RENAME TO ix_episode_outline_placeholders_series_id")
    op.execute(
        "ALTER TABLE episode_outlines "
        "RENAME CONSTRAINT fk_episode_outlines_series_id_series "
        "TO fk_episode_outline_placeholders_series_id_series"
    )
    op.execute(
        "ALTER TABLE episode_outlines "
        "RENAME CONSTRAINT fk_episode_outlines_episode_id_episodes "
        "TO fk_episode_outline_placeholders_episode_id_episodes"
    )
    op.execute(
        "ALTER TABLE episode_outlines "
        "RENAME CONSTRAINT uq_episode_outlines_episode_id "
        "TO uq_episode_outline_placeholders_episode_id"
    )
    op.execute(
        "ALTER TABLE episode_outlines "
        "RENAME CONSTRAINT pk_episode_outlines TO pk_episode_outline_placeholders"
    )
    op.rename_table("episode_outlines", "episode_outline_placeholders")
    outline_version_source.drop(op.get_bind(), checkfirst=True)
