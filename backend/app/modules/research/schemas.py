from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.types import (
    DiscoveryLedgerType,
    ResearchConfidenceLevel,
    ResearchRunSourceUsageStatus,
    ResearchRunStatus,
    ResearchRunType,
    ResearchScoreEntityType,
    ResearchSourceProviderType,
)
from app.schemas.pagination import OffsetPageResponse


class ResearchRunStatsResponse(BaseModel):
    total_runs: int = 0
    running_runs: int = 0
    failed_runs: int = 0
    total_documents_found: int = 0
    total_documents_used: int = 0
    average_duration_ms: int = 0


class ResearchRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_type: ResearchRunType
    status: ResearchRunStatus
    query_text: str
    series_id: UUID | None = None
    episode_id: UUID | None = None
    strategy_run_id: UUID | None = None
    agent_run_id: UUID | None = None
    mcp_tool_run_id: UUID | None = None
    initiated_by_user_id: UUID | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    failure_reason: str | None = None
    enabled_source_count: int
    successful_source_count: int
    failed_source_count: int
    skipped_source_count: int
    total_documents_found: int
    total_documents_used: int
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class ResearchRunSourceUsageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    research_run_id: UUID
    source_id: UUID
    source_key: str
    source_name: str
    provider_type: ResearchSourceProviderType
    status: ResearchRunSourceUsageStatus
    query_text: str | None = None
    documents_found: int
    documents_used: int
    latency_ms: int
    failure_reason: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class ResearchDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    research_run_id: UUID
    source_id: UUID
    source_key: str
    source_name: str
    provider_type: ResearchSourceProviderType
    external_resource_id: str | None = None
    title: str
    url: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime
    resource_type: str
    content_excerpt: str | None = None
    normalized_content: str | None = None
    raw_metadata_json: dict[str, object]
    tier: str
    tier_score: int
    engagement_score: int
    freshness_score: int
    author_score: int
    composite_score: int
    trend_score: int | None = None
    trend_available: bool
    trend_source: str | None = None
    trend_failure_reason: str | None = None
    confidence_level: ResearchConfidenceLevel
    score_explanation_json: dict[str, object]
    used_in_output: bool
    archived: bool
    created_at: datetime


class DiscoveryLedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    research_run_id: UUID
    document_id: UUID | None = None
    source_id: UUID
    source_key: str
    source_name: str
    provider_type: ResearchSourceProviderType
    document_title: str | None = None
    document_url: str | None = None
    document_tier: str | None = None
    document_tier_score: int | None = None
    document_engagement_score: int | None = None
    document_freshness_score: int | None = None
    document_author_score: int | None = None
    document_composite_score: int | None = None
    document_confidence_level: ResearchConfidenceLevel | None = None
    document_trend_score: int | None = None
    document_trend_available: bool | None = None
    document_score_explanation_json: dict[str, object] | None = None
    series_id: UUID | None = None
    episode_id: UUID | None = None
    strategy_idea_id: UUID | None = None
    ledger_type: DiscoveryLedgerType
    evidence_summary: str
    created_at: datetime


class ResearchRunListResponse(OffsetPageResponse):
    items: list[ResearchRunResponse]
    stats: ResearchRunStatsResponse = Field(default_factory=ResearchRunStatsResponse)


class ResearchRunDetailResponse(ResearchRunResponse):
    source_usage: list[ResearchRunSourceUsageResponse] = Field(default_factory=list)
    documents: list[ResearchDocumentResponse] = Field(default_factory=list)
    ledger_entries: list[DiscoveryLedgerEntryResponse] = Field(default_factory=list)
    score_summary: dict[str, object] = Field(default_factory=dict)


class ResearchDocumentListResponse(OffsetPageResponse):
    items: list[ResearchDocumentResponse]


class DiscoveryLedgerListResponse(OffsetPageResponse):
    items: list[DiscoveryLedgerEntryResponse]


class ResearchRunSourceUsageListResponse(OffsetPageResponse):
    items: list[ResearchRunSourceUsageResponse]


class ResearchActionResponse(BaseModel):
    success: bool
    message: str
    run: ResearchRunResponse | None = None
    document: ResearchDocumentResponse | None = None


class ResearchDocumentScoreResponse(BaseModel):
    document_id: UUID
    research_run_id: UUID
    source_id: UUID
    source_key: str
    source_name: str
    provider_type: ResearchSourceProviderType
    title: str
    tier: str
    tier_score: int
    engagement_score: int
    freshness_score: int
    author_score: int
    composite_score: int
    trend_score: int | None = None
    trend_available: bool
    trend_source: str | None = None
    trend_failure_reason: str | None = None
    confidence_level: ResearchConfidenceLevel
    score_explanation_json: dict[str, object]


class ResearchScoreExplainRequest(BaseModel):
    tier_score: int = Field(ge=0, le=100)
    engagement_score: int = Field(ge=0, le=100)
    freshness_score: int = Field(ge=0, le=100)
    author_score: int = Field(ge=0, le=100)


class ResearchScoreExplanationResponse(BaseModel):
    formula: str
    formula_version: str
    tier_score: int
    engagement_score: int
    freshness_score: int
    author_score: int
    composite_score: int
    confidence_level: ResearchConfidenceLevel
    explanation: str


class ResearchScoreSummaryResponse(BaseModel):
    document_count: int
    tier_score_avg: int
    engagement_score_avg: int
    freshness_score_avg: int
    author_score_avg: int
    composite_score: int
    trend_score: int | None = None
    trend_available: bool
    confidence_level: ResearchConfidenceLevel
    confidence_distribution: dict[str, int]
    tier_distribution: dict[str, int]
    explanation: str


class ResearchScoreRunActionResponse(BaseModel):
    success: bool
    message: str
    score_summary: ResearchScoreSummaryResponse


class ResearchScoreBreakdownResponse(BaseModel):
    id: UUID
    entity_type: ResearchScoreEntityType
    entity_id: UUID
    research_run_id: UUID | None = None
    tier_score_avg: int
    engagement_score_avg: int
    freshness_score_avg: int
    author_score_avg: int
    composite_score: int
    trend_score: int | None = None
    trend_available: bool
    confidence_level: ResearchConfidenceLevel
    formula_version: str
    explanation_json: dict[str, object]
    created_at: datetime
