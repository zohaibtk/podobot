from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.briefs.schemas import BriefUpdateRequest, BriefWorkspaceResponse
from app.modules.briefs.service import BriefService
from app.security.auth import require_permission

router = APIRouter(prefix="/series/{series_id}/briefs", tags=["briefs"])


def get_brief_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BriefService:
    return BriefService(session)


BriefServiceDep = Annotated[BriefService, Depends(get_brief_service)]
RequireSeriesView = Depends(require_permission("series.view"))
RequireBriefGenerate = Depends(require_permission("brief.generate"))
RequireBriefApprove = Depends(require_permission("brief.approve"))


@router.get("", response_model=BriefWorkspaceResponse)
async def get_brief_workspace(
    series_id: UUID,
    service: BriefServiceDep,
    _current_user=RequireSeriesView,
):
    return await service.get_workspace(series_id)


@router.post("/episodes/{episode_id}/generate", response_model=BriefWorkspaceResponse)
async def generate_brief_pair(
    series_id: UUID,
    episode_id: UUID,
    service: BriefServiceDep,
    _current_user=RequireBriefGenerate,
):
    return await service.generate_pair(series_id, episode_id)


@router.post("/episodes/{episode_id}/approve", response_model=BriefWorkspaceResponse)
async def approve_brief_pair(
    series_id: UUID,
    episode_id: UUID,
    service: BriefServiceDep,
    _current_user=RequireBriefApprove,
):
    return await service.approve_pair(series_id, episode_id)


@router.patch("/{brief_id}", response_model=BriefWorkspaceResponse)
async def update_brief(
    series_id: UUID,
    brief_id: UUID,
    payload: BriefUpdateRequest,
    service: BriefServiceDep,
    _current_user=RequireBriefGenerate,
):
    return await service.update_brief(series_id, brief_id, payload)


@router.post("/{brief_id}/regenerate", response_model=BriefWorkspaceResponse)
async def regenerate_brief(
    series_id: UUID,
    brief_id: UUID,
    service: BriefServiceDep,
    _current_user=RequireBriefGenerate,
):
    return await service.regenerate_brief(series_id, brief_id)


@router.get("/{brief_id}/download")
async def download_brief(
    series_id: UUID,
    brief_id: UUID,
    service: BriefServiceDep,
    _current_user=RequireSeriesView,
):
    filename, content = await service.download_brief(series_id, brief_id)
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
