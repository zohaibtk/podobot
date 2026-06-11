from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.episodes.schemas import (
    EpisodeAssignmentRequest,
    EpisodeCreateRequest,
    EpisodeDraftGenerationRequest,
    EpisodeDraftGenerationResponse,
    EpisodePlanWorkspaceResponse,
    EpisodeReorderRequest,
    EpisodeUpdateRequest,
)
from app.modules.episodes.service import EpisodePlanService
from app.security.auth import require_permission

router = APIRouter(prefix="/series/{series_id}/episodes", tags=["episode planning"])


def get_episode_plan_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EpisodePlanService:
    return EpisodePlanService(session)


EpisodePlanServiceDep = Annotated[EpisodePlanService, Depends(get_episode_plan_service)]
RequireSeriesView = Depends(require_permission("series.view"))
RequireEpisodeCreate = Depends(require_permission("episode.create"))
RequireEpisodeEdit = Depends(require_permission("episode.edit"))
RequireEpisodeLock = Depends(require_permission("episode.lock"))


@router.get("/plan", response_model=EpisodePlanWorkspaceResponse)
async def get_episode_plan(
    series_id: UUID,
    service: EpisodePlanServiceDep,
    _current_user=RequireSeriesView,
):
    return await service.get_plan(series_id)


@router.post("", response_model=EpisodePlanWorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def add_episode(
    series_id: UUID,
    payload: EpisodeCreateRequest,
    service: EpisodePlanServiceDep,
    _current_user=RequireEpisodeCreate,
):
    return await service.add_episode(series_id, payload)


@router.post("/draft", response_model=EpisodeDraftGenerationResponse)
async def generate_episode_draft(
    series_id: UUID,
    payload: EpisodeDraftGenerationRequest,
    service: EpisodePlanServiceDep,
    _current_user=RequireEpisodeEdit,
):
    return await service.generate_episode_draft(series_id, payload)


@router.patch("/{episode_id}", response_model=EpisodePlanWorkspaceResponse)
async def update_episode(
    series_id: UUID,
    episode_id: UUID,
    payload: EpisodeUpdateRequest,
    service: EpisodePlanServiceDep,
    _current_user=RequireEpisodeEdit,
):
    return await service.update_episode(series_id, episode_id, payload)


@router.delete("/{episode_id}", response_model=EpisodePlanWorkspaceResponse)
async def remove_episode(
    series_id: UUID,
    episode_id: UUID,
    service: EpisodePlanServiceDep,
    _current_user=RequireEpisodeEdit,
):
    return await service.remove_episode(series_id, episode_id)


@router.post("/reorder", response_model=EpisodePlanWorkspaceResponse)
async def reorder_episodes(
    series_id: UUID,
    payload: EpisodeReorderRequest,
    service: EpisodePlanServiceDep,
    _current_user=RequireEpisodeEdit,
):
    return await service.reorder_episodes(series_id, payload)


@router.post("/{episode_id}/assign", response_model=EpisodePlanWorkspaceResponse)
async def assign_profiles(
    series_id: UUID,
    episode_id: UUID,
    payload: EpisodeAssignmentRequest,
    service: EpisodePlanServiceDep,
    _current_user=RequireEpisodeEdit,
):
    return await service.assign_profiles(series_id, episode_id, payload)


@router.post("/lock", response_model=EpisodePlanWorkspaceResponse)
async def lock_plan(
    series_id: UUID,
    service: EpisodePlanServiceDep,
    _current_user=RequireEpisodeLock,
):
    return await service.lock_plan(series_id)
