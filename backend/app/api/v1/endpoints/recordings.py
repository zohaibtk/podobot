from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.recordings.schemas import RecordingWorkspaceResponse
from app.modules.recordings.service import RecordingService
from app.security.auth import require_permission

router = APIRouter(prefix="/series/{series_id}/recordings", tags=["recordings"])


def get_recording_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RecordingService:
    return RecordingService(session)


RecordingServiceDep = Annotated[RecordingService, Depends(get_recording_service)]
UploadFileDep = Annotated[UploadFile, File()]
RequireSeriesView = Depends(require_permission("series.view"))
RequireRecordingUpload = Depends(require_permission("recording.upload"))


@router.get("", response_model=RecordingWorkspaceResponse)
async def get_recording_workspace(
    series_id: UUID,
    service: RecordingServiceDep,
    _current_user=RequireSeriesView,
):
    return await service.get_workspace(series_id)


@router.post("/episodes/{episode_id}/video", response_model=RecordingWorkspaceResponse)
async def upload_episode_video(
    series_id: UUID,
    episode_id: UUID,
    service: RecordingServiceDep,
    file: UploadFileDep,
    _current_user=RequireRecordingUpload,
):
    return await service.upload_video(series_id, episode_id, file)


@router.post("/episodes/{episode_id}/transcript", response_model=RecordingWorkspaceResponse)
async def upload_episode_transcript(
    series_id: UUID,
    episode_id: UUID,
    service: RecordingServiceDep,
    file: UploadFileDep,
    _current_user=RequireRecordingUpload,
):
    return await service.upload_transcript(series_id, episode_id, file)


@router.post("/episodes/{episode_id}/thumbnails", response_model=RecordingWorkspaceResponse)
async def upload_episode_thumbnail(
    series_id: UUID,
    episode_id: UUID,
    service: RecordingServiceDep,
    file: UploadFileDep,
    _current_user=RequireRecordingUpload,
):
    return await service.upload_thumbnail(series_id, episode_id, file)


@router.post(
    "/episodes/{episode_id}/thumbnails/{thumbnail_id}/select",
    response_model=RecordingWorkspaceResponse,
)
async def select_episode_thumbnail(
    series_id: UUID,
    episode_id: UUID,
    thumbnail_id: UUID,
    service: RecordingServiceDep,
    _current_user=RequireRecordingUpload,
):
    return await service.select_thumbnail(series_id, episode_id, thumbnail_id)


@router.delete(
    "/episodes/{episode_id}/thumbnails/{thumbnail_id}",
    response_model=RecordingWorkspaceResponse,
)
async def delete_episode_thumbnail(
    series_id: UUID,
    episode_id: UUID,
    thumbnail_id: UUID,
    service: RecordingServiceDep,
    _current_user=RequireRecordingUpload,
):
    return await service.delete_thumbnail(series_id, episode_id, thumbnail_id)


@router.post(
    "/episodes/{episode_id}/clip-suggestions",
    response_model=RecordingWorkspaceResponse,
)
async def request_clip_suggestions(
    series_id: UUID,
    episode_id: UUID,
    service: RecordingServiceDep,
    _current_user=RequireRecordingUpload,
):
    return await service.request_clip_suggestions(series_id, episode_id)


@router.post(
    "/episodes/{episode_id}/clip-suggestions/{clip_suggestion_id}/video",
    response_model=RecordingWorkspaceResponse,
)
async def upload_clip_suggestion_video(
    series_id: UUID,
    episode_id: UUID,
    clip_suggestion_id: UUID,
    service: RecordingServiceDep,
    file: UploadFileDep,
    _current_user=RequireRecordingUpload,
):
    return await service.upload_clip_suggestion_video(
        series_id,
        episode_id,
        clip_suggestion_id,
        file,
    )


@router.post("/episodes/{episode_id}/lock", response_model=RecordingWorkspaceResponse)
async def lock_episode_recording(
    series_id: UUID,
    episode_id: UUID,
    service: RecordingServiceDep,
    _current_user=RequireRecordingUpload,
):
    return await service.lock_recording(series_id, episode_id)
