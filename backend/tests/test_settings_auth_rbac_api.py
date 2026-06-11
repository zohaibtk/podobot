from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.api.v1.endpoints.series import get_series_service
from app.api.v1.endpoints.settings import get_settings_service
from app.db.types import DiscoveryStatus, SeriesStage, SeriesStatus, WorkspaceUserStatus
from app.main import create_app
from app.security.auth import CurrentUser, get_current_user


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _role(role_id: UUID | None = None, *, key: str = "editor", system: bool = False):
    return {
        "id": str(role_id or uuid4()),
        "key": key,
        "name": key.replace("_", " ").title(),
        "description": f"{key} role.",
        "is_system": system,
        "is_assignable": True,
        "created_at": _now(),
        "updated_at": _now(),
    }


def _permission(permission_id: UUID | None = None, *, key: str = "series.create"):
    module, action = key.split(".", 1)
    return {
        "id": str(permission_id or uuid4()),
        "key": key,
        "module": module,
        "action": action,
        "label": key.replace(".", " ").title(),
        "description": f"Allows {key}.",
        "is_system": key in {"series.create", "role.manage", "user.manage"},
        "created_at": _now(),
        "updated_at": _now(),
    }


def _user(user_id: UUID, roles):
    return {
        "id": str(user_id),
        "email": "operator@example.com",
        "full_name": "Operator",
        "role": roles[0],
        "roles": roles,
        "effective_permissions": ["series.create", "role.manage"],
        "status": "active",
        "invited_at": None,
        "last_active_at": _now(),
        "created_at": _now(),
        "updated_at": _now(),
    }


class FakeSettingsRBACService:
    def __init__(self) -> None:
        self.admin_role_id = uuid4()
        self.custom_role_id = uuid4()
        self.permission_id = uuid4()
        self.user_id = uuid4()

    async def get_permissions(self):
        permission = _permission(self.permission_id, key="series.create")
        return {
            "items": [permission],
            "groups": [{"module": "series", "permissions": [permission]}],
        }

    async def create_permission(self, payload):
        return _permission(key=payload.key)

    async def update_permission(self, permission_id, payload):
        return _permission(permission_id, key=payload.key or "series.create")

    async def delete_permission(self, permission_id):
        return None

    async def get_role_matrix(self):
        admin = _role(self.admin_role_id, key="admin", system=True)
        custom = _role(self.custom_role_id, key="editor")
        permission = _permission(self.permission_id, key="series.create")
        return {
            "roles": [admin, custom],
            "rows": [
                {
                    "permission": permission,
                    "role_permissions": [
                        {
                            "role_id": str(self.admin_role_id),
                            "role_key": "admin",
                            "role_name": "Admin",
                            "is_allowed": True,
                        },
                        {
                            "role_id": str(self.custom_role_id),
                            "role_key": "editor",
                            "role_name": "Editor",
                            "is_allowed": False,
                        },
                    ],
                }
            ],
            "modules": ["series"],
            "grouped_permissions": [{"module": "series", "permissions": [permission]}],
            "prototype_notice": "Prototype RBAC enforcement is active.",
        }

    async def create_role(self, payload):
        return _role(key=payload.key)

    async def update_role(self, role_id, payload):
        return _role(role_id, key=payload.key or "editor")

    async def delete_role(self, role_id):
        if role_id == self.admin_role_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Protected system roles cannot be deleted",
            )
        return None

    async def clone_role(self, role_id, payload):
        return _role(key=payload.key)

    async def set_role_permissions(self, role_id, payload):
        return await self.get_role_matrix()

    async def assign_role_permission(self, role_id, permission_id):
        return await self.get_role_matrix()

    async def remove_role_permission(self, role_id, permission_id):
        return await self.get_role_matrix()

    async def get_user_management(self):
        admin = _role(self.admin_role_id, key="admin", system=True)
        return {"users": [_user(self.user_id, [admin])], "invitations": []}

    async def assign_user_role(self, user_id, payload):
        admin = _role(self.admin_role_id, key="admin", system=True)
        editor = _role(payload.role_id, key="editor")
        return _user(user_id, [admin, editor])

    async def remove_user_role(self, user_id, role_id):
        admin = _role(self.admin_role_id, key="admin", system=True)
        return _user(user_id, [admin])

    async def update_user_status(self, user_id, payload):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="At least one active admin user must remain",
        )


