"""discovery and narratives

Revision ID: 0003_discovery_narratives
Revises: 0002_series_foundation
Create Date: 2026-06-06
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_discovery_narratives"
down_revision: str | None = "0002_series_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


research_source_status = postgresql.ENUM(
    "pending",
    "running",
    "complete",
    "failed",
    name="research_source_status",
    create_type=False,
)
narrative_status = postgresql.ENUM(
    "candidate",
    "selected",
    "retired",
    name="narrative_status",
    create_type=False,
)


def upgrade() -> None:
    research_source_status.create(op.get_bind(), checkfirst=True)
    narrative_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "discovery_ledger_entries",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("source_name", sa.String(length=180), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("status", research_source_status, server_default="pending", nullable=False),
        sa.Column("signal_title", sa.String(length=220), nullable=False),
        sa.Column("signal_summary", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_discovery_ledger_entries_series_id",
        "discovery_ledger_entries",
        ["series_id"],
    )

    op.create_table(
        "narratives",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("thesis", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("supporting_signals", postgresql.JSONB(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("status", narrative_status, server_default="candidate", nullable=False),
        sa.Column("is_selected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_narratives_series_id", "narratives", ["series_id"])
    op.create_index(
        "uq_narratives_one_selected_per_series",
        "narratives",
        ["series_id"],
        unique=True,
        postgresql_where=sa.text("is_selected = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_narratives_one_selected_per_series", table_name="narratives")
    op.drop_index("ix_narratives_series_id", table_name="narratives")
    op.drop_table("narratives")
    op.drop_index("ix_discovery_ledger_entries_series_id", table_name="discovery_ledger_entries")
    op.drop_table("discovery_ledger_entries")
    narrative_status.drop(op.get_bind(), checkfirst=True)
    research_source_status.drop(op.get_bind(), checkfirst=True)
