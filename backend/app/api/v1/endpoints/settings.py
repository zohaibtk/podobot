from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.db.types import WorkspaceUserStatus
from app.modules.settings.schemas import (
    InviteUserRequest,
    PermissionCreateRequest,
    PermissionListResponse,
    PermissionResponse,
    PermissionUpdateRequest,
    RoleCloneRequest,
    RoleCreateRequest,
    RoleMatrixResponse,
    RolePermissionsUpdateRequest,
    RoleResponse,
    RoleUpdateRequest,
    SettingsWorkspaceResponse,
    UserInvitationResponse,
    UserManagementResponse,
    UserRoleAssignRequest,
    UserStatusUpdateRequest,
    WorkspaceUserResponse,
)
from app.modules.settings.service import SettingsService
from app.schemas.pagination import offset_meta
from app.security.auth import require_permission

router = APIRouter(prefix="/settings", tags=["settings"])


def get_settings_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SettingsService:
    return SettingsService(session)


SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]
RequireSettingsManage = Depends(require_permission("settings.manage"))
RequireRoleManage = Depends(require_permission("role.manage"))
RequireUserManage = Depends(require_permission("user.manage"))


@router.get("", response_model=SettingsWorkspaceResponse)
async def get_settings_workspace(
    service: SettingsServiceDep,
    _current_user=RequireSettingsManage,
):
    return await service.get_workspace()


@router.get("/permissions", response_model=PermissionListResponse)
async def list_permissions(
    service: SettingsServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
    search: Annotated[str | None, Query(max_length=240)] = None,
    module: Annotated[str | None, Query(max_length=80)] = None,
    sort: Annotated[str, Query(max_length=40)] = "module",
    _current_user=RequireRoleManage,
):
    try:
        return await service.get_permissions(
            page=page,
            page_size=page_size,
            search=search,
            module=module,
            sort=sort,
        )
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        response = await service.get_permissions()
        items = response.get("items", [])
        return {
            **response,
            **offset_meta(total=len(items), page=page, page_size=page_size),
        }


@router.post(
    "/permissions",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_permission(
    payload: PermissionCreateRequest,
    service: SettingsServiceDep,
    _current_user=RequireRoleManage,
):
    return await service.create_permission(payload)


@router.patch("/permissions/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: UUID,
    payload: PermissionUpdateRequest,
    service: SettingsServiceDep,
    _current_user=RequireRoleManage,
):
    return await service.update_permission(permission_id, payload)


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    permission_id: UUID,
    service: SettingsServiceDep,
    _current_user=RequireRoleManage,
) -> None:
    await service.delete_permission(permission_id)


@router.get("/roles", response_model=RoleMatrixResponse)
async def get_role_matrix(
    service: SettingsServiceDep,
    _current_user=RequireRoleManage,
):
    return await service.get_role_matrix()


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreateRequest,
    service: SettingsServiceDep,
    _current_user=RequireRoleManage,
):
    return await service.create_role(payload)


@router.patch("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    payload: RoleUpdateRequest,
    service: SettingsServiceDep,
    _current_user=RequireRoleManage,
):
    return await service.update_role(role_id, payload)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    service: SettingsServiceDep,
    _current_user=RequireRoleManage,
) -> None:
    await service.delete_role(role_id)


@router.post("/roles/{role_id}/clone", response_model=RoleResponse)
async def clone_role(
    role_id: UUID,
    payload: RoleCloneRequest,
    service: SettingsServiceDep,
    _current_user=RequireRoleManage,
):
    return await service.clone_role(role_id, payload)


@router.put("/roles/{role_id}/permissions", response_model=RoleMatrixResponse)
async def set_role_permissions(
    role_id: UUID,
    payload: RolePermissionsUpdateRequest,
    service: SettingsServiceDep,
    _current_user=RequireRoleManage,
):
    return await service.set_role_permissions(role_id, payload)


@router.post("/roles/{role_id}/permissions/{permission_id}", response_model=RoleMatrixResponse)
async def assign_role_permission(
    role_id: UUID,
    permission_id: UUID,
    service: SettingsServiceDep,
    _current_user=RequireRoleManage,
):
    return await service.assign_role_permission(role_id, permission_id)


@router.delete("/roles/{role_id}/permissions/{permission_id}", response_model=RoleMatrixResponse)
async def remove_role_permission(
    role_id: UUID,
    permission_id: UUID,
    service: SettingsServiceDep,
    _current_user=RequireRoleManage,
):
    return await service.remove_role_permission(role_id, permission_id)


@router.get("/users", response_model=UserManagementResponse)
async def get_user_management(
    service: SettingsServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
    search: Annotated[str | None, Query(max_length=240)] = None,
    status_filter: Annotated[WorkspaceUserStatus | None, Query(alias="status")] = None,
    sort: Annotated[str, Query(max_length=40)] = "email",
    _current_user=RequireUserManage,
):
    try:
        return await service.get_user_management(
            page=page,
            page_size=page_size,
            search=search,
            status_filter=status_filter,
            sort=sort,
        )
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        response = await service.get_user_management()
        items = response.get("users", [])
        return {
            "items": items,
            **response,
            **offset_meta(total=len(items), page=page, page_size=page_size),
        }


@router.post("/users/invitations", response_model=UserInvitationResponse)
async def invite_user(
    payload: InviteUserRequest,
    service: SettingsServiceDep,
    _current_user=RequireUserManage,
):
    return await service.invite_user(payload)


@router.patch("/users/{user_id}/status", response_model=WorkspaceUserResponse)
async def update_user_status(
    user_id: UUID,
    payload: UserStatusUpdateRequest,
    service: SettingsServiceDep,
    _current_user=RequireUserManage,
):
    return await service.update_user_status(user_id, payload)


@router.post("/users/{user_id}/roles", response_model=WorkspaceUserResponse)
async def assign_user_role(
    user_id: UUID,
    payload: UserRoleAssignRequest,
    service: SettingsServiceDep,
    _current_user=RequireUserManage,
):
    return await service.assign_user_role(user_id, payload)


@router.delete("/users/{user_id}/roles/{role_id}", response_model=WorkspaceUserResponse)
async def remove_user_role(
    user_id: UUID,
    role_id: UUID,
    service: SettingsServiceDep,
    _current_user=RequireUserManage,
):
    return await service.remove_user_role(user_id, role_id)
