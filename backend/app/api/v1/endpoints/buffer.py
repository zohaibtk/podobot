from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.db.types import Platform
from app.modules.schedules.buffer_service import BufferPublishingService
from app.modules.schedules.schemas import (
    BufferChannelMappingRequest,
    BufferOAuthCallbackResponse,
    BufferOAuthStartResponse,
    BufferWebhookResponse,
    BufferWorkspaceResponse,
)
from app.security.auth import require_permission

router = APIRouter(prefix="/buffer", tags=["buffer"])


def get_buffer_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BufferPublishingService:
    return BufferPublishingService(session)


BufferServiceDep = Annotated[BufferPublishingService, Depends(get_buffer_service)]
RequireIntegrationManage = Depends(require_permission("integration.manage"))
RequireScheduleEdit = Depends(require_permission("schedule.edit"))


@router.get("/workspace", response_model=BufferWorkspaceResponse)
async def get_buffer_workspace(
    service: BufferServiceDep,
    _current_user=RequireScheduleEdit,
):
    return await service.workspace()


@router.post("/oauth/start", response_model=BufferOAuthStartResponse)
async def start_buffer_oauth(
    service: BufferServiceDep,
    _current_user=RequireIntegrationManage,
):
    return await service.start_oauth()


@router.get("/oauth/callback", response_model=BufferOAuthCallbackResponse)
async def complete_buffer_oauth(
    service: BufferServiceDep,
    code: Annotated[str, Query(min_length=1)],
    state: Annotated[str, Query(min_length=1)],
):
    return await service.complete_oauth(code=code, state=state)


@router.post("/channels/sync", response_model=BufferWorkspaceResponse)
async def sync_buffer_channels(
    service: BufferServiceDep,
    _current_user=RequireIntegrationManage,
):
    return await service.sync_channels()


@router.patch("/channel-mappings/{platform}", response_model=BufferWorkspaceResponse)
async def update_buffer_channel_mapping(
    platform: Platform,
    payload: BufferChannelMappingRequest,
    service: BufferServiceDep,
    _current_user=RequireIntegrationManage,
):
    return await service.map_channel(platform, payload.channel_id)


@router.post("/webhooks", response_model=BufferWebhookResponse)
async def receive_buffer_webhook(
    request: Request,
    service: BufferServiceDep,
    x_buffer_signature: Annotated[str | None, Header(alias="X-Buffer-Signature")] = None,
):
    raw_body = await request.body()
    payload = await request.json()
    return await service.handle_webhook(
        payload,
        signature=x_buffer_signature,
        raw_body=raw_body,
    )