class FakeSeriesService:
    async def create_series(self, payload):
        now = _now()
        return {
            "id": str(uuid4()),
            "name": payload.name,
            "audience": payload.audience,
            "description": payload.description,
            "guest_name": payload.guest_name,
            "status": SeriesStatus.RESEARCHING.value,
            "discovery_status": DiscoveryStatus.RUNNING.value,
            "current_stage": SeriesStage.DISCOVERY.value,
            "created_at": now,
            "updated_at": now,
        }


def _current_user(*permissions: str, roles: set[str] | None = None):
    return CurrentUser(
        id=uuid4(),
        email="operator@example.com",
        full_name="Operator",
        status=WorkspaceUserStatus.ACTIVE,
        role_keys=frozenset(roles or {"producer"}),
        permissions=frozenset(permissions),
    )


def _client(
    service: FakeSettingsRBACService | None = None,
    current_user: CurrentUser | None = None,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings_service] = lambda: service or FakeSettingsRBACService()
    app.dependency_overrides[get_current_user] = lambda: (
        current_user
        or _current_user(
            "settings.manage",
            "role.manage",
            "user.manage",
        )
    )
    return TestClient(app)


def test_permission_crud_and_grouping_routes() -> None:
    client = _client()

    listed = client.get("/api/v1/settings/permissions")
    created = client.post(
        "/api/v1/settings/permissions",
        json={
            "key": "dashboard.view",
            "label": "View dashboard",
            "description": "Open dashboard.",
        },
    )
    edited = client.patch(
        f"/api/v1/settings/permissions/{uuid4()}",
        json={"key": "series.edit", "label": "Edit series"},
    )
    deleted = client.delete(f"/api/v1/settings/permissions/{uuid4()}")

    assert listed.status_code == 200
    assert listed.json()["groups"][0]["module"] == "series"
    assert created.status_code == 201
    assert created.json()["key"] == "dashboard.view"
    assert edited.status_code == 200
    assert edited.json()["key"] == "series.edit"
    assert deleted.status_code == 204


def test_role_crud_clone_and_permission_assignment_routes() -> None:
    service = FakeSettingsRBACService()
    client = _client(service)

    created = client.post(
        "/api/v1/settings/roles",
        json={"key": "editor", "name": "Editor", "description": "Edits content."},
    )
    edited = client.patch(
        f"/api/v1/settings/roles/{service.custom_role_id}",
        json={"name": "Senior Editor"},
    )
    cloned = client.post(
        f"/api/v1/settings/roles/{service.custom_role_id}/clone",
        json={"key": "editor_clone", "name": "Editor Clone"},
    )
    assigned = client.put(
        f"/api/v1/settings/roles/{service.custom_role_id}/permissions",
        json={"permission_ids": [str(service.permission_id)]},
    )
    deleted = client.delete(f"/api/v1/settings/roles/{service.custom_role_id}")

    assert created.status_code == 201
    assert edited.status_code == 200
    assert cloned.status_code == 200
    assert assigned.status_code == 200
    assert deleted.status_code == 204


def test_protected_system_roles_cannot_be_deleted() -> None:
    service = FakeSettingsRBACService()
    response = _client(service).delete(f"/api/v1/settings/roles/{service.admin_role_id}")

    assert response.status_code == 409
    assert "Protected system roles" in response.text


def test_user_role_assignment_and_last_active_admin_guard() -> None:
    service = FakeSettingsRBACService()
    client = _client(service)

    assigned = client.post(
        f"/api/v1/settings/users/{service.user_id}/roles",
        json={"role_id": str(service.custom_role_id)},
    )
    removed = client.delete(
        f"/api/v1/settings/users/{service.user_id}/roles/{service.custom_role_id}"
    )
    deactivated = client.patch(
        f"/api/v1/settings/users/{service.user_id}/status",
        json={"status": "suspended"},
    )

    assert assigned.status_code == 200
    assert len(assigned.json()["roles"]) == 2
    assert removed.status_code == 200
    assert deactivated.status_code == 409
    assert "active admin" in deactivated.text


def test_protected_route_denies_missing_permission_and_allows_valid_permission() -> None:
    app = create_app()
    app.dependency_overrides[get_series_service] = lambda: FakeSeriesService()
    app.dependency_overrides[get_current_user] = lambda: _current_user()
    client = TestClient(app)
    payload = {
        "name": "AI Briefings",
        "audience": "CIOs",
        "description": "Weekly executive conversations.",
    }

    denied = client.post("/api/v1/series", json=payload)

    app.dependency_overrides[get_current_user] = lambda: _current_user("series.create")
    allowed = client.post("/api/v1/series", json=payload)

    assert denied.status_code == 403
    assert "series.create" in denied.text
    assert allowed.status_code == 201
