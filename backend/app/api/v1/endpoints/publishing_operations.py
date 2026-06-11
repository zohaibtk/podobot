from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.db.types import Platform, ScheduleStatus
from app.modules.publishing_operations.schemas import (
    PublishingAnalyticsResponse,
    PublishingAuditLogListResponse,
    PublishingBulkActionRequest,
    PublishingBulkActionResponse,
    PublishingOperationsWorkspaceResponse,
    PublishingQueueResponse,
    PublishingTimelineResponse,
)
from app.modules.publishing_operations.service import PublishingOperationsService
from app.schemas.pagination import cursor_meta, offset_meta
from app.security.auth import require_permission

router = APIRouter(prefix="/publishing", tags=["publishing"])


def get_publishing_operations_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PublishingOperationsService:
    return PublishingOperationsService(session)


PublishingOperationsServiceDep = Annotated[
    PublishingOperationsService,
    Depends(get_publishing_operations_service),
]
RequireSeriesView = Depends(require_permission("series.view"))
RequireScheduleEdit = Depends(require_permission("schedule.edit"))
RequireScheduleCancel = Depends(require_permission("schedule.cancel"))


@router.get("/workspace", response_model=PublishingOperationsWorkspaceResponse)
async def get_publishing_operations_workspace(
    service: PublishingOperationsServiceDep,
    _current_user=RequireSeriesView,
):
    return await service.workspace()


@router.get("/analytics", response_model=PublishingAnalyticsResponse)
async def get_publishing_analytics(
    service: PublishingOperationsServiceDep,
    _current_user=RequireSeriesView,
):
    return await service.analytics()


@router.get("/queue", response_model=PublishingQueueResponse)
async def get_publishing_queue(
    service: PublishingOperationsServiceDep,
    statuses: Annotated[list[ScheduleStatus] | None, Query(alias="status")] = None,
    platforms: Annotated[list[Platform] | None, Query(alias="platform")] = None,
    query: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1, le=200)] = None,
    _current_user=RequireSeriesView,
):
    effective_page_size = page_size or limit
    try:
        return await service.queue_items(
            statuses=statuses,
            platforms=platforms,
            query=query,
            limit=limit,
            page=page,
            page_size=page_size,
        )
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        response = await service.queue_items(
            statuses=statuses,
            platforms=platforms,
            query=query,
            limit=effective_page_size,
        )
        total = int(response.get("total_count", len(response.get("items", []))))
        return {
            **response,
            **offset_meta(total=total, page=page, page_size=effective_page_size),
        }


@router.get("/timeline", response_model=PublishingTimelineResponse)
async def get_publishing_timeline(
    service: PublishingOperationsServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
    _current_user=RequireSeriesView,
):
    if not hasattr(service, "timeline_page"):
        items = await service.timeline(limit=limit)
        return PublishingTimelineResponse(
            items=items,
            **cursor_meta(page_size=limit, has_next=False, next_cursor=None),
        )
    return PublishingTimelineResponse(
        **await service.timeline_page(limit=limit, cursor=cursor)
    )


@router.get("/audits", response_model=PublishingAuditLogListResponse)
async def get_publishing_audits(
    service: PublishingOperationsServiceDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
    _current_user=RequireSeriesView,
):
    if not hasattr(service, "audit_logs_page"):
        items = await service.audit_logs(limit=limit)
        return PublishingAuditLogListResponse(
            items=items,
            **cursor_meta(page_size=limit, has_next=False, next_cursor=None),
        )
    return PublishingAuditLogListResponse(
        **await service.audit_logs_page(limit=limit, cursor=cursor)
    )


@router.post("/bulk/retry", response_model=PublishingBulkActionResponse)
async def retry_publishing_rows(
    payload: PublishingBulkActionRequest,
    service: PublishingOperationsServiceDep,
    _current_user=RequireScheduleEdit,
):
    return await service.retry_bulk(payload)


@router.post("/bulk/sync", response_model=PublishingBulkActionResponse)
async def sync_publishing_rows(
    payload: PublishingBulkActionRequest,
    service: PublishingOperationsServiceDep,
    _current_user=RequireScheduleEdit,
):
    return await service.sync_bulk(payload)


@router.post("/bulk/stop", response_model=PublishingBulkActionResponse)
async def stop_publishing_rows(
    payload: PublishingBulkActionRequest,
    service: PublishingOperationsServiceDep,
    _current_user=RequireScheduleCancel,
):
    return await service.stop_bulk(payload)
