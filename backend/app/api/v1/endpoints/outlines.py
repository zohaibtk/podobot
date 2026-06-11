from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.outlines.schemas import (
    OutlineRegenerateRequest,
    OutlineUpdateRequest,
    OutlineVersionListResponse,
    OutlineWorkspaceResponse,
)
from app.modules.outlines.service import OutlineService
from app.security.auth import require_permission

router = APIRouter(prefix="/series/{series_id}/outlines", tags=["outlines"])


def get_outline_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OutlineService:
    return OutlineService(session)


OutlineServiceDep = Annotated[OutlineService, Depends(get_outline_service)]
RequireSeriesView = Depends(require_permission("series.view"))
RequireOutlineGenerate = Depends(require_permission("outline.generate"))
RequireOutlineEdit = Depends(require_permission("outline.edit"))


@router.get("", response_model=OutlineWorkspaceResponse)
async def get_outline_workspace(
    series_id: UUID,
    service: OutlineServiceDep,
    _current_user=RequireSeriesView,
):
    return await service.get_workspace(series_id)


@router.patch("/{outline_id}", response_model=OutlineWorkspaceResponse)
async def update_outline(
    series_id: UUID,
    outline_id: UUID,
    payload: OutlineUpdateRequest,
    service: OutlineServiceDep,
    _current_user=RequireOutlineEdit,
):
    return await service.update_outline(series_id, outline_id, payload)


@router.post("/{outline_id}/regenerate", response_model=OutlineWorkspaceResponse)
async def regenerate_outline(
    series_id: UUID,
    outline_id: UUID,
    service: OutlineServiceDep,
    payload: OutlineRegenerateRequest | None = None,
    _current_user=RequireOutlineGenerate,
):
    return await service.regenerate_outline(series_id, outline_id, payload)


@router.post("/{outline_id}/approve", response_model=OutlineWorkspaceResponse)
async def approve_outline(
    series_id: UUID,
    outline_id: UUID,
    service: OutlineServiceDep,
    _current_user=RequireOutlineEdit,
):
    return await service.approve_outline(series_id, outline_id)


@router.get("/{outline_id}/versions", response_model=OutlineVersionListResponse)
async def list_outline_versions(
    series_id: UUID,
    outline_id: UUID,
    service: OutlineServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
    _current_user=RequireSeriesView,
):
    return await service.list_versions(
        series_id,
        outline_id,
        page=page,
        page_size=page_size,
    )
