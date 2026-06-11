from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.types import (
    ResearchSourceCategory,
    ResearchSourceProviderType,
    ResearchSourceStatus,
)
from app.modules.research_sources.models import ResearchSource
from app.modules.research_sources.schemas import ResearchSourceUpdateRequest
from app.research.providers.credentials import ResearchCredentialProvider
from app.schemas.pagination import OffsetParams, offset_meta
from app.security.secrets import encrypt_secret, is_encrypted_secret, mask_secret


@dataclass(frozen=True)
class ResearchSourceDefault:
    key: str
    name: str
    provider_type: ResearchSourceProviderType
    category: ResearchSourceCategory
    enabled: bool
    critical: bool
    priority: int
    config_json: dict[str, object]
    status: ResearchSourceStatus = ResearchSourceStatus.UNKNOWN
    quota_status: str = "unknown"


@dataclass(frozen=True)
class ResearchSourceHealthResult:
    success: bool
    status: ResearchSourceStatus
    message: str
    quota_status: str
    average_latency_ms: int
    success_rate: float
    recent_failure_count: int


RESEARCH_SOURCE_DEFAULTS = [
    ResearchSourceDefault(
        key="reddit_json",
        name="Reddit JSON",
        provider_type=ResearchSourceProviderType.REDDIT_JSON,
        category=ResearchSourceCategory.DISCOVERY,
        enabled=True,
        critical=False,
        priority=10,
        config_json={"mode": "public_json", "rate_limit_hint": "community-dependent"},
    ),
    ResearchSourceDefault(
        key="hn_algolia",
        name="HN Algolia",
        provider_type=ResearchSourceProviderType.HN_ALGOLIA,
        category=ResearchSourceCategory.DISCOVERY,
        enabled=True,
        critical=False,
        priority=20,
        config_json={"mode": "public_api", "index": "story"},
    ),
    ResearchSourceDefault(
        key="youtube_data_api",
        name="YouTube Data API v3",
        provider_type=ResearchSourceProviderType.YOUTUBE_DATA_API,
        category=ResearchSourceCategory.DISCOVERY,
        enabled=True,
        critical=False,
        priority=30,
        config_json={"mode": "api", "requires_api_key": True, "secret_configured": False},
    ),
    ResearchSourceDefault(
        key="exa",
        name="Exa",
        provider_type=ResearchSourceProviderType.EXA,
        category=ResearchSourceCategory.DISCOVERY,
        enabled=True,
        critical=False,
        priority=40,
        config_json={"mode": "api", "requires_api_key": True, "secret_configured": False},
    ),
    ResearchSourceDefault(
        key="firecrawl",
        name="Firecrawl",
        provider_type=ResearchSourceProviderType.FIRECRAWL,
        category=ResearchSourceCategory.SCRAPING,
        enabled=True,
        critical=False,
        priority=50,
        config_json={"mode": "api", "requires_api_key": True, "secret_configured": False},
    ),
    ResearchSourceDefault(
        key="serpapi",
        name="SerpAPI",
        provider_type=ResearchSourceProviderType.SERPAPI,
        category=ResearchSourceCategory.TRENDS,
        enabled=True,
        critical=False,
        priority=60,
        config_json={"mode": "api", "requires_api_key": True, "secret_configured": False},
    ),
    ResearchSourceDefault(
        key="pytrends",
        name="pytrends",
        provider_type=ResearchSourceProviderType.PYTRENDS,
        category=ResearchSourceCategory.TRENDS,
        enabled=True,
        critical=False,
        priority=70,
        config_json={"mode": "library", "rate_limit_hint": "google-trends-session"},
    ),
    ResearchSourceDefault(
        key="openai",
        name="OpenAI",
        provider_type=ResearchSourceProviderType.OPENAI,
        category=ResearchSourceCategory.LLM,
        enabled=True,
        critical=True,
        priority=80,
        config_json={
            "mode": "api",
            "requires_api_key": True,
            "secret_configured": False,
            "llm_primary_integration": True,
        },
    ),
    ResearchSourceDefault(
        key="gemini",
        name="Gemini API",
        provider_type=ResearchSourceProviderType.GEMINI,
        category=ResearchSourceCategory.LLM,
        enabled=True,
        critical=False,
        priority=90,
        config_json={
            "mode": "api",
            "requires_api_key": True,
            "secret_configured": False,
            "llm_fallback_integration": True,
        },
    ),
    ResearchSourceDefault(
        key="groq",
        name="Groq LLM",
        provider_type=ResearchSourceProviderType.GROQ,
        category=ResearchSourceCategory.LLM,
        enabled=True,
        critical=False,
        priority=100,
        config_json={
            "mode": "api",
            "requires_api_key": True,
            "secret_configured": False,
            "llm_fallback_integration": True,
        },
    ),
    ResearchSourceDefault(
        key="grok_x",
        name="Grok LLM",
        provider_type=ResearchSourceProviderType.GROK_X,
        category=ResearchSourceCategory.LLM,
        enabled=True,
        critical=False,
        priority=110,
        config_json={
            "mode": "api",
            "requires_api_key": True,
            "secret_configured": False,
            "llm_fallback_integration": True,
        },
    ),
]

