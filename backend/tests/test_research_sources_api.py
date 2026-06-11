from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.endpoints.research_sources import get_research_source_service
from app.db.types import (
    ResearchSourceCategory,
    ResearchSourceProviderType,
    ResearchSourceStatus,
    WorkspaceUserStatus,
)
from app.main import create_app
from app.modules.research_sources.service import (
    RESEARCH_SOURCE_DEFAULTS,
    ResearchSourceConfigService,
    ResearchSourceService,
)
from app.research.providers.base import ProviderMode
from app.research.providers.credentials import ResearchCredentialProvider
from app.security.auth import CurrentUser, get_current_user
from app.security.secrets import decrypt_secret, is_encrypted_secret


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _source_payload(
    *,
    source_id=None,
    key: str = "gemini",
    name: str = "Gemini API",
    provider_type: ResearchSourceProviderType = ResearchSourceProviderType.GEMINI,
    category: ResearchSourceCategory = ResearchSourceCategory.LLM,
    enabled: bool = True,
    critical: bool = True,
    status: ResearchSourceStatus = ResearchSourceStatus.UNKNOWN,
    config_json: dict[str, object] | None = None,
    last_checked_at: str | None = None,
) -> dict[str, object]:
    now = _now()
    return {
        "id": str(source_id or uuid4()),
        "key": key,
        "name": name,
        "provider_type": provider_type.value,
        "category": category.value,
        "enabled": enabled,
        "critical": critical,
        "priority": 90,
        "status": status.value,
        "quota_status": "unknown" if status != ResearchSourceStatus.DISABLED else "disabled",
        "last_checked_at": last_checked_at,
        "last_failure_reason": None,
        "documents_fetched_today": 12,
        "success_rate": 0.96,
        "average_latency_ms": 180,
        "recent_failure_count": 0,
        "config_json": config_json or {"mode": "api", "api_key_ciphertext": "[REDACTED]"},
        "provider_mode": "mock" if status == ResearchSourceStatus.DISABLED else "real",
        "missing_configuration": False,
        "configuration_status": "source_api_key_configured",
        "connection_status": status.value,
        "last_test_result": "Not tested" if last_checked_at is None else status.value,
        "trend_provider_status": None,
        "created_at": now,
        "updated_at": now,
    }


class FakeResearchSourceService:
    def __init__(self) -> None:
        self.source_id = uuid4()

    async def list_sources(self, **kwargs):
        return {
            "items": [_source_payload(source_id=self.source_id)],
            "total": 10,
            "page": kwargs["page"],
            "page_size": kwargs["page_size"],
            "total_pages": 1,
            "has_next": False,
            "has_previous": False,
        }

    async def get_source(self, source_id):
        return _source_payload(source_id=source_id)

    async def update_source(self, source_id, payload):
        item = _source_payload(source_id=source_id)
        if payload.priority is not None:
            item["priority"] = payload.priority
        if payload.critical is not None:
            item["critical"] = payload.critical
        if payload.api_key is not None:
            item["config_json"] = {
                "mode": "api",
                "api_key_ciphertext": "[REDACTED]",
                "secret_configured": True,
                "secret_storage": "encrypted_database",
            }
            item["missing_configuration"] = False
            item["configuration_status"] = "source_api_key_configured"
        if payload.clear_api_key is True:
            item["config_json"] = {
                "mode": "api",
                "requires_api_key": True,
                "secret_configured": False,
            }
            item["missing_configuration"] = True
        return item

    async def enable_source(self, source_id):
        return _source_payload(
            source_id=source_id,
            enabled=True,
            status=ResearchSourceStatus.UNKNOWN,
        )

    async def disable_source(self, source_id):
        item = _source_payload(
            source_id=source_id,
            enabled=False,
            status=ResearchSourceStatus.DISABLED,
        )
        item["last_failure_reason"] = "Source disabled by administrator."
        return item

    async def test_source(self, source_id):
        checked_at = _now()
        return {
            "source": _source_payload(
                source_id=source_id,
                status=ResearchSourceStatus.HEALTHY,
                last_checked_at=checked_at,
            ),
            "success": True,
            "message": "Gemini API mock source connection is healthy.",
        }


