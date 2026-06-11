import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def enable_legacy_unit_test_dev_auth(monkeypatch):
    monkeypatch.setattr(settings, "auth_dev_auto_login", True)
