from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.db.types import ResearchSourceCategory, ResearchSourceStatus
from app.modules.research_sources.schemas import (
    ResearchSourceListResponse,
    ResearchSourceResponse,
    ResearchSourceTestResponse,
    ResearchSourceUpdateRequest,
)
from app.modules.research_sources.service import ResearchSourceService
from app.security.auth import require_permission

router = APIRouter(prefix="/research/sources", tags=["research sources"])


def get_research_source_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResearchSourceService:
    return ResearchSourceService(session)


ResearchSourceServiceDep = Annotated[
    ResearchSourceService,
    Depends(get_research_source_service),
]
RequireIntegrationManage = Depends(require_permission("integration.manage"))


@router.get("", response_model=ResearchSourceListResponse)
async def list_research_sources(
    service: ResearchSourceServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
    category: ResearchSourceCategory | None = None,
    status_filter: Annotated[ResearchSourceStatus | None, Query(alias="status")] = None,
    enabled: bool | None = None,
    search: Annotated[str | None, Query(max_length=240)] = None,
    sort: Annotated[str, Query(max_length=40)] = "priority",
) -> ResearchSourceListResponse:
    return ResearchSourceListResponse(
        **(
            await service.list_sources(
                page=page,
                page_size=page_size,
                category=category,
                status_filter=status_filter,
                enabled=enabled,
                search=search,
                sort=sort,
            )
        )
    )


@router.get("/{source_id}", response_model=ResearchSourceResponse)
async def get_research_source(
    source_id: UUID,
    service: ResearchSourceServiceDep,
) -> ResearchSourceResponse:
    return ResearchSourceResponse(**(await service.get_source(source_id)))


@router.patch("/{source_id}", response_model=ResearchSourceResponse)
async def update_research_source(
    source_id: UUID,
    payload: ResearchSourceUpdateRequest,
    service: ResearchSourceServiceDep,
    _current_user=RequireIntegrationManage,
) -> ResearchSourceResponse:
    return ResearchSourceResponse(**(await service.update_source(source_id, payload)))


@router.post("/{source_id}/enable", response_model=ResearchSourceResponse)
async def enable_research_source(
    source_id: UUID,
    service: ResearchSourceServiceDep,
    _current_user=RequireIntegrationManage,
) -> ResearchSourceResponse:
    return ResearchSourceResponse(**(await service.enable_source(source_id)))


@router.post("/{source_id}/disable", response_model=ResearchSourceResponse)
async def disable_research_source(
    source_id: UUID,
    service: ResearchSourceServiceDep,
    _current_user=RequireIntegrationManage,
) -> ResearchSourceResponse:
    return ResearchSourceResponse(**(await service.disable_source(source_id)))


@router.post("/{source_id}/test", response_model=ResearchSourceTestResponse)
async def test_research_source(
    source_id: UUID,
    service: ResearchSourceServiceDep,
    _current_user=RequireIntegrationManage,
) -> ResearchSourceTestResponse:
    return ResearchSourceTestResponse(**(await service.test_source(source_id)))
