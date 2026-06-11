"""episode plan

Revision ID: 0004_episode_plan
Revises: 0003_discovery_narratives
Create Date: 2026-06-06
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_episode_plan"
down_revision: str | None = "0003_discovery_narratives"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


profile_kind = postgresql.ENUM("host", "guest", name="profile_kind", create_type=False)
episode_status = postgresql.ENUM(
    "planned",
    "outlined",
    "profiles_set",
    "brief_ready",
    "approved",
    "recorded",
    "captioning",
    "scheduled",
    "partially_published",
    "published",
    name="episode_status",
    create_type=False,
)
episode_outline_status = postgresql.ENUM(
    "placeholder",
    "generated",
    name="episode_outline_status",
    create_type=False,
)


def upgrade() -> None:
    profile_kind.create(op.get_bind(), checkfirst=True)
    episode_status.create(op.get_bind(), checkfirst=True)
    episode_outline_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "series",
        sa.Column("episode_plan_generated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("series", sa.Column("plan_locked_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "profiles",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("role_title", sa.String(length=180), nullable=False),
        sa.Column("kind", profile_kind, nullable=False),
        sa.Column("archetype", sa.String(length=240), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kind", "name", name="uq_profiles_kind_name"),
    )
    op.create_index("ix_profiles_kind", "profiles", ["kind"])

    op.create_table(
        "episodes",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("premise", sa.Text(), nullable=False),
        sa.Column("status", episode_status, server_default="planned", nullable=False),
        sa.Column("host_profile_id", sa.UUID(), nullable=True),
        sa.Column("guest_profile_id", sa.UUID(), nullable=True),
        sa.Column("guest_name_override", sa.String(length=180), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("episode_number > 0", name="ck_episodes_episode_number_positive"),
        sa.CheckConstraint(
            "host_profile_id IS NULL OR guest_profile_id IS NULL OR host_profile_id <> guest_profile_id",
            name="ck_episodes_host_guest_profile_different",
        ),
        sa.ForeignKeyConstraint(["guest_profile_id"], ["profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["host_profile_id"], ["profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("series_id", "episode_number", name="uq_episodes_series_episode_number"),
    )
    op.create_index("ix_episodes_series_id", "episodes", ["series_id"])

    op.create_table(
        "episode_outline_placeholders",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("outline_markdown", sa.Text(), nullable=False),
        sa.Column("status", episode_outline_status, server_default="placeholder", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("episode_id", name="uq_episode_outline_placeholders_episode_id"),
    )
    op.create_index(
        "ix_episode_outline_placeholders_series_id",
        "episode_outline_placeholders",
        ["series_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_episode_outline_placeholders_series_id",
        table_name="episode_outline_placeholders",
    )
    op.drop_table("episode_outline_placeholders")
    op.drop_index("ix_episodes_series_id", table_name="episodes")
    op.drop_table("episodes")
    op.drop_index("ix_profiles_kind", table_name="profiles")
    op.drop_table("profiles")
    op.drop_column("series", "plan_locked_at")
    op.drop_column("series", "episode_plan_generated_at")
    episode_outline_status.drop(op.get_bind(), checkfirst=True)
    episode_status.drop(op.get_bind(), checkfirst=True)
    profile_kind.drop(op.get_bind(), checkfirst=True)
