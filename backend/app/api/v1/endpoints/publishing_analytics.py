from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.db.types import CaptionVideoKind, Platform
from app.modules.publishing_analytics.schemas import (
    ChannelPerformanceListResponse,
    ContentPerformanceListResponse,
    PublishingAnalyticsAuditLogListResponse,
    PublishingAnalyticsWorkspaceResponse,
)
from app.modules.publishing_analytics.service import (
    AnalyticsFilters,
    PublishingAnalyticsService,
)
from app.schemas.pagination import OffsetParams, offset_meta
from app.security.auth import require_permission

router = APIRouter(prefix="/publishing-analytics", tags=["publishing analytics"])


def get_publishing_analytics_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PublishingAnalyticsService:
    return PublishingAnalyticsService(session)


PublishingAnalyticsServiceDep = Annotated[
    PublishingAnalyticsService,
    Depends(get_publishing_analytics_service),
]
RequireSeriesView = Depends(require_permission("series.view"))


def analytics_filters(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    platforms: Annotated[list[Platform] | None, Query(alias="platform")] = None,
    video_kinds: Annotated[list[CaptionVideoKind] | None, Query(alias="video_kind")] = None,
) -> AnalyticsFilters:
    return AnalyticsFilters(
        date_from=date_from,
        date_to=date_to,
        platforms=platforms,
        video_kinds=video_kinds,
    )


AnalyticsFiltersDep = Annotated[AnalyticsFilters, Depends(analytics_filters)]


@router.get("/workspace", response_model=PublishingAnalyticsWorkspaceResponse)
async def get_publishing_analytics_workspace(
    service: PublishingAnalyticsServiceDep,
    filters: AnalyticsFiltersDep,
    _current_user=RequireSeriesView,
):
    return await service.workspace(filters)


@router.get("/channels", response_model=ChannelPerformanceListResponse)
async def get_channel_performance(
    service: PublishingAnalyticsServiceDep,
    filters: AnalyticsFiltersDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
    _current_user=RequireSeriesView,
):
    items = await service.channels(filters)
    return paged_items(items, page=page, page_size=page_size)


@router.get("/content", response_model=ContentPerformanceListResponse)
async def get_content_performance(
    service: PublishingAnalyticsServiceDep,
    filters: AnalyticsFiltersDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
    _current_user=RequireSeriesView,
):
    items = await service.content(filters)
    return paged_items(items, page=page, page_size=page_size)


@router.get("/executive-report")
async def get_executive_report(
    service: PublishingAnalyticsServiceDep,
    filters: AnalyticsFiltersDep,
    _current_user=RequireSeriesView,
):
    return await service.executive_report(filters)


@router.get("/audit-events", response_model=PublishingAnalyticsAuditLogListResponse)
async def get_publishing_analytics_audit_events(
    service: PublishingAnalyticsServiceDep,
    filters: AnalyticsFiltersDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
    _current_user=RequireSeriesView,
):
    return await service.audit_events_page(filters=filters, page=page, page_size=page_size)


def paged_items(items: list[object], *, page: int, page_size: int) -> dict[str, object]:
    pagination = OffsetParams(page=page, page_size=page_size)
    return {
        "items": items[pagination.offset : pagination.offset + pagination.page_size],
        **offset_meta(total=len(items), page=page, page_size=page_size),
    }
