from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.files.signed_urls import SignedURLService
from app.files.storage import storage
from app.modules.recordings.schemas import SignedMediaURLResponse
from app.modules.recordings.service import RecordingService
from app.security.auth import require_permission

router = APIRouter(prefix="/media", tags=["media"])


def get_recording_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RecordingService:
    return RecordingService(session)


RecordingServiceDep = Annotated[RecordingService, Depends(get_recording_service)]
RequireSeriesView = Depends(require_permission("series.view"))


@router.get("/assets/{asset_id}/signed-url", response_model=SignedMediaURLResponse)
async def create_signed_media_url(
    asset_id: UUID,
    service: RecordingServiceDep,
    _current_user=RequireSeriesView,
):
    return await service.get_signed_media_url(asset_id)


@router.get("/signed/{token}")
async def read_signed_media(token: str):
    storage_key = SignedURLService().verify(token)
    try:
        path = storage.resolve(storage_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found",
        ) from exc
    if not path.exists() or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found",
        )
    return FileResponse(path)
