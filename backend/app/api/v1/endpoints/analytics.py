from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.dashboard.schemas import (
    AgentActivityResponse,
    DashboardAnalyticsResponse,
    PipelineStageResponse,
    RecentResearchRunResponse,
    SourceHealthResponse,
)
from app.modules.dashboard.service import DashboardAnalyticsService
from app.security.auth import require_permission

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_dashboard_analytics_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DashboardAnalyticsService:
    return DashboardAnalyticsService(session)


DashboardAnalyticsServiceDep = Annotated[
    DashboardAnalyticsService,
    Depends(get_dashboard_analytics_service),
]
RequireDashboardView = Depends(require_permission("dashboard.view"))


def analytics_range(
    range_value: Annotated[str, Query(alias="range")] = "30d",
    group_by: Annotated[str | None, Query()] = None,
    start_date: Annotated[str | None, Query()] = None,
    end_date: Annotated[str | None, Query()] = None,
) -> tuple[str, str | None, str | None, str | None]:
    return range_value, group_by, start_date, end_date


AnalyticsRangeDep = Annotated[
    tuple[str, str | None, str | None, str | None],
    Depends(analytics_range),
]


@router.get("/dashboard", response_model=DashboardAnalyticsResponse)
async def get_dashboard_analytics(
    service: DashboardAnalyticsServiceDep,
    params: AnalyticsRangeDep,
    _current_user=RequireDashboardView,
) -> DashboardAnalyticsResponse:
    range_value, group_by, start_date, end_date = params
    return DashboardAnalyticsResponse(
        **await service.dashboard(range_value, group_by, start_date, end_date)
    )


@router.get("/pipeline", response_model=list[PipelineStageResponse])
async def get_pipeline_analytics(
    service: DashboardAnalyticsServiceDep,
    params: AnalyticsRangeDep,
    _current_user=RequireDashboardView,
) -> list[PipelineStageResponse]:
    range_value, group_by, start_date, end_date = params
    return [
        PipelineStageResponse(**item)
        for item in await service.pipeline(range_value, group_by, start_date, end_date)
    ]


@router.get("/research-confidence")
async def get_research_confidence_analytics(
    service: DashboardAnalyticsServiceDep,
    params: AnalyticsRangeDep,
    _current_user=RequireDashboardView,
):
    range_value, group_by, start_date, end_date = params
    return await service.research_confidence(range_value, group_by, start_date, end_date)


@router.get("/source-distribution")
async def get_source_distribution_analytics(
    service: DashboardAnalyticsServiceDep,
    params: AnalyticsRangeDep,
    _current_user=RequireDashboardView,
):
    range_value, group_by, start_date, end_date = params
    return await service.source_distribution(range_value, group_by, start_date, end_date)


@router.get("/trending-themes")
async def get_trending_themes_analytics(
    service: DashboardAnalyticsServiceDep,
    params: AnalyticsRangeDep,
    _current_user=RequireDashboardView,
):
    range_value, group_by, start_date, end_date = params
    return await service.trending_themes(range_value, group_by, start_date, end_date)


@router.get("/publishing")
async def get_publishing_analytics(
    service: DashboardAnalyticsServiceDep,
    params: AnalyticsRangeDep,
    _current_user=RequireDashboardView,
):
    range_value, group_by, start_date, end_date = params
    return await service.publishing(range_value, group_by, start_date, end_date)


@router.get("/strategy")
async def get_strategy_analytics(
    service: DashboardAnalyticsServiceDep,
    params: AnalyticsRangeDep,
    _current_user=RequireDashboardView,
):
    range_value, group_by, start_date, end_date = params
    return await service.strategy(range_value, group_by, start_date, end_date)


@router.get("/source-health", response_model=list[SourceHealthResponse])
async def get_source_health_analytics(
    service: DashboardAnalyticsServiceDep,
    params: AnalyticsRangeDep,
    _current_user=RequireDashboardView,
) -> list[SourceHealthResponse]:
    range_value, group_by, start_date, end_date = params
    return [
        SourceHealthResponse(**item)
        for item in await service.source_health(range_value, group_by, start_date, end_date)
    ]


@router.get("/recent-research-runs", response_model=list[RecentResearchRunResponse])
async def get_recent_research_runs_analytics(
    service: DashboardAnalyticsServiceDep,
    params: AnalyticsRangeDep,
    _current_user=RequireDashboardView,
) -> list[RecentResearchRunResponse]:
    range_value, group_by, start_date, end_date = params
    return [
        RecentResearchRunResponse(**item)
        for item in await service.recent_research_runs(
            range_value,
            group_by,
            start_date,
            end_date,
        )
    ]


@router.get("/agent-activity", response_model=list[AgentActivityResponse])
async def get_agent_activity_analytics(
    service: DashboardAnalyticsServiceDep,
    params: AnalyticsRangeDep,
    _current_user=RequireDashboardView,
) -> list[AgentActivityResponse]:
    range_value, group_by, start_date, end_date = params
    return [
        AgentActivityResponse(**item)
        for item in await service.agent_activity(range_value, group_by, start_date, end_date)
    ]