def _current_user(*permissions: str) -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="operator@example.com",
        full_name="Operator",
        status=WorkspaceUserStatus.ACTIVE,
        role_keys=frozenset({"producer"}),
        permissions=frozenset(permissions),
    )


def _client(
    service: FakeResearchSourceService | None = None,
    current_user: CurrentUser | None = None,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_research_source_service] = (
        lambda: service or FakeResearchSourceService()
    )
    app.dependency_overrides[get_current_user] = lambda: (
        current_user or _current_user("integration.manage")
    )
    return TestClient(app)


def test_research_sources_are_seeded() -> None:
    keys = {source.key for source in RESEARCH_SOURCE_DEFAULTS}
    grok = next(source for source in RESEARCH_SOURCE_DEFAULTS if source.key == "grok_x")
    groq = next(source for source in RESEARCH_SOURCE_DEFAULTS if source.key == "groq")
    openai = next(source for source in RESEARCH_SOURCE_DEFAULTS if source.key == "openai")
    gemini = next(source for source in RESEARCH_SOURCE_DEFAULTS if source.key == "gemini")

    assert keys == {
        "reddit_json",
        "hn_algolia",
        "youtube_data_api",
        "exa",
        "firecrawl",
        "serpapi",
        "pytrends",
        "openai",
        "gemini",
        "groq",
        "grok_x",
    }
    assert len(RESEARCH_SOURCE_DEFAULTS) == 11
    assert openai.name == "OpenAI"
    assert openai.category == ResearchSourceCategory.LLM
    assert openai.enabled is True
    assert openai.critical is True
    assert openai.priority == 80
    assert openai.config_json["llm_primary_integration"] is True
    assert gemini.priority == 90
    assert gemini.config_json["llm_fallback_integration"] is True
    assert groq.priority == 100
    assert grok.name == "Grok LLM"
    assert grok.category == ResearchSourceCategory.LLM
    assert grok.enabled is True
    assert grok.priority == 110
    assert grok.config_json["llm_fallback_integration"] is True
    assert groq.name == "Groq LLM"
    assert groq.category == ResearchSourceCategory.LLM
    assert groq.enabled is True
    assert groq.config_json["llm_fallback_integration"] is True


def test_llm_fallback_default_priorities_are_migrated_once() -> None:
    service = ResearchSourceService(session=None)  # type: ignore[arg-type]
    groq_default = next(source for source in RESEARCH_SOURCE_DEFAULTS if source.key == "groq")

    source = SimpleNamespace(
        key="groq",
        priority=95,
        config_json={"llm_fallback_integration": True},
    )
    changed = service._sync_existing_default(source, groq_default)

    assert changed is True
    assert source.priority == 100

    custom_source = SimpleNamespace(
        key="groq",
        priority=42,
        config_json={"llm_fallback_integration": True},
    )
    changed = service._sync_existing_default(custom_source, groq_default)

    assert changed is False
    assert custom_source.priority == 42

    grok_default = next(source for source in RESEARCH_SOURCE_DEFAULTS if source.key == "grok_x")
    grok_source = SimpleNamespace(
        key="grok_x",
        priority=100,
        config_json={"llm_fallback_integration": True},
    )
    changed = service._sync_existing_default(grok_source, grok_default)

    assert changed is True
    assert grok_source.priority == 110


def test_buffer_is_not_seeded_as_research_source() -> None:
    keys = {source.key for source in RESEARCH_SOURCE_DEFAULTS}
    provider_types = {source.provider_type.value for source in RESEARCH_SOURCE_DEFAULTS}

    assert "buffer" not in keys
    assert "buffer" not in provider_types


def test_enabled_source_filter_returns_only_enabled_sources() -> None:
    enabled = SimpleNamespace(enabled=True, status=ResearchSourceStatus.HEALTHY)
    disabled = SimpleNamespace(enabled=False, status=ResearchSourceStatus.DISABLED)
    inconsistent_disabled = SimpleNamespace(enabled=True, status=ResearchSourceStatus.DISABLED)

    assert ResearchSourceService.is_enabled_for_research(enabled) is True
    assert ResearchSourceService.is_enabled_for_research(disabled) is False
    assert ResearchSourceService.is_enabled_for_research(inconsistent_disabled) is False


def test_research_source_list_is_paginated() -> None:
    response = _client().get("/api/v1/research/sources?page=1&page_size=20")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 10
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["items"][0]["key"] == "gemini"


