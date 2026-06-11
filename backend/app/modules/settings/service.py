import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.types import UserInvitationStatus, WorkspaceUserStatus
from app.modules.settings.models import (
    Permission,
    Role,
    RolePermission,
    SettingsAuditLog,
    UserInvitation,
    UserRole,
    WorkspaceUser,
)
from app.modules.settings.schemas import (
    InviteUserRequest,
    PermissionCreateRequest,
    PermissionUpdateRequest,
    RoleCloneRequest,
    RoleCreateRequest,
    RolePermissionsUpdateRequest,
    RoleUpdateRequest,
    UserRoleAssignRequest,
    UserStatusUpdateRequest,
)
from app.schemas.pagination import OffsetParams, offset_meta
from app.security.passwords import hash_password_async, verify_password_async

SETTINGS_TAB_NAMES = ["Role management", "User management"]
PROTOTYPE_NOTICE = (
    "Prototype RBAC enforcement is active for protected API routes. "
    "Custom roles and permissions are auditable, while production identity federation "
    "and refresh-token rotation remain deferred."
)


@dataclass(frozen=True)
class RoleDefault:
    key: str
    name: str
    description: str


@dataclass(frozen=True)
class PermissionDefault:
    key: str
    label: str
    description: str

    @property
    def module(self) -> str:
        return self.key.split(".", 1)[0]

    @property
    def action(self) -> str:
        return self.key.split(".", 1)[1]


@dataclass(frozen=True)
class DefaultWorkspaceUser:
    email: str
    full_name: str
    role_key: str
    password: str | None = None


ROLE_DEFAULTS = [
    RoleDefault(
        key="admin",
        name="Admin",
        description="Workspace administrator with full permissions.",
    ),
    RoleDefault(
        key="producer",
        name="Producer",
        description="Editorial operator role with broad production permissions.",
    ),
    RoleDefault(
        key="viewer",
        name="Viewer",
        description="Read-oriented collaborator for review and visibility.",
    ),
]

PERMISSION_DEFAULTS = [
    PermissionDefault("dashboard.view", "View dashboard", "Open the dashboard."),
    PermissionDefault("series.create", "Create series", "Create new series."),
    PermissionDefault("series.view", "View series", "Open series workspaces."),
    PermissionDefault("series.edit", "Edit series", "Edit series metadata."),
    PermissionDefault("series.delete", "Delete series", "Archive or remove series."),
    PermissionDefault("narrative.generate", "Generate narratives", "Generate narrative options."),
    PermissionDefault("narrative.select", "Select narrative", "Choose the production narrative."),
    PermissionDefault("episode.create", "Create episodes", "Add episodes to a plan."),
    PermissionDefault("episode.edit", "Edit episodes", "Edit and reorder planned episodes."),
    PermissionDefault("episode.lock", "Lock episode plan", "Approve the episode plan."),
    PermissionDefault("outline.generate", "Generate outlines", "Generate episode outlines."),
    PermissionDefault("outline.edit", "Edit outlines", "Edit outline versions."),
    PermissionDefault("brief.generate", "Generate briefs", "Generate and regenerate briefs."),
    PermissionDefault("brief.approve", "Approve briefs", "Approve host and guest brief pairs."),
    PermissionDefault("recording.upload", "Upload recordings", "Upload media and transcripts."),
    PermissionDefault("caption.generate", "Generate captions", "Generate platform captions."),
    PermissionDefault("schedule.create", "Create schedules", "Schedule captioned posts."),
    PermissionDefault("schedule.edit", "Edit schedules", "Edit and reschedule posts."),
    PermissionDefault("schedule.cancel", "Cancel schedules", "Cancel scheduled posts."),
    PermissionDefault("strategy.view", "View strategy", "Open strategy research ideas."),
    PermissionDefault(
        "strategy.convert",
        "Convert strategy ideas",
        "Convert ideas to draft series.",
    ),
    PermissionDefault(
        "integration.manage",
        "Manage source integrations",
        "Configure discovery sources and provider keys.",
    ),
    PermissionDefault("settings.manage", "Manage settings", "Update workspace settings."),
    PermissionDefault("user.manage", "Manage users", "Invite and manage users."),
    PermissionDefault("role.manage", "Manage roles", "Create and assign roles and permissions."),
    PermissionDefault("research.view", "View research", "Inspect research runs and evidence."),
    PermissionDefault(
        "research.manage",
        "Manage research",
        "Retry runs, archive documents, and clear failed research activity.",
    ),
]

