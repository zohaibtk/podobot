"""strategy module

Revision ID: 0011_strategy_module
Revises: 0010_scheduling_buffer
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_strategy_module"
down_revision: str | None = "0010_scheduling_buffer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


agent_run_status = postgresql.ENUM(
    "queued",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    "requires_human",
    name="agent_run_status",
    create_type=False,
)
strategy_idea_status = postgresql.ENUM(
    "proposed",
    "in_review",
    "dismissed",
    "converted",
    name="strategy_idea_status",
    create_type=False,
)


def upgrade() -> None:
    agent_run_status.create(op.get_bind(), checkfirst=True)
    strategy_idea_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "strategy_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("topic", sa.String(length=220), nullable=False),
        sa.Column("status", agent_run_status, server_default="succeeded", nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_strategy_runs_run_date", "strategy_runs", ["run_date"])

    op.create_table(
        "strategy_ideas",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("audience", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("proposed_guest_name", sa.String(length=180), nullable=True),
        sa.Column("thesis", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("evidence_signals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_proposal", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence_score", sa.Integer(), server_default="75", nullable=False),
        sa.Column(
            "status",
            strategy_idea_status,
            server_default="proposed",
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_series_id", sa.UUID(), nullable=True),
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
            "confidence_score >= 0 AND confidence_score <= 100",
            name="ck_strategy_ideas_confidence_score_range",
        ),
        sa.ForeignKeyConstraint(["converted_series_id"], ["series.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["strategy_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_strategy_ideas_converted_series_id",
        "strategy_ideas",
        ["converted_series_id"],
    )
    op.create_index("ix_strategy_ideas_run_id", "strategy_ideas", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_strategy_ideas_run_id", table_name="strategy_ideas")
    op.drop_index("ix_strategy_ideas_converted_series_id", table_name="strategy_ideas")
    op.drop_table("strategy_ideas")
    op.drop_index("ix_strategy_runs_run_date", table_name="strategy_runs")
    op.drop_table("strategy_runs")

    strategy_idea_status.drop(op.get_bind(), checkfirst=True)
    agent_run_status.drop(op.get_bind(), checkfirst=True)
