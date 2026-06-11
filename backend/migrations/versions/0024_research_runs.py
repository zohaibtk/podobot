"""research runs persistence

Revision ID: 0024_research_runs
Revises: 0023_research_source_registry
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024_research_runs"
down_revision: str | None = "0023_research_source_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


research_run_type = postgresql.ENUM(
    "discovery",
    "strategy",
    "narrative_regeneration",
    "topic_generation",
    "brief_context",
    "manual_research",
    name="research_run_type",
    create_type=False,
)
research_run_status = postgresql.ENUM(
    "pending",
    "running",
    "completed",
    "partial_success",
    "failed",
    "cancelled",
    name="research_run_status",
    create_type=False,
)
research_source_usage_status = postgresql.ENUM(
    "used",
    "skipped_disabled",
    "failed",
    "no_results",
    name="research_source_usage_status",
    create_type=False,
)
research_ledger_type = postgresql.ENUM(
    "source",
    "signal",
    "narrative_support",
    "narrative_counter",
    "topic_support",
    "strategy_support",
    name="research_ledger_type",
    create_type=False,
)
research_source_provider_type = postgresql.ENUM(
    "reddit_json",
    "hn_algolia",
    "youtube_data_api",
    "exa",
    "firecrawl",
    "serpapi",
    "pytrends",
    "grok_x",
    "gemini",
    name="research_source_provider_type",
    create_type=False,
)


def upgrade() -> None:
    research_run_type.create(op.get_bind(), checkfirst=True)
    research_run_status.create(op.get_bind(), checkfirst=True)
    research_source_usage_status.create(op.get_bind(), checkfirst=True)
    research_ledger_type.create(op.get_bind(), checkfirst=True)

    op.add_column("mcp_tool_runs", sa.Column("research_run_id", sa.UUID(), nullable=True))
    op.create_index("ix_mcp_tool_runs_research_run_id", "mcp_tool_runs", ["research_run_id"])

    op.create_table(
        "research_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_type", research_run_type, nullable=False),
        sa.Column("status", research_run_status, server_default="pending", nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=True),
        sa.Column("episode_id", sa.UUID(), nullable=True),
        sa.Column("strategy_run_id", sa.UUID(), nullable=True),
        sa.Column("agent_run_id", sa.UUID(), nullable=True),
        sa.Column("mcp_tool_run_id", sa.UUID(), nullable=True),
        sa.Column("initiated_by_user_id", sa.UUID(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("enabled_source_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("successful_source_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_source_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped_source_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_documents_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_documents_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["initiated_by_user_id"], ["workspace_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mcp_tool_run_id"], ["mcp_tool_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["strategy_run_id"], ["strategy_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_runs_agent_run_id", "research_runs", ["agent_run_id"])
    op.create_index("ix_research_runs_episode_id", "research_runs", ["episode_id"])
    op.create_index("ix_research_runs_episode_created_at", "research_runs", ["episode_id", "created_at"])
    op.create_index("ix_research_runs_initiated_by_user_id", "research_runs", ["initiated_by_user_id"])
    op.create_index("ix_research_runs_mcp_tool_run_id", "research_runs", ["mcp_tool_run_id"])
    op.create_index("ix_research_runs_run_type", "research_runs", ["run_type"])
    op.create_index("ix_research_runs_run_type_created_at", "research_runs", ["run_type", "created_at"])
    op.create_index("ix_research_runs_series_id", "research_runs", ["series_id"])
    op.create_index("ix_research_runs_series_created_at", "research_runs", ["series_id", "created_at"])
    op.create_index("ix_research_runs_status", "research_runs", ["status"])
    op.create_index("ix_research_runs_status_created_at", "research_runs", ["status", "created_at"])
    op.create_index("ix_research_runs_strategy_run_id", "research_runs", ["strategy_run_id"])
    op.create_index("ix_research_runs_strategy_created_at", "research_runs", ["strategy_run_id", "created_at"])

    op.create_table(
        "research_run_source_usage",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("research_run_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("status", research_source_usage_status, nullable=False),
        sa.Column("query_text", sa.Text(), nullable=True),
        sa.Column("documents_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("documents_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["research_sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_run_source_usage_research_run_id", "research_run_source_usage", ["research_run_id"])
    op.create_index("ix_research_run_source_usage_source_id", "research_run_source_usage", ["source_id"])
    op.create_index("ix_research_run_source_usage_status", "research_run_source_usage", ["status"])
    op.create_index("ix_research_source_usage_run_status", "research_run_source_usage", ["research_run_id", "status"])
    op.create_index("ix_research_source_usage_source_started", "research_run_source_usage", ["source_id", "started_at"])

    op.create_table(
        "research_documents",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("research_run_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("provider_type", research_source_provider_type, nullable=False),
        sa.Column("external_resource_id", sa.String(length=500), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=240), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("content_excerpt", sa.Text(), nullable=True),
        sa.Column("normalized_content", sa.Text(), nullable=True),
        sa.Column(
            "raw_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("used_in_output", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("archived", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["research_sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_documents_archived", "research_documents", ["archived"])
    op.create_index("ix_research_documents_archived_created", "research_documents", ["archived", "created_at"])
    op.create_index("ix_research_documents_provider_created", "research_documents", ["provider_type", "created_at"])
    op.create_index("ix_research_documents_provider_type", "research_documents", ["provider_type"])
    op.create_index("ix_research_documents_research_run_id", "research_documents", ["research_run_id"])
    op.create_index("ix_research_documents_run_created", "research_documents", ["research_run_id", "created_at"])
    op.create_index("ix_research_documents_source_created", "research_documents", ["source_id", "created_at"])
    op.create_index("ix_research_documents_source_id", "research_documents", ["source_id"])
    op.create_index("ix_research_documents_used_in_output", "research_documents", ["used_in_output"])

    op.create_table(
        "research_discovery_ledger_entries",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("research_run_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("series_id", sa.UUID(), nullable=True),
        sa.Column("episode_id", sa.UUID(), nullable=True),
        sa.Column("strategy_idea_id", sa.UUID(), nullable=True),
        sa.Column("ledger_type", research_ledger_type, nullable=False),
        sa.Column("evidence_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["research_documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["research_sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["strategy_idea_id"], ["strategy_ideas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_discovery_ledger_entries_document_id", "research_discovery_ledger_entries", ["document_id"])
    op.create_index("ix_research_discovery_ledger_entries_episode_id", "research_discovery_ledger_entries", ["episode_id"])
    op.create_index("ix_research_discovery_ledger_entries_ledger_type", "research_discovery_ledger_entries", ["ledger_type"])
    op.create_index("ix_research_discovery_ledger_entries_research_run_id", "research_discovery_ledger_entries", ["research_run_id"])
    op.create_index("ix_research_discovery_ledger_entries_series_id", "research_discovery_ledger_entries", ["series_id"])
    op.create_index("ix_research_discovery_ledger_entries_source_id", "research_discovery_ledger_entries", ["source_id"])
    op.create_index("ix_research_discovery_ledger_entries_strategy_idea_id", "research_discovery_ledger_entries", ["strategy_idea_id"])
    op.create_index("ix_research_ledger_episode_created", "research_discovery_ledger_entries", ["episode_id", "created_at"])
    op.create_index("ix_research_ledger_run_created", "research_discovery_ledger_entries", ["research_run_id", "created_at"])
    op.create_index("ix_research_ledger_series_created", "research_discovery_ledger_entries", ["series_id", "created_at"])
    op.create_index("ix_research_ledger_source_created", "research_discovery_ledger_entries", ["source_id", "created_at"])
    op.create_index("ix_research_ledger_strategy_idea_created", "research_discovery_ledger_entries", ["strategy_idea_id", "created_at"])
    op.create_index("ix_research_ledger_type_created", "research_discovery_ledger_entries", ["ledger_type", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_research_ledger_type_created", table_name="research_discovery_ledger_entries")
    op.drop_index("ix_research_ledger_strategy_idea_created", table_name="research_discovery_ledger_entries")
    op.drop_index("ix_research_ledger_source_created", table_name="research_discovery_ledger_entries")
    op.drop_index("ix_research_ledger_series_created", table_name="research_discovery_ledger_entries")
    op.drop_index("ix_research_ledger_run_created", table_name="research_discovery_ledger_entries")
    op.drop_index("ix_research_ledger_episode_created", table_name="research_discovery_ledger_entries")
    op.drop_index("ix_research_discovery_ledger_entries_strategy_idea_id", table_name="research_discovery_ledger_entries")
    op.drop_index("ix_research_discovery_ledger_entries_source_id", table_name="research_discovery_ledger_entries")
    op.drop_index("ix_research_discovery_ledger_entries_series_id", table_name="research_discovery_ledger_entries")
    op.drop_index("ix_research_discovery_ledger_entries_research_run_id", table_name="research_discovery_ledger_entries")
    op.drop_index("ix_research_discovery_ledger_entries_ledger_type", table_name="research_discovery_ledger_entries")
    op.drop_index("ix_research_discovery_ledger_entries_episode_id", table_name="research_discovery_ledger_entries")
    op.drop_index("ix_research_discovery_ledger_entries_document_id", table_name="research_discovery_ledger_entries")
    op.drop_table("research_discovery_ledger_entries")

    op.drop_index("ix_research_documents_used_in_output", table_name="research_documents")
    op.drop_index("ix_research_documents_source_id", table_name="research_documents")
    op.drop_index("ix_research_documents_source_created", table_name="research_documents")
    op.drop_index("ix_research_documents_run_created", table_name="research_documents")
    op.drop_index("ix_research_documents_research_run_id", table_name="research_documents")
    op.drop_index("ix_research_documents_provider_type", table_name="research_documents")
    op.drop_index("ix_research_documents_provider_created", table_name="research_documents")
    op.drop_index("ix_research_documents_archived_created", table_name="research_documents")
    op.drop_index("ix_research_documents_archived", table_name="research_documents")
    op.drop_table("research_documents")

    op.drop_index("ix_research_source_usage_source_started", table_name="research_run_source_usage")
    op.drop_index("ix_research_source_usage_run_status", table_name="research_run_source_usage")
    op.drop_index("ix_research_run_source_usage_status", table_name="research_run_source_usage")
    op.drop_index("ix_research_run_source_usage_source_id", table_name="research_run_source_usage")
    op.drop_index("ix_research_run_source_usage_research_run_id", table_name="research_run_source_usage")
    op.drop_table("research_run_source_usage")

    op.drop_index("ix_research_runs_strategy_created_at", table_name="research_runs")
    op.drop_index("ix_research_runs_strategy_run_id", table_name="research_runs")
    op.drop_index("ix_research_runs_status_created_at", table_name="research_runs")
    op.drop_index("ix_research_runs_status", table_name="research_runs")
    op.drop_index("ix_research_runs_series_created_at", table_name="research_runs")
    op.drop_index("ix_research_runs_series_id", table_name="research_runs")
    op.drop_index("ix_research_runs_run_type_created_at", table_name="research_runs")
    op.drop_index("ix_research_runs_run_type", table_name="research_runs")
    op.drop_index("ix_research_runs_mcp_tool_run_id", table_name="research_runs")
    op.drop_index("ix_research_runs_initiated_by_user_id", table_name="research_runs")
    op.drop_index("ix_research_runs_episode_created_at", table_name="research_runs")
    op.drop_index("ix_research_runs_episode_id", table_name="research_runs")
    op.drop_index("ix_research_runs_agent_run_id", table_name="research_runs")
    op.drop_table("research_runs")

    op.drop_index("ix_mcp_tool_runs_research_run_id", table_name="mcp_tool_runs")
    op.drop_column("mcp_tool_runs", "research_run_id")

    research_ledger_type.drop(op.get_bind(), checkfirst=True)
    research_source_usage_status.drop(op.get_bind(), checkfirst=True)
    research_run_status.drop(op.get_bind(), checkfirst=True)
    research_run_type.drop(op.get_bind(), checkfirst=True)