DEFAULT_PERMISSION_KEYS = {permission.key for permission in PERMISSION_DEFAULTS}
LEGACY_PERMISSION_KEYS = {
    "briefs.approve",
    "briefs.edit",
    "briefs.view",
    "captions.edit",
    "captions.generate",
    "captions.view",
    "command_center.view",
    "discovery.run",
    "discovery.select_narrative",
    "discovery.view",
    "episode_plan.edit",
    "episode_plan.lock",
    "episode_plan.view",
    "integrations.manage",
    "integrations.view",
    "outlines.approve",
    "outlines.edit",
    "outlines.view",
    "profiles.manage",
    "profiles.view",
    "publishing.recover",
    "publishing.schedule",
    "publishing.view",
    "recordings.lock",
    "recordings.upload",
    "recordings.view",
    "settings.edit_workspace",
    "settings.manage_roles",
    "settings.manage_users",
    "settings.view_workspace",
    "strategy.run_research",
}
PRODUCER_DENIED = {"integration.manage", "settings.manage", "user.manage", "role.manage"}
DEFAULTS_LOCK = asyncio.Lock()
ADMIN_EMAIL = "admin@podobot.com"
DEFAULT_WORKSPACE_USERS = [
    DefaultWorkspaceUser(
        email=ADMIN_EMAIL,
        full_name="PodoBot Admin",
        role_key="admin",
    ),
    DefaultWorkspaceUser(
        email="producer@podobot.com",
        full_name="PodoBot Producer",
        role_key="producer",
        password="producer",
    ),
    DefaultWorkspaceUser(
        email="viewer@podobot.com",
        full_name="PodoBot Viewer",
        role_key="viewer",
        password="viewer",
    ),
]
LEGACY_DEMO_USER_EMAILS = (
    "admin@podobot.local",
    "producer@podobot.local",
    "reviewer@podobot.local",
    "viewer@podobot.local",
)


class PrototypeRBACService:
    def is_allowed(self, role_key: str, permission: PermissionDefault) -> bool:
        if role_key == "admin":
            return True
        if role_key == "producer":
            return permission.key not in PRODUCER_DENIED
        return permission.key.endswith(".view")


