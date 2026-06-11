from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.main import create_app


def test_product_routes_require_authentication(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_dev_auto_login", False)
    client = TestClient(create_app())
    series_id = uuid4()

    protected_routes = [
        "/api/v1/series",
        f"/api/v1/series/{series_id}",
        f"/api/v1/series/{series_id}/discovery",
        f"/api/v1/series/{series_id}/episodes/plan",
        f"/api/v1/series/{series_id}/outlines",
        f"/api/v1/series/{series_id}/briefs",
        f"/api/v1/series/{series_id}/recordings",
        f"/api/v1/series/{series_id}/captions",
        f"/api/v1/series/{series_id}/schedules",
        "/api/v1/profiles",
        "/api/v1/strategy",
        "/api/v1/agents",
    ]

    for path in protected_routes:
        response = client.get(path)
        assert response.status_code == 401, path


def test_dev_login_requires_development_auto_login(monkeypatch) -> None:
    client = TestClient(create_app())

    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "auth_dev_auto_login", True)
    production_response = client.post("/api/v1/auth/dev-login")

    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "auth_dev_auto_login", False)
    disabled_response = client.post("/api/v1/auth/dev-login")

    assert production_response.status_code == 404
    assert disabled_response.status_code == 404


def test_production_settings_accept_safe_values() -> None:
    safe_settings = Settings(
        environment="production",
        auth_jwt_secret="production-jwt-secret",
        buffer_webhook_secret="production-buffer-webhook-secret",
        auth_dev_admin_password="production-admin-password",
        postgres_password="production-postgres-password",
        auth_dev_auto_login=False,
        _env_file=None,
    )

    assert safe_settings.environment == "production"


def test_vercel_settings_default_storage_uses_tmp(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")

    vercel_settings = Settings(_env_file=None)

    assert vercel_settings.local_storage_root == "/tmp/podobot-storage"


def test_vercel_relative_storage_resolves_under_tmp(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")

    vercel_settings = Settings(local_storage_root="podobot-storage", _env_file=None)

    assert vercel_settings.local_storage_root == "/tmp/podobot-storage"


@pytest.mark.parametrize(
    ("field_name", "override_value"),
    [
        ("auth_jwt_secret", "podobot-development-secret-change-me"),
        ("buffer_webhook_secret", "podobot-buffer-webhook-development-secret"),
        ("auth_dev_admin_password", "admin"),
        ("postgres_password", "podobot"),
        ("auth_dev_auto_login", True),
    ],
)
def test_production_settings_reject_unsafe_defaults(field_name: str, override_value) -> None:
    safe_values = {
        "environment": "production",
        "auth_jwt_secret": "production-jwt-secret",
        "buffer_webhook_secret": "production-buffer-webhook-secret",
        "auth_dev_admin_password": "production-admin-password",
        "postgres_password": "production-postgres-password",
        "auth_dev_auto_login": False,
        "_env_file": None,
    }
    safe_values[field_name] = override_value

    with pytest.raises(ValidationError, match=field_name):
        Settings(**safe_values)
