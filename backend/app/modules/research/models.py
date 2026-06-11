from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import (
    DiscoveryLedgerType,
    ResearchConfidenceLevel,
    ResearchRunSourceUsageStatus,
    ResearchRunStatus,
    ResearchRunType,
    ResearchScoreEntityType,
    ResearchSourceProviderType,
)
from app.modules.series.models import enum_values


class ResearchRun(Base):
    __tablename__ = "research_runs"
    __table_args__ = (
        Index("ix_research_runs_status_created_at", "status", "created_at"),
        Index("ix_research_runs_run_type_created_at", "run_type", "created_at"),
        Index("ix_research_runs_series_created_at", "series_id", "created_at"),
        Index("ix_research_runs_episode_created_at", "episode_id", "created_at"),
        Index("ix_research_runs_strategy_created_at", "strategy_run_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    run_type: Mapped[ResearchRunType] = mapped_column(
        Enum(ResearchRunType, name="research_run_type", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    status: Mapped[ResearchRunStatus] = mapped_column(
        Enum(ResearchRunStatus, name="research_run_status", values_callable=enum_values),
        nullable=False,
        default=ResearchRunStatus.PENDING,
        server_default=ResearchRunStatus.PENDING.value,
        index=True,
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    series_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("series.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    episode_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("episodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    strategy_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("strategy_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    agent_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mcp_tool_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("mcp_tool_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    initiated_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspace_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled_source_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    successful_source_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    failed_source_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    skipped_source_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_documents_found: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_documents_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ResearchRunSourceUsage(Base):
    __tablename__ = "research_run_source_usage"
    __table_args__ = (
        Index("ix_research_source_usage_run_status", "research_run_id", "status"),
        Index("ix_research_source_usage_source_started", "source_id", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    research_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("research_sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[ResearchRunSourceUsageStatus] = mapped_column(
        Enum(
            ResearchRunSourceUsageStatus,
            name="research_source_usage_status",
            values_callable=enum_values,
        ),
        nullable=False,
        index=True,
    )
    query_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    documents_found: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    documents_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ResearchDocument(Base):
    __tablename__ = "research_documents"
    __table_args__ = (
        Index("ix_research_documents_run_created", "research_run_id", "created_at"),
        Index("ix_research_documents_source_created", "source_id", "created_at"),
        Index("ix_research_documents_provider_created", "provider_type", "created_at"),
        Index("ix_research_documents_archived_created", "archived", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    research_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("research_sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    provider_type: Mapped[ResearchSourceProviderType] = mapped_column(
        Enum(
            ResearchSourceProviderType,
            name="research_source_provider_type",
            values_callable=enum_values,
        ),
        nullable=False,
        index=True,
    )
    external_resource_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(240), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False, default="document")
    content_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    tier: Mapped[str] = mapped_column(String(1), nullable=False, default="D", server_default="D")
    tier_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=25,
        server_default="25",
    )
    engagement_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
        server_default="50",
    )
    freshness_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=45,
        server_default="45",
    )
    author_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
        server_default="50",
    )
    composite_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        index=True,
    )
    trend_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trend_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    trend_source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    trend_failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_level: Mapped[ResearchConfidenceLevel] = mapped_column(
        Enum(
            ResearchConfidenceLevel,
            name="research_confidence_level",
            values_callable=enum_values,
        ),
        nullable=False,
        default=ResearchConfidenceLevel.WEAK,
        server_default=ResearchConfidenceLevel.WEAK.value,
        index=True,
    )
    score_explanation_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    used_in_output: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )
    archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ResearchScoreBreakdown(Base):
    __tablename__ = "research_score_breakdowns"
    __table_args__ = (
        Index(
            "ix_research_score_breakdowns_entity_created",
            "entity_type",
            "entity_id",
            "created_at",
        ),
        Index("ix_research_score_breakdowns_run_created", "research_run_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    entity_type: Mapped[ResearchScoreEntityType] = mapped_column(
        Enum(
            ResearchScoreEntityType,
            name="research_score_entity_type",
            values_callable=enum_values,
        ),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), nullable=False, index=True)
    research_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("research_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tier_score_avg: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    engagement_score_avg: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    freshness_score_avg: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    author_score_avg: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    composite_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        index=True,
    )
    trend_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trend_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    confidence_level: Mapped[ResearchConfidenceLevel] = mapped_column(
        Enum(
            ResearchConfidenceLevel,
            name="research_confidence_level",
            values_callable=enum_values,
        ),
        nullable=False,
        default=ResearchConfidenceLevel.WEAK,
        server_default=ResearchConfidenceLevel.WEAK.value,
    )
    formula_version: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="prd-r4-v1",
        server_default="prd-r4-v1",
    )
    explanation_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DiscoveryLedgerEntry(Base):
    __tablename__ = "research_discovery_ledger_entries"
    __table_args__ = (
        Index("ix_research_ledger_run_created", "research_run_id", "created_at"),
        Index("ix_research_ledger_source_created", "source_id", "created_at"),
        Index("ix_research_ledger_series_created", "series_id", "created_at"),
        Index("ix_research_ledger_episode_created", "episode_id", "created_at"),
        Index("ix_research_ledger_strategy_idea_created", "strategy_idea_id", "created_at"),
        Index("ix_research_ledger_type_created", "ledger_type", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    research_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("research_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("research_sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    series_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("series.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    episode_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("episodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    strategy_idea_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("strategy_ideas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ledger_type: Mapped[DiscoveryLedgerType] = mapped_column(
        Enum(DiscoveryLedgerType, name="research_ledger_type", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    evidence_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