class SettingsDataService:
    def __init__(
        self,
        session: AsyncSession,
        rbac_service: PrototypeRBACService | None = None,
    ) -> None:
        self.session = session
        self.rbac_service = rbac_service or PrototypeRBACService()

    async def _ensure_defaults(self) -> None:
        async with DEFAULTS_LOCK:
            await self._ensure_defaults_locked()

    async def _ensure_defaults_locked(self) -> None:
        created = False
        roles = await self._roles_by_key()
        for role_default in ROLE_DEFAULTS:
            role = roles.get(role_default.key)
            if role is None:
                self.session.add(
                    Role(
                        key=role_default.key,
                        name=role_default.name,
                        description=role_default.description,
                        is_system=True,
                        is_assignable=True,
                    )
                )
                created = True
            elif not role.is_system:
                role.is_system = True
                created = True

        permissions = await self._permissions_by_key()
        for legacy_key in LEGACY_PERMISSION_KEYS:
            legacy_permission = permissions.get(legacy_key)
            if legacy_permission is not None:
                await self.session.delete(legacy_permission)
                permissions.pop(legacy_key, None)
                created = True

        if created:
            await self.session.flush()

        permissions = await self._permissions_by_key()
        for permission_default in PERMISSION_DEFAULTS:
            permission = permissions.get(permission_default.key)
            if permission is None:
                self.session.add(
                    Permission(
                        key=permission_default.key,
                        module=permission_default.module,
                        action=permission_default.action,
                        label=permission_default.label,
                        description=permission_default.description,
                        is_system=True,
                    )
                )
                created = True
            elif not permission.is_system:
                permission.is_system = True
                created = True

        if created:
            await self.session.flush()

        roles = await self._roles_by_key()
        permissions = await self._permissions_by_key()
        role_permissions = await self._role_permission_keys()
        role_permissions_created = False
        for role_key, role in roles.items():
            for permission in permissions.values():
                key = (role.id, permission.id)
                if key in role_permissions:
                    continue
                default = next(
                    (
                        permission_default
                        for permission_default in PERMISSION_DEFAULTS
                        if permission_default.key == permission.key
                    ),
                    None,
                )
                is_allowed = (
                    self.rbac_service.is_allowed(role_key, default)
                    if default is not None
                    else False
                )
                self.session.add(
                    RolePermission(
                        role_id=role.id,
                        permission_id=permission.id,
                        is_allowed=is_allowed,
                    )
                )
                role_permissions_created = True

        users_created = await self._ensure_default_users(roles)
        user_roles_created = await self._ensure_user_role_links()
        if created or role_permissions_created or users_created or user_roles_created:
            await self.session.commit()

    async def _ensure_default_users(self, roles: dict[str, Role]) -> bool:
        users_changed = False
        now = datetime.now(UTC)

        for default_user in DEFAULT_WORKSPACE_USERS:
            password = default_user.password or settings.auth_dev_admin_password
            user = await self._user_by_email(default_user.email)
            legacy_email = default_user.email.replace("@podobot.com", "@podobot.local")
            if user is None:
                legacy_user = await self._user_by_email(legacy_email)
                if legacy_user is not None:
                    user = legacy_user
                    user.email = default_user.email
                    users_changed = True
            if user is None and default_user.role_key == "viewer":
                legacy_reviewer = await self._user_by_email("reviewer@podobot.local")
                if legacy_reviewer is not None:
                    user = legacy_reviewer
                    user.email = default_user.email
                    users_changed = True
            if user is None:
                user = WorkspaceUser(
                    email=default_user.email,
                    full_name=default_user.full_name,
                    role_id=roles[default_user.role_key].id,
                    status=WorkspaceUserStatus.ACTIVE,
                    last_active_at=now,
                    password_hash=await hash_password_async(password),
                )
                self.session.add(user)
                users_changed = True
            else:
                if not user.full_name:
                    user.full_name = default_user.full_name
                    users_changed = True
                if user.role_id != roles[default_user.role_key].id:
                    user.role_id = roles[default_user.role_key].id
                    users_changed = True
                if user.status != WorkspaceUserStatus.ACTIVE:
                    user.status = WorkspaceUserStatus.ACTIVE
                    users_changed = True
                if not user.password_hash:
                    user.password_hash = await hash_password_async(password)
                    users_changed = True

        for email in LEGACY_DEMO_USER_EMAILS:
            legacy_user = await self._user_by_email(email)
            if legacy_user is not None and legacy_user.email != ADMIN_EMAIL:
                await self.session.delete(legacy_user)
                users_changed = True
        return users_changed

    async def _ensure_user_role_links(self) -> bool:
        created = False
        users = await self._users()
        role_links = await self._user_role_keys()
        for user in users:
            key = (user.id, user.role_id)
            if key in role_links:
                continue
            self.session.add(UserRole(user_id=user.id, role_id=user.role_id, is_primary=True))
            created = True
        return created

    async def _roles(self) -> list[Role]:
        result = await self.session.execute(select(Role).order_by(Role.name.asc()))
        return list(result.scalars().all())

    async def _roles_by_key(self) -> dict[str, Role]:
        result = await self.session.execute(select(Role))
        return {role.key: role for role in result.scalars().all()}

    async def _role(self, role_id: UUID) -> Role:
        role = await self.session.get(Role, role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return role

    async def _role_by_key(self, key: str) -> Role | None:
        result = await self.session.execute(select(Role).where(Role.key == key))
        return result.scalar_one_or_none()

    async def _permissions(self) -> list[Permission]:
        result = await self.session.execute(
            select(Permission).order_by(Permission.module.asc(), Permission.action.asc())
        )
        return list(result.scalars().all())

    async def _permissions_page(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        module: str | None = None,
        sort: str = "module",
    ) -> tuple[list[Permission], int]:
        pagination = OffsetParams(page=page, page_size=page_size)
        statement = select(Permission)
        if module:
            statement = statement.where(Permission.module == module)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Permission.key.ilike(pattern),
                    Permission.module.ilike(pattern),
                    Permission.action.ilike(pattern),
                    Permission.label.ilike(pattern),
                    Permission.description.ilike(pattern),
                )
            )
        total = int(
            (await self.session.execute(select(func.count()).select_from(statement.subquery())))
            .scalar_one()
            or 0
        )
        sort_options = {
            "module": (Permission.module.asc(), Permission.action.asc(), Permission.key.asc()),
            "-module": (Permission.module.desc(), Permission.action.asc(), Permission.key.asc()),
            "key": (Permission.key.asc(),),
            "-key": (Permission.key.desc(),),
            "created_at": (Permission.created_at.desc(), Permission.key.asc()),
            "-created_at": (Permission.created_at.desc(), Permission.key.asc()),
        }
        result = await self.session.execute(
            statement.order_by(*sort_options.get(sort, sort_options["module"]))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        return list(result.scalars().all()), total

    async def _permissions_by_key(self) -> dict[str, Permission]:
        result = await self.session.execute(select(Permission))
        return {permission.key: permission for permission in result.scalars().all()}

    async def _permission(self, permission_id: UUID) -> Permission:
        permission = await self.session.get(Permission, permission_id)
        if permission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found",
            )
        return permission

    async def _role_permission_keys(self) -> set[tuple[UUID, UUID]]:
        result = await self.session.execute(select(RolePermission))
        return {
            (role_permission.role_id, role_permission.permission_id)
            for role_permission in result.scalars().all()
        }

    async def _role_permissions(self) -> list[RolePermission]:
        result = await self.session.execute(select(RolePermission))
        return list(result.scalars().all())

    async def _user_role_keys(self) -> set[tuple[UUID, UUID]]:
        result = await self.session.execute(select(UserRole))
        return {(user_role.user_id, user_role.role_id) for user_role in result.scalars().all()}

    async def _user_roles(self, user_id: UUID) -> list[UserRole]:
        result = await self.session.execute(
            select(UserRole).where(UserRole.user_id == user_id).order_by(UserRole.created_at.asc())
        )
        return list(result.scalars().all())

    async def _user(self, user_id: UUID) -> WorkspaceUser:
        user = await self.session.get(WorkspaceUser, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace user not found",
            )
        return user

    async def _user_by_email(self, email: str) -> WorkspaceUser | None:
        result = await self.session.execute(
            select(WorkspaceUser).where(WorkspaceUser.email == email)
        )
        return result.scalar_one_or_none()

    async def _users(self) -> list[WorkspaceUser]:
        result = await self.session.execute(
            select(WorkspaceUser).order_by(WorkspaceUser.email.asc())
        )
        return list(result.scalars().all())

    async def _users_page(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status_filter: WorkspaceUserStatus | None = None,
        sort: str = "email",
    ) -> tuple[list[WorkspaceUser], int]:
        pagination = OffsetParams(page=page, page_size=page_size)
        statement = select(WorkspaceUser)
        if status_filter is not None:
            statement = statement.where(WorkspaceUser.status == status_filter)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    WorkspaceUser.email.ilike(pattern),
                    WorkspaceUser.full_name.ilike(pattern),
                )
            )
        total = int(
            (await self.session.execute(select(func.count()).select_from(statement.subquery())))
            .scalar_one()
            or 0
        )
        sort_options = {
            "email": (WorkspaceUser.email.asc(),),
            "-email": (WorkspaceUser.email.desc(),),
            "updated_at": (WorkspaceUser.updated_at.desc(), WorkspaceUser.email.asc()),
            "-updated_at": (WorkspaceUser.updated_at.desc(), WorkspaceUser.email.asc()),
            "created_at": (WorkspaceUser.created_at.desc(), WorkspaceUser.email.asc()),
            "-created_at": (WorkspaceUser.created_at.desc(), WorkspaceUser.email.asc()),
            "status": (WorkspaceUser.status.asc(), WorkspaceUser.email.asc()),
        }
        result = await self.session.execute(
            statement.order_by(*sort_options.get(sort, sort_options["email"]))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        return list(result.scalars().all()), total

    async def _invitations(self) -> list[UserInvitation]:
        result = await self.session.execute(
            select(UserInvitation).order_by(UserInvitation.created_at.desc())
        )
        return list(result.scalars().all())

    async def _audit_logs(self) -> list[SettingsAuditLog]:
        result = await self.session.execute(
            select(SettingsAuditLog).order_by(SettingsAuditLog.created_at.desc()).limit(20)
        )
        return list(result.scalars().all())

    async def _role_matrix_response(self) -> dict[str, object]:
        roles = await self._roles()
        permissions = await self._permissions()
        role_permissions = await self._role_permissions()
        role_permission_map = {
            (role_permission.role_id, role_permission.permission_id): role_permission.is_allowed
            for role_permission in role_permissions
        }
        permission_rows = [
            {
                "permission": permission,
                "role_permissions": [
                    {
                        "role_id": role.id,
                        "role_key": role.key,
                        "role_name": role.name,
                        "is_allowed": role_permission_map.get((role.id, permission.id), False),
                    }
                    for role in roles
                ],
            }
            for permission in permissions
        ]
        return {
            "roles": roles,
            "rows": permission_rows,
            "modules": sorted({permission.module for permission in permissions}),
            "grouped_permissions": self._grouped_permissions_response(permissions),
            "prototype_notice": PROTOTYPE_NOTICE,
        }

    async def _users_response(
        self,
        users: list[WorkspaceUser] | None = None,
    ) -> list[dict[str, object]]:
        return [await self._user_response(user) for user in (users or await self._users())]

    async def _invitations_response(self) -> list[dict[str, object]]:
        roles = {role.id: role for role in await self._roles()}
        return [
            self._invitation_response(invitation, roles[invitation.role_id])
            for invitation in await self._invitations()
        ]

    async def _user_response(self, user: WorkspaceUser) -> dict[str, object]:
        roles = await self._roles_for_user(user)
        primary_role = next((role for role in roles if role.id == user.role_id), roles[0])
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": primary_role,
            "roles": roles,
            "effective_permissions": await self._effective_permission_keys(user.id),
            "status": user.status,
            "invited_at": user.invited_at,
            "last_active_at": user.last_active_at,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

    def _invitation_response(self, invitation: UserInvitation, role: Role) -> dict[str, object]:
        return {
            "id": invitation.id,
            "email": invitation.email,
            "role": role,
            "status": invitation.status,
            "invited_by": invitation.invited_by,
            "created_user_id": invitation.created_user_id,
            "created_at": invitation.created_at,
            "updated_at": invitation.updated_at,
        }

    def _permission_list_response(
        self,
        permissions: list[Permission],
        *,
        pagination: dict[str, object] | None = None,
    ) -> dict[str, object]:
        response = {
            "items": permissions,
            "groups": self._grouped_permissions_response(permissions),
        }
        if pagination is not None:
            response.update(pagination)
        return response

    def _grouped_permissions_response(
        self,
        permissions: list[Permission],
    ) -> list[dict[str, object]]:
        groups: dict[str, list[Permission]] = {}
        for permission in permissions:
            groups.setdefault(permission.module, []).append(permission)
        return [
            {"module": module, "permissions": module_permissions}
            for module, module_permissions in sorted(groups.items())
        ]

    def _add_audit_log(
        self,
        *,
        action: str,
        redacted_changes: dict[str, object],
        reason: str | None = None,
        actor: str = "system",
    ) -> None:
        self.session.add(
            SettingsAuditLog(
                action=action,
                actor=actor,
                redacted_changes=redacted_changes,
                reason=reason,
            )
        )

    def _token_digest(self, email: str, created_at: datetime) -> str:
        return sha256(f"{email}:{created_at.isoformat()}".encode()).hexdigest()

    async def _roles_for_user(self, user: WorkspaceUser) -> list[Role]:
        role_links = await self._user_roles(user.id)
        role_ids = [role_link.role_id for role_link in role_links]
        if not role_ids:
            role_ids = [user.role_id]
        roles_by_id = {role.id: role for role in await self._roles()}
        return [roles_by_id[role_id] for role_id in role_ids if role_id in roles_by_id]

    async def _effective_permission_keys(self, user_id: UUID) -> list[str]:
        user = await self._user(user_id)
        roles = await self._roles_for_user(user)
        role_ids = [role.id for role in roles]
        if not role_ids:
            return []
        result = await self.session.execute(
            select(Permission.key)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id.in_(role_ids), RolePermission.is_allowed.is_(True))
            .order_by(Permission.key.asc())
        )
        return sorted(set(result.scalars().all()))

    async def _active_admin_count(self, *, excluding_user_id: UUID | None = None) -> int:
        users = [user for user in await self._users() if user.status == WorkspaceUserStatus.ACTIVE]
        count = 0
        for user in users:
            if excluding_user_id is not None and user.id == excluding_user_id:
                continue
            roles = await self._roles_for_user(user)
            if any(role.key == "admin" for role in roles):
                count += 1
        return count