SENSITIVE_CONFIG_MARKERS = (
    "secret",
    "api_key",
    "apikey",
    "token",
    "password",
    "credential",
)

PLAINTEXT_SECRET_KEYS = ("api_key_secret", "api_key", "secret", "token")
ENCRYPTED_API_KEY_KEY = "api_key_ciphertext"
FALLBACK_PRIORITY_MIGRATIONS = {
    "groq": 95,
    "grok_x": 100,
}


class ResearchSourceConfigService:
    def store_api_key(
        self,
        config_json: dict[str, object] | None,
        api_key: str,
    ) -> dict[str, object]:
        cleaned = api_key.strip()
        next_config = self._without_secret_keys(config_json or {})
        next_config[ENCRYPTED_API_KEY_KEY] = encrypt_secret(cleaned)
        next_config["secret_configured"] = True
        next_config["secret_storage"] = "encrypted_database"
        next_config["masked_label"] = mask_secret(cleaned)
        return next_config

    def clear_api_key(self, config_json: dict[str, object] | None) -> dict[str, object]:
        next_config = self._without_secret_keys(config_json or {})
        next_config["secret_configured"] = False
        next_config.pop("secret_storage", None)
        next_config.pop("masked_label", None)
        return next_config

    def encrypted_config(
        self,
        config_json: dict[str, object] | None,
    ) -> tuple[dict[str, object], bool]:
        config = dict(config_json or {})
        encrypted = config.get(ENCRYPTED_API_KEY_KEY)
        plaintext = self._plaintext_secret(config)
        if plaintext:
            return self.store_api_key(config, plaintext), True
        if is_encrypted_secret(encrypted):
            cleaned = self._without_plaintext_secret_keys(config)
            cleaned["secret_configured"] = True
            cleaned.setdefault("secret_storage", "encrypted_database")
            return cleaned, cleaned != config
        return config, False

    def redact_config(self, config_json: dict[str, object] | None) -> dict[str, object]:
        return self._redact_mapping(config_json or {})

    def _redact_mapping(self, value: dict[str, object]) -> dict[str, object]:
        redacted: dict[str, object] = {}
        for key, item in value.items():
            if self._is_sensitive_key(key):
                redacted[key] = "[REDACTED]" if item not in (None, "", False) else item
            elif isinstance(item, dict):
                redacted[key] = self._redact_mapping(item)
            elif isinstance(item, list):
                redacted[key] = [self._redact_value(entry) for entry in item]
            else:
                redacted[key] = item
        return redacted

    def _redact_value(self, value: object) -> object:
        if isinstance(value, dict):
            return self._redact_mapping(value)
        if isinstance(value, list):
            return [self._redact_value(entry) for entry in value]
        return value

    def _is_sensitive_key(self, key: str) -> bool:
        normalized = key.lower()
        return any(marker in normalized for marker in SENSITIVE_CONFIG_MARKERS)

    def _plaintext_secret(self, config_json: dict[str, object]) -> str | None:
        for key in PLAINTEXT_SECRET_KEYS:
            value = config_json.get(key)
            if isinstance(value, str) and value.strip() and not is_encrypted_secret(value):
                return value.strip()
        return None

    def _without_secret_keys(self, config_json: dict[str, object]) -> dict[str, object]:
        next_config = self._without_plaintext_secret_keys(config_json)
        next_config.pop(ENCRYPTED_API_KEY_KEY, None)
        return next_config

    def _without_plaintext_secret_keys(
        self,
        config_json: dict[str, object],
    ) -> dict[str, object]:
        return {
            key: value
            for key, value in config_json.items()
            if key not in PLAINTEXT_SECRET_KEYS
        }


