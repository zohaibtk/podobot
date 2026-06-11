from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.captions.schemas import (
    CaptionPlatformCreateRequest,
    CaptionUpdateRequest,
    CaptionWorkspaceResponse,
)
from app.modules.captions.service import CaptionService
from app.security.auth import require_permission

router = APIRouter(prefix="/series/{series_id}/captions", tags=["captions"])


def get_caption_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CaptionService:
    return CaptionService(session)


CaptionServiceDep = Annotated[CaptionService, Depends(get_caption_service)]
RequireSeriesView = Depends(require_permission("series.view"))
RequireCaptionGenerate = Depends(require_permission("caption.generate"))


@router.get("", response_model=CaptionWorkspaceResponse)
async def get_caption_workspace(
    series_id: UUID,
    service: CaptionServiceDep,
    _current_user=RequireSeriesView,
):
    return await service.get_workspace(series_id)


@router.post("/episodes/{episode_id}/platforms", response_model=CaptionWorkspaceResponse)
async def add_caption_platform(
    series_id: UUID,
    episode_id: UUID,
    payload: CaptionPlatformCreateRequest,
    service: CaptionServiceDep,
    _current_user=RequireCaptionGenerate,
):
    return await service.add_platform(series_id, episode_id, payload)


@router.post("/{caption_id}/generate", response_model=CaptionWorkspaceResponse)
async def generate_caption(
    series_id: UUID,
    caption_id: UUID,
    service: CaptionServiceDep,
    _current_user=RequireCaptionGenerate,
):
    return await service.generate_caption(series_id, caption_id)


@router.post("/{caption_id}/regenerate", response_model=CaptionWorkspaceResponse)
async def regenerate_caption(
    series_id: UUID,
    caption_id: UUID,
    service: CaptionServiceDep,
    _current_user=RequireCaptionGenerate,
):
    return await service.regenerate_caption(series_id, caption_id)


@router.patch("/{caption_id}", response_model=CaptionWorkspaceResponse)
async def update_caption(
    series_id: UUID,
    caption_id: UUID,
    payload: CaptionUpdateRequest,
    service: CaptionServiceDep,
    _current_user=RequireCaptionGenerate,
):
    return await service.update_caption(series_id, caption_id, payload)