class PermissionService(SettingsDataService):
    async def get_permissions(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        module: str | None = None,
        sort: str = "module",
    ) -> dict[str, object]:
        await self._ensure_defaults()
        permissions, total = await self._permissions_page(
            page=page,
            page_size=page_size,
            search=search,
            module=module,
            sort=sort,
        )
        return self._permission_list_response(
            permissions,
            pagination=offset_meta(total=total, page=page, page_size=page_size),
        )

    async def create_permission(self, payload: PermissionCreateRequest) -> dict[str, object]:
        await self._ensure_defaults()
        permissions = await self._permissions_by_key()
        if payload.key in permissions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Permission key already exists",
            )
        module, action = payload.key.split(".", 1)
        permission = Permission(
            key=payload.key,
            module=module,
            action=action,
            label=payload.label,
            description=payload.description,
            is_system=False,
        )
        self.session.add(permission)
        await self.session.flush()
        for role in await self._roles():
            self.session.add(
                RolePermission(role_id=role.id, permission_id=permission.id, is_allowed=False)
            )
        self._add_audit_log(
            action="permission_created",
            redacted_changes={"permission": payload.key},
            reason="Custom permission created.",
        )
        await self.session.commit()
        await self.session.refresh(permission)
        return permission

    async def update_permission(
        self,
        permission_id: UUID,
        payload: PermissionUpdateRequest,
    ) -> dict[str, object]:
        await self._ensure_defaults()
        permission = await self._permission(permission_id)
        changes = payload.model_dump(exclude_none=True)
        if "key" in changes and changes["key"] != permission.key:
            permissions = await self._permissions_by_key()
            if changes["key"] in permissions:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Permission key already exists",
                )
            module, action = changes["key"].split(".", 1)
            permission.key = changes["key"]
            permission.module = module
            permission.action = action
        if "label" in changes:
            permission.label = changes["label"]
        if "description" in changes:
            permission.description = changes["description"]
        self._add_audit_log(
            action="permission_updated",
            redacted_changes={"permission_id": str(permission.id), "changes": changes},
            reason="Permission definition updated.",
        )
        await self.session.commit()
        await self.session.refresh(permission)
        return permission

    async def delete_permission(self, permission_id: UUID) -> None:
        await self._ensure_defaults()
        permission = await self._permission(permission_id)
        if permission.is_system:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="System permissions cannot be deleted",
            )
        self._add_audit_log(
            action="permission_deleted",
            redacted_changes={"permission": permission.key},
            reason="Custom permission deleted.",
        )
        await self.session.delete(permission)
        await self.session.commit()


