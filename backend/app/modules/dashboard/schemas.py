from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

DashboardRange = Literal["today", "7d", "30d", "90d", "custom"]
DashboardGroupBy = Literal["hour", "day", "week", "month"]


class DashboardMetaResponse(BaseModel):
    generated_at: datetime
    range: DashboardRange
    group_by: DashboardGroupBy
    provider: Literal["real"]
    window_start: datetime
    window_end: datetime


class DashboardKpiResponse(BaseModel):
    key: str
    label: str
    value: float
    display_value: str
    delta: float
    delta_label: str
    trend: Literal["up", "down", "flat"]
    sparkline: list[float]


class PipelineStageResponse(BaseModel):
    stage: str
    count: int
    delta: int
    is_bottleneck: bool


class ConfidencePointResponse(BaseModel):
    label: str
    average_confidence: float
    previous_confidence: float


class SourceDistributionResponse(BaseModel):
    source: str
    documents: int
    percentage: float


class TrendingThemeResponse(BaseModel):
    theme: str
    score: int
    growth: float


class PublishingPerformanceResponse(BaseModel):
    status: str
    count: int
    percentage: float


class ResearchOverviewResponse(BaseModel):
    sources_analyzed: int
    signals_extracted: int
    avg_confidence: float
    top_trend: str


class SeriesVelocityPointResponse(BaseModel):
    label: str
    series: int
    previous_series: int


class EpisodeVelocityPointResponse(BaseModel):
    label: str
    episodes: int
    previous_episodes: int


class PublishingVelocityPointResponse(BaseModel):
    label: str
    scheduled: int
    published: int
    failed: int


class CalendarItemResponse(BaseModel):
    id: str
    title: str
    platform: str
    status: str
    scheduled_for: datetime


class PublishingCalendarDayResponse(BaseModel):
    date: str
    items: list[CalendarItemResponse]


class StrategyOpportunityResponse(BaseModel):
    id: str
    title: str
    confidence: int
    trend: str
    source_count: int
    status: str


class ActionQueueItemResponse(BaseModel):
    id: str
    priority: Literal["high", "medium", "low"]
    type: str
    entity: str
    quick_action: str
    href: str | None = None


class SourceHealthResponse(BaseModel):
    id: str
    source: str
    health: str
    latency_ms: int
    success_rate: float
    documents_collected: int
    last_failure: str | None = None


class RecentResearchRunResponse(BaseModel):
    id: str
    query: str
    run_type: str
    status: str
    sources_used: int
    documents_found: int
    signals_extracted: int
    avg_confidence: float
    duration_ms: int | None = None
    created_at: datetime


class AgentActivityResponse(BaseModel):
    id: str
    agent_name: str
    status: str
    started_at: datetime | None = None
    duration_ms: int | None = None
    related_entity: str
    href: str | None = None


class DashboardAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meta: DashboardMetaResponse
    kpis: list[DashboardKpiResponse]
    pipeline: list[PipelineStageResponse]
    research_confidence: list[ConfidencePointResponse]
    source_distribution: list[SourceDistributionResponse]
    trending_themes: list[TrendingThemeResponse]
    publishing_performance: list[PublishingPerformanceResponse]
    research_overview: ResearchOverviewResponse
    series_velocity: list[SeriesVelocityPointResponse]
    episode_velocity: list[EpisodeVelocityPointResponse]
    publishing_velocity: list[PublishingVelocityPointResponse]
    publishing_calendar: list[PublishingCalendarDayResponse]
    strategy_opportunities: list[StrategyOpportunityResponse]
    action_queue: list[ActionQueueItemResponse]
    source_health: list[SourceHealthResponse]
    recent_research_runs: list[RecentResearchRunResponse]
    agent_activity: list[AgentActivityResponse]
