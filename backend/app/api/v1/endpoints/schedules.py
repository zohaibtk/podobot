from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.schedules.schemas import (
    BulkScheduleRequest,
    ScheduleCreateRequest,
    ScheduleRescheduleRequest,
    ScheduleUpdateRequest,
    ScheduleWorkspaceResponse,
)
from app.modules.schedules.service import ScheduleService
from app.security.auth import require_permission

router = APIRouter(prefix="/series/{series_id}/schedules", tags=["schedules"])


def get_schedule_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ScheduleService:
    return ScheduleService(session)


ScheduleServiceDep = Annotated[ScheduleService, Depends(get_schedule_service)]
RequireSeriesView = Depends(require_permission("series.view"))
RequireScheduleCreate = Depends(require_permission("schedule.create"))
RequireScheduleEdit = Depends(require_permission("schedule.edit"))
RequireScheduleCancel = Depends(require_permission("schedule.cancel"))


@router.get("", response_model=ScheduleWorkspaceResponse)
async def get_schedule_workspace(
    series_id: UUID,
    service: ScheduleServiceDep,
    _current_user=RequireSeriesView,
):
    return await service.get_workspace(series_id)


@router.post("", response_model=ScheduleWorkspaceResponse)
async def create_schedule(
    series_id: UUID,
    payload: ScheduleCreateRequest,
    service: ScheduleServiceDep,
    _current_user=RequireScheduleCreate,
):
    return await service.create_schedule(series_id, payload)


@router.post("/bulk", response_model=ScheduleWorkspaceResponse)
async def bulk_schedule(
    series_id: UUID,
    payload: BulkScheduleRequest,
    service: ScheduleServiceDep,
    _current_user=RequireScheduleCreate,
):
    return await service.bulk_schedule(series_id, payload)


@router.patch("/{schedule_id}", response_model=ScheduleWorkspaceResponse)
async def update_schedule(
    series_id: UUID,
    schedule_id: UUID,
    payload: ScheduleUpdateRequest,
    service: ScheduleServiceDep,
    _current_user=RequireScheduleEdit,
):
    return await service.update_schedule(series_id, schedule_id, payload)


@router.post("/{schedule_id}/reschedule", response_model=ScheduleWorkspaceResponse)
async def reschedule(
    series_id: UUID,
    schedule_id: UUID,
    payload: ScheduleRescheduleRequest,
    service: ScheduleServiceDep,
    _current_user=RequireScheduleEdit,
):
    return await service.reschedule(series_id, schedule_id, payload)


@router.post("/{schedule_id}/cancel", response_model=ScheduleWorkspaceResponse)
async def cancel_schedule(
    series_id: UUID,
    schedule_id: UUID,
    service: ScheduleServiceDep,
    _current_user=RequireScheduleCancel,
):
    return await service.cancel_schedule(series_id, schedule_id)


@router.post("/sync", response_model=ScheduleWorkspaceResponse)
async def sync_statuses(
    series_id: UUID,
    service: ScheduleServiceDep,
    _current_user=RequireScheduleEdit,
):
    return await service.sync_statuses(series_id)
