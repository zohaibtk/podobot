from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.types import AgentRunStatus, StrategyIdeaStatus
from app.modules.series.schemas import SeriesResponse
from app.schemas.pagination import CursorPageResponse


class StrategyRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_date: date
    topic: str
    status: AgentRunStatus
    started_at: datetime
    completed_at: datetime | None = None
    idea_count: int = 0
    created_at: datetime
    updated_at: datetime


class StrategyIdeaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    title: str
    audience: str
    description: str
    proposed_guest_name: str | None = None
    thesis: str
    rationale: str
    evidence_signals: list[dict[str, object]]
    source_proposal: dict[str, object]
    confidence_score: int
    opportunity_score: int
    opportunity_score_breakdown: dict[str, object]
    opportunity_score_explanation: str
    audience_intelligence: dict[str, object]
    lifecycle_stage: str
    season_potential: dict[str, object]
    trend_intelligence: dict[str, object]
    source_count: int
    potential_episode_count: int
    theme_count: int
    generated_at: datetime | None = None
    status: StrategyIdeaStatus
    reviewed_at: datetime | None = None
    dismissed_at: datetime | None = None
    converted_at: datetime | None = None
    converted_series_id: UUID | None = None
    run_date: date
    run_topic: str
    created_at: datetime
    updated_at: datetime


class StrategyIdeaGroupResponse(BaseModel):
    run_id: UUID
    run_date: date
    run_topic: str
    status: StrategyIdeaStatus
    ideas: list[StrategyIdeaResponse]


class StrategyWorkspaceSummaryResponse(BaseModel):
    run_count: int
    proposed_count: int
    in_review_count: int
    dismissed_count: int
    converted_count: int
    new_opportunities_count: int
    high_confidence_count: int
    hot_trends_count: int
    converted_this_month_count: int
    average_opportunity_score: int


class StrategyWorkspaceResponse(BaseModel):
    runs: list[StrategyRunResponse]
    groups: list[StrategyIdeaGroupResponse]
    summary: StrategyWorkspaceSummaryResponse


class StrategyRunListResponse(CursorPageResponse):
    items: list[StrategyRunResponse]


class StrategyIdeaListResponse(CursorPageResponse):
    items: list[StrategyIdeaResponse]


class StrategyIdeaActionResponse(BaseModel):
    workspace: StrategyWorkspaceResponse
    idea: StrategyIdeaResponse
    converted_series: SeriesResponse | None = None
