from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.db.types import SeriesStatus
from app.modules.discovery.schemas import DiscoveryWorkspaceResponse
from app.modules.discovery.service import DiscoveryService
from app.modules.series.schemas import (
    SeriesCreateRequest,
    SeriesListResponse,
    SeriesResponse,
    SeriesUpdateRequest,
)
from app.modules.series.service import SeriesService
from app.schemas.pagination import offset_meta
from app.security.auth import require_permission

router = APIRouter(prefix="/series", tags=["series"])


def get_series_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SeriesService:
    return SeriesService(session)


SeriesServiceDep = Annotated[SeriesService, Depends(get_series_service)]


def get_discovery_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DiscoveryService:
    return DiscoveryService(session)


DiscoveryServiceDep = Annotated[DiscoveryService, Depends(get_discovery_service)]
RequireSeriesCreate = Depends(require_permission("series.create"))
RequireSeriesView = Depends(require_permission("series.view"))
RequireSeriesEdit = Depends(require_permission("series.edit"))
RequireSeriesDelete = Depends(require_permission("series.delete"))
RequireNarrativeGenerate = Depends(require_permission("narrative.generate"))
RequireNarrativeSelect = Depends(require_permission("narrative.select"))


@router.get("", response_model=SeriesListResponse)
async def list_series(
    service: SeriesServiceDep,
    _current_user=RequireSeriesView,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
    search: Annotated[str | None, Query(max_length=240)] = None,
    status_filter: Annotated[SeriesStatus | None, Query(alias="status")] = None,
    sort: Annotated[str, Query(max_length=40)] = "-created_at",
) -> SeriesListResponse:
    try:
        response = await service.list_series(
            page=page,
            page_size=page_size,
            search=search,
            status_filter=status_filter,
            sort=sort,
        )
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        items = await service.list_series()
        response = {
            "items": items,
            **offset_meta(total=len(items), page=page, page_size=page_size),
        }
    return SeriesListResponse(
        **response
    )


@router.post("", response_model=SeriesResponse, status_code=status.HTTP_201_CREATED)
async def create_series(
    payload: SeriesCreateRequest,
    service: SeriesServiceDep,
    _current_user=RequireSeriesCreate,
):
    return await service.create_series(payload)


@router.get("/{series_id}", response_model=SeriesResponse)
async def get_series(
    series_id: UUID,
    service: SeriesServiceDep,
    _current_user=RequireSeriesView,
):
    return await service.get_series(series_id)


@router.get("/{series_id}/discovery", response_model=DiscoveryWorkspaceResponse)
async def get_discovery_workspace(
    series_id: UUID,
    service: DiscoveryServiceDep,
    _current_user=RequireSeriesView,
):
    return await service.get_workspace(series_id)


@router.post("/{series_id}/discovery/run", response_model=DiscoveryWorkspaceResponse)
async def run_discovery(
    series_id: UUID,
    service: DiscoveryServiceDep,
    _current_user=RequireNarrativeGenerate,
):
    return await service.run_discovery(series_id)


@router.post("/{series_id}/narratives/regenerate", response_model=DiscoveryWorkspaceResponse)
async def regenerate_narratives(
    series_id: UUID,
    service: DiscoveryServiceDep,
    _current_user=RequireNarrativeGenerate,
):
    return await service.regenerate_narratives(series_id)


@router.post(
    "/{series_id}/narratives/{narrative_id}/select",
    response_model=DiscoveryWorkspaceResponse,
)
async def select_narrative(
    series_id: UUID,
    narrative_id: UUID,
    service: DiscoveryServiceDep,
    _current_user=RequireNarrativeSelect,
):
    return await service.select_narrative(series_id, narrative_id)


@router.patch("/{series_id}", response_model=SeriesResponse)
async def update_series(
    series_id: UUID,
    payload: SeriesUpdateRequest,
    service: SeriesServiceDep,
    _current_user=RequireSeriesEdit,
):
    return await service.update_series(series_id, payload)


@router.delete("/{series_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_series(
    series_id: UUID,
    service: SeriesServiceDep,
    _current_user=RequireSeriesDelete,
) -> None:
    await service.delete_series(series_id)
