"""research scoring and explainability

Revision ID: 0025_research_scoring
Revises: 0024_research_runs
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025_research_scoring"
down_revision: str | None = "0024_research_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


research_confidence_level = postgresql.ENUM(
    "High",
    "Medium",
    "Low",
    "Weak",
    name="research_confidence_level",
    create_type=False,
)
research_score_entity_type = postgresql.ENUM(
    "research_document",
    "narrative",
    "episode_topic",
    "strategy_idea",
    "outline",
    "brief",
    name="research_score_entity_type",
    create_type=False,
)


def upgrade() -> None:
    research_confidence_level.create(op.get_bind(), checkfirst=True)
    research_score_entity_type.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "research_documents",
        sa.Column("tier", sa.String(length=1), server_default="D", nullable=False),
    )
    op.add_column(
        "research_documents",
        sa.Column("tier_score", sa.Integer(), server_default="25", nullable=False),
    )
    op.add_column(
        "research_documents",
        sa.Column("engagement_score", sa.Integer(), server_default="50", nullable=False),
    )
    op.add_column(
        "research_documents",
        sa.Column("freshness_score", sa.Integer(), server_default="45", nullable=False),
    )
    op.add_column(
        "research_documents",
        sa.Column("author_score", sa.Integer(), server_default="50", nullable=False),
    )
    op.add_column(
        "research_documents",
        sa.Column("composite_score", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "research_documents",
        sa.Column("trend_score", sa.Integer(), nullable=True),
    )
    op.add_column(
        "research_documents",
        sa.Column("trend_available", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "research_documents",
        sa.Column("trend_source", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "research_documents",
        sa.Column("trend_failure_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "research_documents",
        sa.Column(
            "confidence_level",
            research_confidence_level,
            server_default="Weak",
            nullable=False,
        ),
    )
    op.add_column(
        "research_documents",
        sa.Column(
            "score_explanation_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_research_documents_composite_score",
        "research_documents",
        ["composite_score"],
    )
    op.create_index(
        "ix_research_documents_confidence_level",
        "research_documents",
        ["confidence_level"],
    )

    op.create_table(
        "research_score_breakdowns",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("entity_type", research_score_entity_type, nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("research_run_id", sa.UUID(), nullable=True),
        sa.Column("tier_score_avg", sa.Integer(), server_default="0", nullable=False),
        sa.Column("engagement_score_avg", sa.Integer(), server_default="0", nullable=False),
        sa.Column("freshness_score_avg", sa.Integer(), server_default="0", nullable=False),
        sa.Column("author_score_avg", sa.Integer(), server_default="0", nullable=False),
        sa.Column("composite_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("trend_score", sa.Integer(), nullable=True),
        sa.Column("trend_available", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "confidence_level",
            research_confidence_level,
            server_default="Weak",
            nullable=False,
        ),
        sa.Column(
            "formula_version",
            sa.String(length=40),
            server_default="prd-r4-v1",
            nullable=False,
        ),
        sa.Column(
            "explanation_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_research_score_breakdowns_entity_type",
        "research_score_breakdowns",
        ["entity_type"],
    )
    op.create_index(
        "ix_research_score_breakdowns_entity_id",
        "research_score_breakdowns",
        ["entity_id"],
    )
    op.create_index(
        "ix_research_score_breakdowns_research_run_id",
        "research_score_breakdowns",
        ["research_run_id"],
    )
    op.create_index(
        "ix_research_score_breakdowns_composite_score",
        "research_score_breakdowns",
        ["composite_score"],
    )
    op.create_index(
        "ix_research_score_breakdowns_entity_created",
        "research_score_breakdowns",
        ["entity_type", "entity_id", "created_at"],
    )
    op.create_index(
        "ix_research_score_breakdowns_run_created",
        "research_score_breakdowns",
        ["research_run_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_research_score_breakdowns_run_created", table_name="research_score_breakdowns")
    op.drop_index(
        "ix_research_score_breakdowns_entity_created",
        table_name="research_score_breakdowns",
    )
    op.drop_index(
        "ix_research_score_breakdowns_composite_score",
        table_name="research_score_breakdowns",
    )
    op.drop_index(
        "ix_research_score_breakdowns_research_run_id",
        table_name="research_score_breakdowns",
    )
    op.drop_index(
        "ix_research_score_breakdowns_entity_id",
        table_name="research_score_breakdowns",
    )
    op.drop_index(
        "ix_research_score_breakdowns_entity_type",
        table_name="research_score_breakdowns",
    )
    op.drop_table("research_score_breakdowns")

    op.drop_index("ix_research_documents_confidence_level", table_name="research_documents")
    op.drop_index("ix_research_documents_composite_score", table_name="research_documents")
    op.drop_column("research_documents", "score_explanation_json")
    op.drop_column("research_documents", "confidence_level")
    op.drop_column("research_documents", "trend_failure_reason")
    op.drop_column("research_documents", "trend_source")
    op.drop_column("research_documents", "trend_available")
    op.drop_column("research_documents", "trend_score")
    op.drop_column("research_documents", "composite_score")
    op.drop_column("research_documents", "author_score")
    op.drop_column("research_documents", "freshness_score")
    op.drop_column("research_documents", "engagement_score")
    op.drop_column("research_documents", "tier_score")
    op.drop_column("research_documents", "tier")

    research_score_entity_type.drop(op.get_bind(), checkfirst=True)
    research_confidence_level.drop(op.get_bind(), checkfirst=True)