class RoleService(PermissionService):
    async def create_role(self, payload: RoleCreateRequest) -> dict[str, object]:
        await self._ensure_defaults()
        if await self._role_by_key(payload.key):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role key exists")
        role = Role(
            key=payload.key,
            name=payload.name,
            description=payload.description,
            is_system=False,
            is_assignable=payload.is_assignable,
        )
        self.session.add(role)
        await self.session.flush()
        for permission in await self._permissions():
            self.session.add(RolePermission(role_id=role.id, permission_id=permission.id))
        self._add_audit_log(
            action="role_created",
            redacted_changes={"role": role.key},
            reason="Custom role created.",
        )
        await self.session.commit()
        await self.session.refresh(role)
        return role

    async def update_role(self, role_id: UUID, payload: RoleUpdateRequest) -> dict[str, object]:
        await self._ensure_defaults()
        role = await self._role(role_id)
        changes = payload.model_dump(exclude_none=True)
        if "key" in changes and changes["key"] != role.key:
            if role.is_system:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Protected system role keys cannot be changed",
                )
            if await self._role_by_key(changes["key"]):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role key exists")
            role.key = changes["key"]
        if "name" in changes:
            role.name = changes["name"]
        if "description" in changes:
            role.description = changes["description"]
        if "is_assignable" in changes:
            role.is_assignable = changes["is_assignable"]
        self._add_audit_log(
            action="role_updated",
            redacted_changes={"role_id": str(role.id), "changes": changes},
            reason="Role settings updated.",
        )
        await self.session.commit()
        await self.session.refresh(role)
        return role

    async def delete_role(self, role_id: UUID) -> None:
        await self._ensure_defaults()
        role = await self._role(role_id)
        if role.is_system:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Protected system roles cannot be deleted",
            )
        result = await self.session.execute(
            select(UserRole.id).where(UserRole.role_id == role.id).limit(1)
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assigned roles cannot be deleted",
            )
        self._add_audit_log(
            action="role_deleted",
            redacted_changes={"role": role.key},
            reason="Custom role deleted.",
        )
        await self.session.delete(role)
        await self.session.commit()

    async def clone_role(self, role_id: UUID, payload: RoleCloneRequest) -> dict[str, object]:
        await self._ensure_defaults()
        source = await self._role(role_id)
        if await self._role_by_key(payload.key):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role key exists")
        clone = Role(
            key=payload.key,
            name=payload.name,
            description=payload.description or f"Cloned from {source.name}.",
            is_system=False,
            is_assignable=True,
        )
        self.session.add(clone)
        await self.session.flush()
        source_permissions = {
            role_permission.permission_id: role_permission.is_allowed
            for role_permission in await self._role_permissions()
            if role_permission.role_id == source.id
        }
        for permission in await self._permissions():
            self.session.add(
                RolePermission(
                    role_id=clone.id,
                    permission_id=permission.id,
                    is_allowed=source_permissions.get(permission.id, False),
                )
            )
        self._add_audit_log(
            action="role_cloned",
            redacted_changes={"source": source.key, "clone": clone.key},
            reason="Role cloned with permission assignments.",
        )
        await self.session.commit()
        await self.session.refresh(clone)
        return clone

    async def set_role_permissions(
        self,
        role_id: UUID,
        payload: RolePermissionsUpdateRequest,
    ) -> dict[str, object]:
        await self._ensure_defaults()
        role = await self._role(role_id)
        requested = set(payload.permission_ids)
        valid_permissions = {permission.id: permission for permission in await self._permissions()}
        if requested - set(valid_permissions):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="One or more permissions do not exist",
            )
        role_permissions = [
            role_permission
            for role_permission in await self._role_permissions()
            if role_permission.role_id == role.id
        ]
        existing = {
            role_permission.permission_id: role_permission for role_permission in role_permissions
        }
        for permission_id in valid_permissions:
            role_permission = existing.get(permission_id)
            if role_permission is None:
                role_permission = RolePermission(role_id=role.id, permission_id=permission_id)
                self.session.add(role_permission)
            role_permission.is_allowed = permission_id in requested
        self._add_audit_log(
            action="role_permissions_updated",
            redacted_changes={
                "role": role.key,
                "permission_count": len(requested),
            },
            reason="Role permission assignment saved.",
        )
        await self.session.commit()
        return await self._role_matrix_response()

    async def assign_role_permission(self, role_id: UUID, permission_id: UUID) -> dict[str, object]:
        role = await self._role(role_id)
        role_permissions = await self._role_permissions()
        role_permission = next(
            (
                item
                for item in role_permissions
                if item.role_id == role_id and item.permission_id == permission_id
            ),
            None,
        )
        if role_permission is None:
            await self._permission(permission_id)
            role_permission = RolePermission(role_id=role_id, permission_id=permission_id)
            self.session.add(role_permission)
        role_permission.is_allowed = True
        self._add_audit_log(
            action="role_permission_assigned",
            redacted_changes={"role": role.key, "permission_id": str(permission_id)},
        )
        await self.session.commit()
        return await self._role_matrix_response()

    async def remove_role_permission(self, role_id: UUID, permission_id: UUID) -> dict[str, object]:
        role = await self._role(role_id)
        role_permissions = await self._role_permissions()
        role_permission = next(
            (
                item
                for item in role_permissions
                if item.role_id == role_id and item.permission_id == permission_id
            ),
            None,
        )
        if role_permission is not None:
            role_permission.is_allowed = False
        self._add_audit_log(
            action="role_permission_removed",
            redacted_changes={"role": role.key, "permission_id": str(permission_id)},
        )
        await self.session.commit()
        return await self._role_matrix_response()