class ResearchSourceHealthService:
    def __init__(self, credential_provider: ResearchCredentialProvider | None = None) -> None:
        self.credential_provider = credential_provider or ResearchCredentialProvider()

    def test_source(self, source: ResearchSource) -> ResearchSourceHealthResult:
        if not source.enabled:
            return ResearchSourceHealthResult(
                success=False,
                status=ResearchSourceStatus.DISABLED,
                message=f"{source.name} is disabled.",
                quota_status="disabled",
                average_latency_ms=0,
                success_rate=source.success_rate,
                recent_failure_count=source.recent_failure_count,
            )

        config = source.config_json or {}
        if config.get("simulate_failure") is True or config.get("force_failure") is True:
            return ResearchSourceHealthResult(
                success=False,
                status=ResearchSourceStatus.FAILED,
                message=f"{source.name} failed the source health check.",
                quota_status="failed",
                average_latency_ms=max(source.average_latency_ms, 900),
                success_rate=0.42,
                recent_failure_count=source.recent_failure_count + 1,
            )

        latency = 120 + min(source.priority, 100)
        provider_mode = self.credential_provider.provider_mode(
            source.provider_type,
            source.config_json,
        )
        status_value = ResearchSourceStatus.HEALTHY
        message = f"{source.name} {provider_mode.value} provider configuration is available."
        quota_status = "available"
        success_rate = 0.99
        recent_failure_count = 0

        if self.credential_provider.missing_configuration(
            source.provider_type,
            source.config_json,
        ):
            status_value = ResearchSourceStatus.WARNING
            message = f"{source.name} credentials are not configured."
            quota_status = "credentials_pending"
            success_rate = 0.92

        return ResearchSourceHealthResult(
            success=status_value != ResearchSourceStatus.FAILED,
            status=status_value,
            message=message,
            quota_status=quota_status,
            average_latency_ms=latency,
            success_rate=success_rate,
            recent_failure_count=recent_failure_count,
        )


