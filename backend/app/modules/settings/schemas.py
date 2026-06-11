import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db.types import UserInvitationStatus, WorkspaceUserStatus
from app.schemas.pagination import OffsetPageResponse

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PERMISSION_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
ROLE_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_email(value: str) -> str:
    normalized = value.strip().lower()
    if not EMAIL_PATTERN.match(normalized):
        raise ValueError("A valid email address is required")
    return normalized


class InviteUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: str = Field(min_length=3, max_length=240)
    role_id: UUID
    full_name: str | None = Field(default=None, max_length=180)

    @field_validator("email")
    @classmethod
    def validate_invite_email(cls, value: str) -> str:
        return validate_email(value)


class UserStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: WorkspaceUserStatus


class PermissionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str = Field(min_length=3, max_length=160)
    label: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=2000)

    @field_validator("key")
    @classmethod
    def validate_permission_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not PERMISSION_KEY_PATTERN.match(normalized):
            raise ValueError("Permission key must use module.action format")
        return normalized


class PermissionUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str | None = Field(default=None, min_length=3, max_length=160)
    label: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, min_length=1, max_length=2000)

    @field_validator("key")
    @classmethod
    def validate_permission_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not PERMISSION_KEY_PATTERN.match(normalized):
            raise ValueError("Permission key must use module.action format")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> "PermissionUpdateRequest":
        if not self.model_dump(exclude_none=True):
            raise ValueError("At least one permission field is required")
        return self


class RoleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    is_assignable: bool = True

    @field_validator("key")
    @classmethod
    def validate_role_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not ROLE_KEY_PATTERN.match(normalized):
            raise ValueError("Role key must contain lowercase letters, numbers, or underscores")
        return normalized


class RoleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str | None = Field(default=None, min_length=2, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    is_assignable: bool | None = None

    @field_validator("key")
    @classmethod
    def validate_role_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not ROLE_KEY_PATTERN.match(normalized):
            raise ValueError("Role key must contain lowercase letters, numbers, or underscores")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> "RoleUpdateRequest":
        if not self.model_dump(exclude_none=True):
            raise ValueError("At least one role field is required")
        return self


class RoleCloneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=2000)

    @field_validator("key")
    @classmethod
    def validate_role_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not ROLE_KEY_PATTERN.match(normalized):
            raise ValueError("Role key must contain lowercase letters, numbers, or underscores")
        return normalized


class RolePermissionsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permission_ids: list[UUID]


class UserRoleAssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_id: UUID


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: str = Field(min_length=3, max_length=240)
    password: str = Field(min_length=1, max_length=240)

    @field_validator("email")
    @classmethod
    def validate_login_email(cls, value: str) -> str:
        return validate_email(value)


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    name: str
    description: str
    is_system: bool
    is_assignable: bool
    created_at: datetime
    updated_at: datetime


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    module: str
    action: str
    label: str
    description: str
    is_system: bool = False
    created_at: datetime
    updated_at: datetime | None = None


class PermissionGroupResponse(BaseModel):
    module: str
    permissions: list[PermissionResponse]


class PermissionListResponse(OffsetPageResponse):
    items: list[PermissionResponse]
    groups: list[PermissionGroupResponse]


class RolePermissionCellResponse(BaseModel):
    role_id: UUID
    role_key: str
    role_name: str
    is_allowed: bool


class PermissionMatrixRowResponse(BaseModel):
    permission: PermissionResponse
    role_permissions: list[RolePermissionCellResponse]


class RoleMatrixResponse(BaseModel):
    roles: list[RoleResponse]
    rows: list[PermissionMatrixRowResponse]
    modules: list[str]
    grouped_permissions: list[PermissionGroupResponse] = Field(default_factory=list)
    prototype_notice: str


class WorkspaceUserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None = None
    role: RoleResponse
    roles: list[RoleResponse] = Field(default_factory=list)
    effective_permissions: list[str] = Field(default_factory=list)
    status: WorkspaceUserStatus
    invited_at: datetime | None = None
    last_active_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CurrentUserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    full_name: str | None = None
    status: WorkspaceUserStatus
    roles: list[RoleResponse]
    permissions: list[str]


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    refresh_token_placeholder: str
    user: CurrentUserResponse


class LogoutResponse(BaseModel):
    success: bool


class UserInvitationResponse(BaseModel):
    id: UUID
    email: str
    role: RoleResponse
    status: UserInvitationStatus
    invited_by: str
    created_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class SettingsAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action: str
    actor: str
    redacted_changes: dict[str, object]
    reason: str | None = None
    created_at: datetime


class UserManagementResponse(OffsetPageResponse):
    items: list[WorkspaceUserResponse] = Field(default_factory=list)
    users: list[WorkspaceUserResponse]
    invitations: list[UserInvitationResponse]


class SettingsWorkspaceResponse(BaseModel):
    tab_names: list[str]
    role_matrix: RoleMatrixResponse
    users: list[WorkspaceUserResponse]
    invitations: list[UserInvitationResponse]
    prototype_notice: str
