from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.types import DiscoverySourceStatus, NarrativeStatus, ResearchConfidenceLevel
from app.modules.series.schemas import SeriesResponse


class DiscoveryLedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    series_id: UUID
    source_name: str
    source_type: str
    source_url: str
    status: DiscoverySourceStatus
    signal_title: str
    signal_summary: str
    confidence_score: int
    tier: str | None = None
    tier_score: int | None = None
    engagement_score: int | None = None
    freshness_score: int | None = None
    author_score: int | None = None
    composite_score: int | None = None
    confidence_level: ResearchConfidenceLevel | None = None
    trend_score: int | None = None
    trend_available: bool | None = None
    score_explanation_json: dict[str, object] = Field(default_factory=dict)
    sort_order: int
    created_at: datetime
    updated_at: datetime


class SupportingSignalResponse(BaseModel):
    source_name: str
    signal_title: str
    confidence_score: int


class NarrativeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    series_id: UUID
    title: str
    thesis: str
    summary: str
    confidence_score: int
    supporting_signals: list[SupportingSignalResponse]
    generation: int
    status: NarrativeStatus
    is_selected: bool
    selected_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DiscoveryWorkspaceResponse(BaseModel):
    series: SeriesResponse
    progress_percent: int
    ledger: list[DiscoveryLedgerEntryResponse]
    narratives: list[NarrativeResponse]
    selected_narrative_id: UUID | None
    research_activity: dict[str, object] = Field(default_factory=dict)