class ResearchSourceService:
    def __init__(
        self,
        session: AsyncSession,
        config_service: ResearchSourceConfigService | None = None,
        health_service: ResearchSourceHealthService | None = None,
        credential_provider: ResearchCredentialProvider | None = None,
    ) -> None:
        self.session = session
        self.config_service = config_service or ResearchSourceConfigService()
        self.health_service = health_service or ResearchSourceHealthService()
        self.credential_provider = credential_provider or ResearchCredentialProvider()

    async def list_sources(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        category: ResearchSourceCategory | None = None,
        status_filter: ResearchSourceStatus | None = None,
        enabled: bool | None = None,
        search: str | None = None,
        sort: str = "priority",
    ) -> dict[str, object]:
        await self.ensure_defaults()
        pagination = OffsetParams(page=page, page_size=page_size)
        statement = self._filtered_statement(
            category=category,
            status_filter=status_filter,
            enabled=enabled,
            search=search,
        )
        total = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(statement.subquery())
                )
            ).scalar_one()
            or 0
        )
        order_by = self._order_by(sort)
        result = await self.session.execute(
            statement.order_by(*order_by).offset(pagination.offset).limit(pagination.page_size)
        )
        sources = list(result.scalars().all())
        from app.modules.research.service import ResearchPersistenceService

        metrics = await ResearchPersistenceService(self.session).source_metrics(
            [source.id for source in sources]
        )
        return {
            "items": [self._source_response(source, metrics.get(source.id)) for source in sources],
            **offset_meta(total=total, page=page, page_size=page_size),
        }

    async def get_source(self, source_id: UUID) -> dict[str, object]:
        await self.ensure_defaults()
        source = await self._get_source(source_id)
        from app.modules.research.service import ResearchPersistenceService

        metrics = await ResearchPersistenceService(self.session).source_metrics([source.id])
        return self._source_response(source, metrics.get(source.id))

    async def update_source(
        self,
        source_id: UUID,
        payload: ResearchSourceUpdateRequest,
    ) -> dict[str, object]:
        await self.ensure_defaults()
        source = await self._get_source(source_id)
        updates = payload.model_dump(exclude_unset=True)

        if "critical" in updates:
            source.critical = bool(updates["critical"])
        if "priority" in updates:
            source.priority = int(updates["priority"])
        if "quota_status" in updates:
            source.quota_status = str(updates["quota_status"])
        if "config_json" in updates:
            merged_config = {
                **(source.config_json or {}),
                **(updates["config_json"] or {}),
            }
            source.config_json = self.config_service.encrypted_config(merged_config)[0]
            if source.enabled:
                source.status = ResearchSourceStatus.UNKNOWN
                source.last_failure_reason = "Source configuration changed; test required."
        if updates.get("api_key"):
            source.config_json = self.config_service.store_api_key(
                source.config_json,
                str(updates["api_key"]),
            )
            if source.enabled:
                source.status = ResearchSourceStatus.UNKNOWN
                source.last_failure_reason = "Source configuration changed; test required."
        if updates.get("clear_api_key") is True:
            source.config_json = self.config_service.clear_api_key(source.config_json)
            if source.enabled:
                source.status = ResearchSourceStatus.UNKNOWN
                source.last_failure_reason = "Source configuration changed; test required."

        await self.session.commit()
        await self.session.refresh(source)
        return self._source_response(source)

    async def enable_source(self, source_id: UUID) -> dict[str, object]:
        await self.ensure_defaults()
        source = await self._get_source(source_id)
        source.enabled = True
        source.status = ResearchSourceStatus.UNKNOWN
        source.quota_status = "unknown"
        source.last_failure_reason = None
        await self.session.commit()
        await self.session.refresh(source)
        return self._source_response(source)

    async def disable_source(self, source_id: UUID) -> dict[str, object]:
        await self.ensure_defaults()
        source = await self._get_source(source_id)
        source.enabled = False
        source.status = ResearchSourceStatus.DISABLED
        source.quota_status = "disabled"
        source.last_failure_reason = "Source disabled by administrator."
        await self.session.commit()
        await self.session.refresh(source)
        return self._source_response(source)

    async def test_source(self, source_id: UUID) -> dict[str, object]:
        await self.ensure_defaults()
        source = await self._get_source(source_id)
        from app.research.providers.registry import ResearchProviderRegistry

        result = await ResearchProviderRegistry(
            self.session,
            credential_provider=self.credential_provider,
        ).test_source_connection(source.key)
        await self.session.commit()
        return result.output

    async def list_enabled_sources(
        self,
        category: ResearchSourceCategory | None = None,
    ) -> list[ResearchSource]:
        await self.ensure_defaults()
        statement = select(ResearchSource).where(
            ResearchSource.enabled.is_(True),
            ResearchSource.status != ResearchSourceStatus.DISABLED,
        )
        if category is not None:
            statement = statement.where(ResearchSource.category == category)
        result = await self.session.execute(statement.order_by(ResearchSource.priority.asc()))
        return list(result.scalars().all())

    @staticmethod
    def is_enabled_for_research(source: object) -> bool:
        return bool(getattr(source, "enabled", False)) and getattr(
            source,
            "status",
            None,
        ) != ResearchSourceStatus.DISABLED

    async def ensure_defaults(self) -> None:
        result = await self.session.execute(select(ResearchSource))
        sources = list(result.scalars().all())
        changed = False

        for source in sources:
            encrypted_config, migrated = self.config_service.encrypted_config(source.config_json)
            if migrated:
                source.config_json = encrypted_config
                changed = True

        for default in RESEARCH_SOURCE_DEFAULTS:
            existing_source = next(
                (source for source in sources if source.key == default.key),
                None,
            )
            if existing_source is not None:
                if self._sync_existing_default(existing_source, default):
                    changed = True
                continue
            self.session.add(
                ResearchSource(
                    key=default.key,
                    name=default.name,
                    provider_type=default.provider_type,
                    category=default.category,
                    enabled=default.enabled,
                    critical=default.critical,
                    priority=default.priority,
                    status=default.status,
                    quota_status=default.quota_status,
                    config_json=default.config_json,
                )
            )
            changed = True

        if changed:
            await self.session.flush()
            await self.session.commit()

    def _sync_existing_default(
        self,
        source: ResearchSource,
        default: ResearchSourceDefault,
    ) -> bool:
        changed = False
        if (
            source.key in FALLBACK_PRIORITY_MIGRATIONS
            and source.priority == FALLBACK_PRIORITY_MIGRATIONS[source.key]
            and source.priority != default.priority
        ):
            source.priority = default.priority
            changed = True

        if source.key != "grok_x":
            return changed
        config = dict(source.config_json or {})
        if config.get("llm_fallback_integration") is True:
            return changed

        source.name = default.name
        source.category = default.category
        source.enabled = default.enabled
        source.critical = default.critical
        source.priority = default.priority
        source.status = default.status
        source.quota_status = default.quota_status
        source.last_failure_reason = None
        source.config_json = {
            **config,
            "mode": default.config_json.get("mode", "api"),
            "requires_api_key": True,
            "secret_configured": bool(config.get("secret_configured")),
            "llm_fallback_integration": True,
        }
        return True

    def _filtered_statement(
        self,
        *,
        category: ResearchSourceCategory | None,
        status_filter: ResearchSourceStatus | None,
        enabled: bool | None,
        search: str | None,
    ):
        statement = select(ResearchSource)
        if category is not None:
            statement = statement.where(ResearchSource.category == category)
        if status_filter is not None:
            statement = statement.where(ResearchSource.status == status_filter)
        if enabled is not None:
            statement = statement.where(ResearchSource.enabled.is_(enabled))
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    ResearchSource.name.ilike(pattern),
                    ResearchSource.key.ilike(pattern),
                    ResearchSource.quota_status.ilike(pattern),
                )
            )
        return statement

    def _order_by(self, sort: str):
        return {
            "priority": (ResearchSource.priority.asc(), ResearchSource.name.asc()),
            "-priority": (ResearchSource.priority.desc(), ResearchSource.name.asc()),
            "name": (ResearchSource.name.asc(),),
            "-name": (ResearchSource.name.desc(),),
            "status": (ResearchSource.status.asc(), ResearchSource.priority.asc()),
            "-status": (ResearchSource.status.desc(), ResearchSource.priority.asc()),
            "last_checked_at": (
                ResearchSource.last_checked_at.desc().nullslast(),
                ResearchSource.priority.asc(),
            ),
            "-last_checked_at": (
                ResearchSource.last_checked_at.desc().nullslast(),
                ResearchSource.priority.asc(),
            ),
            "updated_at": (ResearchSource.updated_at.desc(), ResearchSource.priority.asc()),
            "-updated_at": (ResearchSource.updated_at.desc(), ResearchSource.priority.asc()),
        }.get(sort, (ResearchSource.priority.asc(), ResearchSource.name.asc()))

    async def _get_source(self, source_id: UUID) -> ResearchSource:
        source = await self.session.get(ResearchSource, source_id)
        if source is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Research source not found",
            )
        return source

    def _source_response(
        self,
        source: ResearchSource,
        usage_metrics: dict[str, object] | None = None,
    ) -> dict[str, object]:
        provider_mode = self.credential_provider.provider_mode(
            source.provider_type,
            source.config_json,
        )
        missing_configuration = self.credential_provider.missing_configuration(
            source.provider_type,
            source.config_json,
        )
        return {
            "id": source.id,
            "key": source.key,
            "name": source.name,
            "provider_type": source.provider_type,
            "category": source.category,
            "enabled": source.enabled,
            "critical": source.critical,
            "priority": source.priority,
            "status": source.status,
            "quota_status": source.quota_status,
            "last_checked_at": source.last_checked_at,
            "last_failure_reason": source.last_failure_reason,
            "documents_fetched_today": source.documents_fetched_today,
            "success_rate": source.success_rate,
            "average_latency_ms": source.average_latency_ms,
            "recent_failure_count": source.recent_failure_count,
            "config_json": self.config_service.redact_config(source.config_json),
            "provider_mode": provider_mode.value,
            "missing_configuration": missing_configuration,
            "configuration_status": self.credential_provider.safe_configuration_status(
                source.provider_type,
                source.config_json,
            ),
            "connection_status": source.status.value,
            "last_test_result": source.last_failure_reason
            or ("Not tested" if source.last_checked_at is None else source.status.value),
            "trend_provider_status": self._trend_provider_status(source),
            "total_runs": int((usage_metrics or {}).get("total_runs") or 0),
            "last_run_at": (usage_metrics or {}).get("last_run_at"),
            "documents_collected": int((usage_metrics or {}).get("documents_collected") or 0),
            "average_composite_score": int(
                (usage_metrics or {}).get("average_composite_score") or 0
            ),
            "average_trend_score": int((usage_metrics or {}).get("average_trend_score") or 0),
            "confidence_distribution": (usage_metrics or {}).get(
                "confidence_distribution"
            )
            or {"High": 0, "Medium": 0, "Low": 0, "Weak": 0},
            "created_at": source.created_at,
            "updated_at": source.updated_at,
        }

    def _trend_provider_status(self, source: ResearchSource) -> str | None:
        if source.provider_type == ResearchSourceProviderType.SERPAPI:
            if self.credential_provider.missing_configuration(
                source.provider_type,
                source.config_json,
            ):
                return "fallback_to_pytrends"
            if source.status == ResearchSourceStatus.FAILED:
                return "fallback_to_pytrends"
            return "primary"
        if source.provider_type == ResearchSourceProviderType.PYTRENDS:
            return "fallback"
        return None
