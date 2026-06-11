"""research source registry

Revision ID: 0023_research_source_registry
Revises: 0022_pagination_indexes
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023_research_source_registry"
down_revision: str | None = "0022_pagination_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
research_source_category = postgresql.ENUM(
    "discovery",
    "scraping",
    "trends",
    "llm",
    name="research_source_category",
    create_type=False,
)
research_source_registry_status = postgresql.ENUM(
    "healthy",
    "warning",
    "failed",
    "disabled",
    "unknown",
    name="research_source_registry_status",
    create_type=False,
)


def upgrade() -> None:
    research_source_provider_type.create(op.get_bind(), checkfirst=True)
    research_source_category.create(op.get_bind(), checkfirst=True)
    research_source_registry_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "research_sources",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("provider_type", research_source_provider_type, nullable=False),
        sa.Column("category", research_source_category, nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("critical", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("priority", sa.Integer(), server_default="100", nullable=False),
        sa.Column(
            "status",
            research_source_registry_status,
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("quota_status", sa.String(length=120), server_default="unknown", nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "documents_fetched_today",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("success_rate", sa.Float(), server_default="0", nullable=False),
        sa.Column("average_latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("recent_failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "config_json",
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("priority >= 0", name="priority_non_negative"),
        sa.CheckConstraint(
            "documents_fetched_today >= 0",
            name="documents_non_negative",
        ),
        sa.CheckConstraint(
            "success_rate >= 0 AND success_rate <= 1",
            name="success_rate_range",
        ),
        sa.CheckConstraint(
            "average_latency_ms >= 0",
            name="latency_non_negative",
        ),
        sa.CheckConstraint(
            "recent_failure_count >= 0",
            name="failures_non_negative",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_research_sources_key"),
    )
    op.create_index("ix_research_sources_key", "research_sources", ["key"])
    op.create_index(
        "ix_research_sources_category_priority",
        "research_sources",
        ["category", "priority"],
    )
    op.create_index(
        "ix_research_sources_enabled_priority",
        "research_sources",
        ["enabled", "priority"],
    )
    op.create_index(
        "ix_research_sources_status_priority",
        "research_sources",
        ["status", "priority"],
    )
    op.create_index(
        "ix_research_sources_provider_type",
        "research_sources",
        ["provider_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_research_sources_provider_type", table_name="research_sources")
    op.drop_index("ix_research_sources_status_priority", table_name="research_sources")
    op.drop_index("ix_research_sources_enabled_priority", table_name="research_sources")
    op.drop_index("ix_research_sources_category_priority", table_name="research_sources")
    op.drop_index("ix_research_sources_key", table_name="research_sources")
    op.drop_table("research_sources")

    research_source_registry_status.drop(op.get_bind(), checkfirst=True)
    research_source_category.drop(op.get_bind(), checkfirst=True)
    research_source_provider_type.drop(op.get_bind(), checkfirst=True)