class AuthorizationService(RoleService):
    async def current_user_payload(self, user_id: UUID) -> dict[str, object]:
        await self._ensure_defaults()
        user = await self._user(user_id)
        if user.status != WorkspaceUserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Current user is not active",
            )
        roles = await self._roles_for_user(user)
        return {
            "id": user.id,
            "email": user.email,
            "name": user.full_name or user.email,
            "full_name": user.full_name,
            "status": user.status,
            "roles": roles,
            "permissions": await self._effective_permission_keys(user.id),
        }

    async def user_has_permission(self, user_id: UUID, permission_key: str) -> bool:
        permissions = await self._effective_permission_keys(user_id)
        return permission_key in permissions

    async def user_has_role(self, user_id: UUID, role_key: str) -> bool:
        user = await self._user(user_id)
        return any(role.key == role_key for role in await self._roles_for_user(user))


class AuthService(AuthorizationService):
    async def login(self, email: str, password: str) -> dict[str, object]:
        await self._ensure_defaults()
        user = await self._user_by_email(email)
        if user is None or not await verify_password_async(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if user.status != WorkspaceUserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only active users can sign in",
            )
        return await self.current_user_payload(user.id)

    async def dev_login(self) -> dict[str, object]:
        await self._ensure_defaults()
        user = await self._user_by_email(ADMIN_EMAIL)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Admin user was not initialized",
            )
        return await self.current_user_payload(user.id)


