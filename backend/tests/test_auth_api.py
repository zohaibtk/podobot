from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

import app.security.auth as auth_module
from app.api.v1.endpoints.auth import get_auth_service
from app.api.v1.endpoints.series import get_series_service
from app.core.config import settings
from app.db.types import DiscoveryStatus, SeriesStage, SeriesStatus, WorkspaceUserStatus
from app.main import create_app
from app.security.auth import create_access_token, decode_access_token


def _role(role_id=None):
    now = datetime.now(UTC)
    return {
        "id": role_id or uuid4(),
        "key": "admin",
        "name": "Admin",
        "description": "Administrator.",
        "is_system": True,
        "is_assignable": True,
        "created_at": now,
        "updated_at": now,
    }


def _user_payload(user_id=None):
    user_id = user_id or uuid4()
    return {
        "id": user_id,
        "email": "admin@example.com",
        "name": "Admin User",
        "full_name": "Admin User",
        "status": WorkspaceUserStatus.ACTIVE,
        "roles": [_role()],
        "permissions": ["series.create", "settings.manage"],
    }


class FakeAuthService:
    def __init__(self) -> None:
        self.user_id = uuid4()

    async def login(self, email, password):
        if email != "admin@example.com" or password != "password":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        return _user_payload(self.user_id)

    async def current_user_payload(self, user_id):
        return _user_payload(user_id)


class FakeAuthorizationService:
    def __init__(self, session) -> None:
        self.session = session

    async def current_user_payload(self, user_id):
        return _user_payload(user_id)


class FakeSeriesService:
    async def create_series(self, payload):
        now = datetime.now(UTC).isoformat()
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


def _client(auth_service=None) -> TestClient:
    app = create_app()
    if auth_service is not None:
        app.dependency_overrides[get_auth_service] = lambda: auth_service
    return TestClient(app)


def test_successful_login_returns_bearer_token_and_user(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_dev_auto_login", False)
    response = _client(FakeAuthService()).post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "password"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "admin@example.com"
    assert body["user"]["name"] == "Admin User"
    assert body["refresh_token_placeholder"]


def test_failed_login_returns_invalid_credentials(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_dev_auto_login", False)
    response = _client(FakeAuthService()).post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong"},
    )

    assert response.status_code == 401
    assert "Invalid email or password" in response.text


def test_current_user_endpoint_uses_valid_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_dev_auto_login", False)
    monkeypatch.setattr(auth_module, "AuthorizationService", FakeAuthorizationService)
    user_id = uuid4()
    token = create_access_token(user_id).token

    response = _client(FakeAuthService()).get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(user_id)
    assert response.json()["permissions"] == ["series.create", "settings.manage"]


def test_protected_route_without_token_is_denied(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_dev_auto_login", False)
    app = create_app()
    app.dependency_overrides[get_series_service] = lambda: FakeSeriesService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/series",
        json={
            "name": "AI Briefings",
            "audience": "CIOs",
            "description": "Weekly executive conversations.",
        },
    )

    assert response.status_code == 401
    assert "Authentication required" in response.text


def test_protected_route_with_valid_token_is_allowed(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_dev_auto_login", False)
    monkeypatch.setattr(auth_module, "AuthorizationService", FakeAuthorizationService)
    app = create_app()
    app.dependency_overrides[get_series_service] = lambda: FakeSeriesService()
    client = TestClient(app)
    token = create_access_token(uuid4()).token

    response = client.post(
        "/api/v1/series",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "AI Briefings",
            "audience": "CIOs",
            "description": "Weekly executive conversations.",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "AI Briefings"


def test_expired_token_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_access_token_minutes", -1)
    token = create_access_token(uuid4()).token

    with pytest.raises(HTTPException) as exc:
        decode_access_token(token)

    assert exc.value.status_code == 401
    assert "expired" in str(exc.value.detail).lower()
