"""strategy opportunity intelligence

Revision ID: 0027_strategy_opportunity
Revises: 0026_short_clip_media_uploads
Create Date: 2026-06-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027_strategy_opportunity"
down_revision: str | None = "0026_short_clip_media_uploads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "strategy_ideas",
        sa.Column("opportunity_score", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "strategy_ideas",
        sa.Column(
            "opportunity_score_breakdown",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "strategy_ideas",
        sa.Column(
            "opportunity_score_explanation",
            sa.Text(),
            server_default="Opportunity score has not been calculated yet.",
            nullable=False,
        ),
    )
    op.add_column(
        "strategy_ideas",
        sa.Column(
            "audience_intelligence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "strategy_ideas",
        sa.Column("lifecycle_stage", sa.String(length=32), server_default="emerging", nullable=False),
    )
    op.add_column(
        "strategy_ideas",
        sa.Column(
            "season_potential",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "strategy_ideas",
        sa.Column(
            "trend_intelligence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "strategy_ideas",
        sa.Column("source_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "strategy_ideas",
        sa.Column("potential_episode_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "strategy_ideas",
        sa.Column("theme_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "strategy_ideas",
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_strategy_ideas_opportunity_score_range",
        "strategy_ideas",
        "opportunity_score >= 0 AND opportunity_score <= 100",
    )
    op.create_index(
        "ix_strategy_ideas_lifecycle_stage",
        "strategy_ideas",
        ["lifecycle_stage"],
    )
    op.create_index(
        "ix_strategy_ideas_status_opportunity",
        "strategy_ideas",
        ["status", "opportunity_score"],
    )


def downgrade() -> None:
    op.drop_index("ix_strategy_ideas_status_opportunity", table_name="strategy_ideas")
    op.drop_index("ix_strategy_ideas_lifecycle_stage", table_name="strategy_ideas")
    op.drop_constraint(
        "ck_strategy_ideas_opportunity_score_range",
        "strategy_ideas",
        type_="check",
    )
    op.drop_column("strategy_ideas", "generated_at")
    op.drop_column("strategy_ideas", "theme_count")
    op.drop_column("strategy_ideas", "potential_episode_count")
    op.drop_column("strategy_ideas", "source_count")
    op.drop_column("strategy_ideas", "trend_intelligence")
    op.drop_column("strategy_ideas", "season_potential")
    op.drop_column("strategy_ideas", "lifecycle_stage")
    op.drop_column("strategy_ideas", "audience_intelligence")
    op.drop_column("strategy_ideas", "opportunity_score_explanation")
    op.drop_column("strategy_ideas", "opportunity_score_breakdown")
    op.drop_column("strategy_ideas", "opportunity_score")