class SettingsService(AuthService):
    async def get_workspace(self) -> dict[str, object]:
        await self._ensure_defaults()
        return {
            "tab_names": SETTINGS_TAB_NAMES,
            "role_matrix": await self._role_matrix_response(),
            "users": await self._users_response(),
            "invitations": await self._invitations_response(),
            "prototype_notice": PROTOTYPE_NOTICE,
        }

    async def get_role_matrix(self) -> dict[str, object]:
        await self._ensure_defaults()
        return await self._role_matrix_response()

    async def get_user_management(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status_filter: WorkspaceUserStatus | None = None,
        sort: str = "email",
    ) -> dict[str, object]:
        await self._ensure_defaults()
        users, total = await self._users_page(
            page=page,
            page_size=page_size,
            search=search,
            status_filter=status_filter,
            sort=sort,
        )
        user_items = await self._users_response(users)
        return {
            "items": user_items,
            "users": user_items,
            "invitations": await self._invitations_response(),
            **offset_meta(total=total, page=page, page_size=page_size),
        }

    async def invite_user(self, payload: InviteUserRequest) -> dict[str, object]:
        await self._ensure_defaults()
        role = await self._role(payload.role_id)
        if not role.is_assignable:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This role cannot be assigned to invited users",
            )
        existing_user = await self._user_by_email(payload.email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A workspace user already exists for this email",
            )

        now = datetime.now(UTC)
        user = WorkspaceUser(
            email=payload.email,
            full_name=payload.full_name,
            role_id=role.id,
            status=WorkspaceUserStatus.INVITED,
            invited_at=now,
        )
        self.session.add(user)
        await self.session.flush()
        self.session.add(UserRole(user_id=user.id, role_id=role.id, is_primary=True))

        invitation = UserInvitation(
            email=payload.email,
            role_id=role.id,
            status=UserInvitationStatus.PENDING,
            invited_by="system",
            token_digest=self._token_digest(payload.email, now),
            created_user_id=user.id,
        )
        self.session.add(invitation)
        self._add_audit_log(
            action="user_invited",
            redacted_changes={
                "email": payload.email,
                "role": role.key,
            },
            reason="Prototype invitation created.",
        )
        await self.session.commit()
        await self.session.refresh(invitation)
        return self._invitation_response(invitation, role)

    async def update_user_status(
        self,
        user_id: UUID,
        payload: UserStatusUpdateRequest,
    ) -> dict[str, object]:
        await self._ensure_defaults()
        user = await self._user(user_id)
        previous_status = user.status
        if (
            previous_status == WorkspaceUserStatus.ACTIVE
            and payload.status != WorkspaceUserStatus.ACTIVE
            and any(role.key == "admin" for role in await self._roles_for_user(user))
            and await self._active_admin_count(excluding_user_id=user.id) < 1
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="At least one active admin user must remain",
            )
        user.status = payload.status
        if payload.status == WorkspaceUserStatus.ACTIVE and user.last_active_at is None:
            user.last_active_at = datetime.now(UTC)
        self._add_audit_log(
            action="user_status_updated",
            redacted_changes={
                "user_id": str(user.id),
                "email": user.email,
                "from": previous_status.value,
                "to": payload.status.value,
            },
            reason="User status changed.",
        )
        await self.session.commit()
        await self.session.refresh(user)
        return await self._user_response(user)

    async def assign_user_role(
        self,
        user_id: UUID,
        payload: UserRoleAssignRequest,
    ) -> dict[str, object]:
        await self._ensure_defaults()
        user = await self._user(user_id)
        role = await self._role(payload.role_id)
        if not role.is_assignable:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This role is not assignable",
            )
        user_roles = await self._user_roles(user.id)
        if any(user_role.role_id == role.id for user_role in user_roles):
            return await self._user_response(user)
        self.session.add(UserRole(user_id=user.id, role_id=role.id, is_primary=False))
        self._add_audit_log(
            action="user_role_assigned",
            redacted_changes={"user": user.email, "role": role.key},
            reason="Role assigned to user.",
        )
        await self.session.commit()
        return await self._user_response(user)

    async def remove_user_role(self, user_id: UUID, role_id: UUID) -> dict[str, object]:
        await self._ensure_defaults()
        user = await self._user(user_id)
        role = await self._role(role_id)
        user_roles = await self._user_roles(user.id)
        matching = next(
            (user_role for user_role in user_roles if user_role.role_id == role.id),
            None,
        )
        if matching is None:
            return await self._user_response(user)
        if len(user_roles) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Users must retain at least one role",
            )
        if (
            user.status == WorkspaceUserStatus.ACTIVE
            and role.key == "admin"
            and await self._active_admin_count(excluding_user_id=user.id) < 1
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="At least one active admin user must remain",
            )
        await self.session.delete(matching)
        remaining_roles = [user_role for user_role in user_roles if user_role.id != matching.id]
        if user.role_id == role.id and remaining_roles:
            replacement = remaining_roles[0]
            user.role_id = replacement.role_id
            replacement.is_primary = True
        self._add_audit_log(
            action="user_role_removed",
            redacted_changes={"user": user.email, "role": role.key},
            reason="Role removed from user.",
        )
        await self.session.commit()
        await self.session.refresh(user)
        return await self._user_response(user)