def test_source_enable_endpoint_works() -> None:
    response = _client().post(f"/api/v1/research/sources/{uuid4()}/enable")

    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert response.json()["status"] == "unknown"


def test_source_disable_endpoint_works() -> None:
    response = _client().post(f"/api/v1/research/sources/{uuid4()}/disable")

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["status"] == "disabled"
    assert "disabled" in body["last_failure_reason"].lower()


def test_source_test_endpoint_stores_status_and_last_checked_at() -> None:
    response = _client().post(f"/api/v1/research/sources/{uuid4()}/test")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["source"]["status"] == "healthy"
    assert body["source"]["last_checked_at"] is not None


def test_unauthorized_user_cannot_configure_source() -> None:
    response = _client(current_user=_current_user("series.view")).patch(
        f"/api/v1/research/sources/{uuid4()}",
        json={"priority": 10},
    )

    assert response.status_code == 403
    assert "integration.manage" in response.text


def test_research_source_status_can_be_viewed_without_manage_permission() -> None:
    response = _client(current_user=_current_user("series.view")).get("/api/v1/research/sources")

    assert response.status_code == 200
    assert response.json()["items"][0]["status"] == "unknown"


def test_api_keys_and_config_secrets_are_not_returned_to_frontend() -> None:
    config = {
        "api_key": "super-secret-key",
        "nested": {"token": "raw-token", "safe": "visible"},
        "safe": "visible",
    }
    redacted = ResearchSourceConfigService().redact_config(config)

    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"] == {"token": "[REDACTED]", "safe": "visible"}
    assert redacted["safe"] == "visible"
    assert "super-secret-key" not in str(redacted)


def test_source_api_key_update_is_redacted() -> None:
    response = _client().patch(
        f"/api/v1/research/sources/{uuid4()}",
        json={"api_key": "source-secret-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["configuration_status"] == "source_api_key_configured"
    assert body["config_json"]["api_key_ciphertext"] == "[REDACTED]"
    assert "source-secret-key" not in str(body)


def test_source_secret_configures_required_provider() -> None:
    credentials = ResearchCredentialProvider()
    source_config = ResearchSourceConfigService().store_api_key(
        {"mode": "api"},
        "exa-source-key",
    )

    credential = credentials.credential_for(ResearchSourceProviderType.EXA, source_config)

    assert credential.value == "exa-source-key"
    assert is_encrypted_secret(source_config["api_key_ciphertext"])
    assert "api_key_secret" not in source_config
    assert (
        credentials.provider_mode(ResearchSourceProviderType.EXA, source_config)
        == ProviderMode.REAL
    )
    assert (
        credentials.missing_configuration(ResearchSourceProviderType.EXA, source_config)
        is False
    )
    assert (
        credentials.safe_configuration_status(ResearchSourceProviderType.EXA, source_config)
        == "source_api_key_configured"
    )
    assert (
        credentials.safe_configuration_status(ResearchSourceProviderType.GROK_X, {"mode": "api"})
        == "database_api_key_missing"
    )
    assert (
        credentials.safe_configuration_status(ResearchSourceProviderType.OPENAI, {"mode": "api"})
        == "database_api_key_missing"
    )


def test_plaintext_source_secret_is_migrated_to_encrypted() -> None:
    config_service = ResearchSourceConfigService()

    migrated_config, migrated = config_service.encrypted_config(
        {"mode": "api", "api_key_secret": "legacy-key"},
    )

    assert migrated is True
    assert "api_key_secret" not in migrated_config
    assert is_encrypted_secret(migrated_config["api_key_ciphertext"])
    assert decrypt_secret(str(migrated_config["api_key_ciphertext"])) == "legacy-key"
    assert migrated_config["secret_storage"] == "encrypted_database"


def test_env_api_keys_are_not_used_for_provider_credentials(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config.settings.exa_api_key", "env-key")
    credentials = ResearchCredentialProvider()

    credential = credentials.credential_for(ResearchSourceProviderType.EXA, {"mode": "api"})

    assert credential.value is None
    assert credentials.provider_mode(ResearchSourceProviderType.EXA) == ProviderMode.UNAVAILABLE
    assert credentials.missing_configuration(ResearchSourceProviderType.EXA) is True
