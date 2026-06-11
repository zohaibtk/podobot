from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.settings import get_settings_service
from app.main import create_app
from app.modules.settings.models import Role, WorkspaceUser
from app.modules.settings.schemas import validate_email
from app.modules.settings.service import (
    DEFAULT_WORKSPACE_USERS,
    PERMISSION_DEFAULTS,
    PROTOTYPE_NOTICE,
    ROLE_DEFAULTS,
    SETTINGS_TAB_NAMES,
    PrototypeRBACService,
    SettingsService,
)
from app.security.passwords import verify_password


def _role(role_id: UUID, key: str, name: str) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(role_id),
        "key": key,
        "name": name,
        "description": f"{name} role.",
        "is_system": True,
        "is_assignable": True,
        "created_at": now,
        "updated_at": now,
    }


def _permission(permission_id: UUID) -> dict[str, object]:
    return {
        "id": str(permission_id),
        "key": "series.create",
        "module": "series",
        "action": "create",
        "label": "Create series",
        "description": "Create new series.",
        "is_system": True,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }


def _workspace_user(user_id: UUID, role: dict[str, object]) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(user_id),
        "email": "user@example.com",
        "full_name": "Workspace User",
        "role": role,
        "status": "active",
        "invited_at": None,
        "last_active_at": now,
        "created_at": now,
        "updated_at": now,
    }


def _invitation(invitation_id: UUID, role: dict[str, object]) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(invitation_id),
        "email": "new.producer@example.com",
        "role": role,
        "status": "pending",
        "invited_by": "system",
        "created_user_id": str(uuid4()),
        "created_at": now,
        "updated_at": now,
    }


class FakeSettingsService:
    def __init__(self) -> None:
        self.admin_role_id = uuid4()
        self.producer_role_id = uuid4()
        self.user_id = uuid4()
        self.invitation_id = uuid4()
        self.permission_id = uuid4()
        self.admin_role = _role(self.admin_role_id, "admin", "Admin")
        self.producer_role = _role(self.producer_role_id, "producer", "Producer")

    async def get_workspace(self):
        return {
            "tab_names": SETTINGS_TAB_NAMES,
            "role_matrix": await self.get_role_matrix(),
            "users": [_workspace_user(self.user_id, self.producer_role)],
            "invitations": [_invitation(self.invitation_id, self.producer_role)],
            "prototype_notice": PROTOTYPE_NOTICE,
        }

    async def get_role_matrix(self):
        return {
            "roles": [self.admin_role, self.producer_role],
            "rows": [
                {
                    "permission": _permission(self.permission_id),
                    "role_permissions": [
                        {
                            "role_id": str(self.admin_role_id),
                            "role_key": "admin",
                            "role_name": "Admin",
                            "is_allowed": True,
                        },
                        {
                            "role_id": str(self.producer_role_id),
                            "role_key": "producer",
                            "role_name": "Producer",
                            "is_allowed": True,
                        },
                    ],
                }
            ],
            "modules": ["series"],
            "prototype_notice": PROTOTYPE_NOTICE,
        }

    async def get_user_management(self):
        return {
            "users": [_workspace_user(self.user_id, self.producer_role)],
            "invitations": [_invitation(self.invitation_id, self.producer_role)],
        }

    async def invite_user(self, payload):
        invitation = _invitation(self.invitation_id, self.producer_role)
        invitation["email"] = payload.email
        return invitation

    async def update_user_status(self, user_id, payload):
        user = _workspace_user(user_id, self.producer_role)
        user["status"] = payload.status.value
        return user


def _client(service: FakeSettingsService | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings_service] = lambda: service or FakeSettingsService()
    return TestClient(app)


def test_settings_workspace_exposes_role_and_user_tabs_with_prototype_notice() -> None:
    response = _client().get("/api/v1/settings")

    assert response.status_code == 200
    body = response.json()
    assert body["tab_names"] == [
        "Role management",
        "User management",
    ]
    assert "workspace_settings" not in body
    assert "audit_logs" not in body
    assert "Prototype RBAC enforcement" in body["prototype_notice"]


def test_workspace_settings_endpoint_removed_from_settings_module() -> None:
    response = _client().get("/api/v1/settings/workspace")

    assert response.status_code == 404


def test_role_matrix_matches_app_module_permissions() -> None:
    response = _client().get("/api/v1/settings/roles")

    assert response.status_code == 200
    body = response.json()
    assert body["modules"] == ["series"]
    assert body["rows"][0]["permission"]["module"] == "series"
    assert {cell["role_key"] for cell in body["rows"][0]["role_permissions"]} == {
        "admin",
        "producer",
    }


def test_invite_user_validates_email_and_returns_pending_invitation() -> None:
    service = FakeSettingsService()
    client = _client(service)

    invalid = client.post(
        "/api/v1/settings/users/invitations",
        json={"email": "bad", "role_id": str(service.producer_role_id)},
    )
    valid = client.post(
        "/api/v1/settings/users/invitations",
        json={
            "email": "New.Producer@Example.com",
            "role_id": str(service.producer_role_id),
            "full_name": "New Producer",
        },
    )

    assert invalid.status_code == 422
    assert valid.status_code == 200
    assert valid.json()["email"] == "new.producer@example.com"
    assert valid.json()["status"] == "pending"


def test_user_status_management_updates_status() -> None:
    response = _client().patch(
        f"/api/v1/settings/users/{uuid4()}/status",
        json={"status": "suspended"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "suspended"


def test_admin_and_producer_overlap_in_prototype_rbac() -> None:
    rbac = PrototypeRBACService()
    overlapping = [
        permission
        for permission in PERMISSION_DEFAULTS
        if rbac.is_allowed("admin", permission) and rbac.is_allowed("producer", permission)
    ]

    assert len(overlapping) >= 20
    assert rbac.is_allowed("producer", PERMISSION_DEFAULTS[0]) is True


@pytest.mark.anyio
async def test_default_workspace_users_include_requested_logins() -> None:
    session = FakeDefaultUserSession()
    roles = {
        role.key: Role(
            id=uuid4(),
            key=role.key,
            name=role.name,
            description=role.description,
            is_system=True,
            is_assignable=True,
        )
        for role in ROLE_DEFAULTS
    }
    service = SettingsService(session)  # type: ignore[arg-type]

    async def user_by_email(email: str) -> WorkspaceUser | None:
        return None

    service._user_by_email = user_by_email  # type: ignore[method-assign]

    assert await service._ensure_default_users(roles) is True

    users = {user.email: user for user in session.added_users}
    defaults = {user.email: user for user in DEFAULT_WORKSPACE_USERS}
    assert {"admin@podobot.com", "producer@podobot.com", "viewer@podobot.com"} <= set(users)
    assert users["producer@podobot.com"].role_id == roles["producer"].id
    assert users["viewer@podobot.com"].role_id == roles["viewer"].id
    assert verify_password(
        defaults["producer@podobot.com"].password or "",
        users["producer@podobot.com"].password_hash,
    )
    assert verify_password(
        defaults["viewer@podobot.com"].password or "",
        users["viewer@podobot.com"].password_hash,
    )


def test_validate_email_normalizes_case() -> None:
    assert validate_email("Admin@Example.COM") == "admin@example.com"


class FakeDefaultUserSession:
    def __init__(self) -> None:
        self.added_users: list[WorkspaceUser] = []

    def add(self, value: object) -> None:
        if isinstance(value, WorkspaceUser):
            self.added_users.append(value)

    async def delete(self, value: object) -> None:
        return None
