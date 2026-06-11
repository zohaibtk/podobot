from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.types import (
    DiscoveryLedgerType,
    ResearchRunSourceUsageStatus,
    ResearchRunType,
    ResearchSourceCategory,
    ResearchSourceProviderType,
    ResearchSourceStatus,
)
from app.modules.research.service import ResearchPersistenceService
from app.modules.research_sources.models import ResearchSource
from app.modules.research_sources.service import ResearchSourceService
from app.research.providers.base import ProviderMode, ProviderTestResult, ResearchProvider
from app.research.providers.credentials import ResearchCredentialProvider
from app.research.providers.exa import ExaResearchProvider
from app.research.providers.firecrawl import FirecrawlScrapingProvider
from app.research.providers.gemini import GeminiResearchClassifierProvider
from app.research.providers.grok import GrokResearchProvider
from app.research.providers.groq import GroqResearchProvider
from app.research.providers.hn import HackerNewsAlgoliaResearchProvider
from app.research.providers.openai import OpenAIResearchProvider
from app.research.providers.pytrends import PytrendsFallbackProvider
from app.research.providers.reddit import RedditResearchProvider
from app.research.providers.serpapi import SerpApiTrendsProvider
from app.research.providers.youtube import YouTubeResearchProvider


@dataclass(frozen=True)
class ProviderExecutionResult:
    output: dict[str, object]
    metadata: dict[str, object]


REAL_PROVIDER_CLASSES = {
    ResearchSourceProviderType.REDDIT_JSON: RedditResearchProvider,
    ResearchSourceProviderType.HN_ALGOLIA: HackerNewsAlgoliaResearchProvider,
    ResearchSourceProviderType.YOUTUBE_DATA_API: YouTubeResearchProvider,
    ResearchSourceProviderType.EXA: ExaResearchProvider,
    ResearchSourceProviderType.FIRECRAWL: FirecrawlScrapingProvider,
    ResearchSourceProviderType.SERPAPI: SerpApiTrendsProvider,
    ResearchSourceProviderType.PYTRENDS: PytrendsFallbackProvider,
    ResearchSourceProviderType.OPENAI: OpenAIResearchProvider,
    ResearchSourceProviderType.GEMINI: GeminiResearchClassifierProvider,
    ResearchSourceProviderType.GROK_X: GrokResearchProvider,
    ResearchSourceProviderType.GROQ: GroqResearchProvider,
}


class ResearchProviderRegistry:
    def __init__(
        self,
        session: AsyncSession,
        credential_provider: ResearchCredentialProvider | None = None,
    ) -> None:
        self.session = session
        self.credential_provider = credential_provider or ResearchCredentialProvider()
        self.source_service = ResearchSourceService(session)

    async def list_enabled_sources(self) -> list[dict[str, object]]:
        sources = await self.source_service.list_enabled_sources()
        return [self.source_payload(source) for source in sources]

    async def test_source_connection(self, source_key: str) -> ProviderExecutionResult:
        source = await self.resolve_source(source_key=source_key)
        provider = self.provider_for_source(source)
        started = perf_counter()
        try:
            result = await provider.test_connection()
        except Exception as exc:
            result = ProviderTestResult(
                success=False,
                status=ResearchSourceStatus.FAILED,
                message=safe_provider_error(exc),
                latency_ms=round((perf_counter() - started) * 1000),
                quota_status="failed",
                provider_mode=provider.provider_mode,
                missing_configuration=self.credential_provider.missing_configuration(
                    source.provider_type,
                    self._source_config(source),
                ),
            )
        execution_ms = result.latency_ms or round((perf_counter() - started) * 1000)
        self.apply_health_result(source, result, execution_ms)
        output = {
            "source": self.source_payload(source),
            "success": result.success,
            "message": result.message,
        }
        return ProviderExecutionResult(
            output=output,
            metadata=self.execution_metadata(
                source=source,
                provider=provider,
                success=result.success,
                execution_time_ms=execution_ms,
            ),
        )

    async def search_sources(
        self,
        *,
        query: str,
        filters: Mapping[str, Any] | None = None,
        source_key: str | None = None,
        provider_type: ResearchSourceProviderType | None = None,
        category: ResearchSourceCategory | None = None,
    ) -> ProviderExecutionResult:
        filters = filters or {}
        sources = await self._execution_sources(
            source_key=source_key,
            provider_type=provider_type,
            category=category or ResearchSourceCategory.DISCOVERY,
        )
        persistence = ResearchPersistenceService(self.session)
        run = await persistence.start_run(
            run_type=self._research_run_type(filters, ResearchRunType.DISCOVERY),
            query_text=query,
            series_id=self._context_uuid(filters, "series_id"),
            episode_id=self._context_uuid(filters, "episode_id"),
            strategy_run_id=self._context_uuid(filters, "strategy_run_id"),
            agent_run_id=self._context_uuid(filters, "agent_run_id"),
            initiated_by_user_id=self._context_uuid(filters, "initiated_by_user_id"),
            metadata_json={
                "filters": dict(filters),
                "source_key": source_key,
                "provider_type": provider_type.value if provider_type else None,
                "category": (category or ResearchSourceCategory.DISCOVERY).value,
            },
            enabled_source_count=len(sources),
        )
        started = perf_counter()
        all_results: list[dict[str, object]] = []
        provider_summaries: list[dict[str, object]] = []
        for source in sources:
            source_started = datetime.now(UTC)
            provider_started = perf_counter()
            if not self._source_is_enabled(source):
                await persistence.record_source_usage(
                    run=run,
                    source=source,
                    status_value=ResearchRunSourceUsageStatus.SKIPPED_DISABLED,
                    query_text=query,
                    failure_reason=f"{source.name} is disabled.",
                    started_at=source_started,
                )
                provider_summaries.append(
                    {
                        "source_key": source.key,
                        "provider_type": source.provider_type.value,
                        "provider_mode": "disabled",
                        "result_count": 0,
                        "status": ResearchRunSourceUsageStatus.SKIPPED_DISABLED.value,
                    }
                )
                continue
            provider = self.provider_for_source(source)
            try:
                provider_output = await provider.search(query, filters)
            except Exception as exc:
                latency_ms = round((perf_counter() - provider_started) * 1000)
                reason = safe_provider_error(exc)
                await persistence.record_source_usage(
                    run=run,
                    source=source,
                    status_value=ResearchRunSourceUsageStatus.FAILED,
                    query_text=query,
                    latency_ms=latency_ms,
                    failure_reason=reason,
                    started_at=source_started,
                )
                provider_summaries.append(
                    {
                        "source_key": source.key,
                        "provider_type": source.provider_type.value,
                        "provider_mode": provider.provider_mode.value,
                        "result_count": 0,
                        "status": ResearchRunSourceUsageStatus.FAILED.value,
                        "failure_reason": reason,
                    }
                )
                continue
            latency_ms = round((perf_counter() - provider_started) * 1000)
            results = provider_output.get("results", [])
            normalized_results = [item for item in results if isinstance(item, dict)]
            if isinstance(results, list):
                all_results.extend(normalized_results)
            usage_status = (
                ResearchRunSourceUsageStatus.USED
                if normalized_results
                else ResearchRunSourceUsageStatus.NO_RESULTS
            )
            for document in normalized_results:
                await persistence.persist_document(
                    run=run,
                    source=source,
                    document=document,
                    used_in_output=True,
                    ledger_type=self._ledger_type(filters),
                    series_id=self._context_uuid(filters, "series_id"),
                    episode_id=self._context_uuid(filters, "episode_id"),
                    strategy_idea_id=self._context_uuid(filters, "strategy_idea_id"),
                )
            await persistence.record_source_usage(
                run=run,
                source=source,
                status_value=usage_status,
                query_text=query,
                documents_found=len(normalized_results),
                documents_used=len(normalized_results),
                latency_ms=latency_ms,
                started_at=source_started,
            )
            provider_summaries.append(
                {
                    "source_key": source.key,
                    "provider_type": source.provider_type.value,
                    "provider_mode": provider.provider_mode.value,
                    "result_count": len(normalized_results),
                    "status": usage_status.value,
                }
            )
        execution_ms = round((perf_counter() - started) * 1000)
        await persistence.complete_run(run)
        return ProviderExecutionResult(
            output={
                "query": query,
                "results": all_results,
                "sources": all_results,
                "provider_summaries": provider_summaries,
            },
            metadata={
                "provider_count": len(provider_summaries),
                "providers": provider_summaries,
                "execution_time_ms": execution_ms,
                "research_run_id": str(run.id),
            },
        )

    async def fetch_resource(
        self,
        *,
        resource_id_or_url: str,
        source_key: str | None = None,
        provider_type: ResearchSourceProviderType | None = None,
    ) -> ProviderExecutionResult:
        source = await self._single_source(
            source_key=source_key,
            provider_type=provider_type,
            fallback_category=ResearchSourceCategory.DISCOVERY,
        )
        provider = self.provider_for_source(source)
        persistence = ResearchPersistenceService(self.session)
        run = await persistence.start_run(
            run_type=ResearchRunType.MANUAL_RESEARCH,
            query_text=resource_id_or_url,
            metadata_json={
                "resource_id_or_url": resource_id_or_url,
                "source_key": source_key,
                "provider_type": provider_type.value if provider_type else None,
            },
            enabled_source_count=1,
        )
        started = perf_counter()
        source_started = datetime.now(UTC)
        try:
            output = await provider.fetch_resource(resource_id_or_url)
        except Exception as exc:
            execution_ms = round((perf_counter() - started) * 1000)
            reason = safe_provider_error(exc)
            await persistence.record_source_usage(
                run=run,
                source=source,
                status_value=ResearchRunSourceUsageStatus.FAILED,
                query_text=resource_id_or_url,
                latency_ms=execution_ms,
                failure_reason=reason,
                started_at=source_started,
            )
            await persistence.fail_run(run, failure_reason=reason)
            raise
        execution_ms = round((perf_counter() - started) * 1000)
        document = output.get("document")
        document_count = 0
        if isinstance(document, dict):
            await persistence.persist_document(
                run=run,
                source=source,
                document=document,
                used_in_output=True,
                ledger_type=DiscoveryLedgerType.SOURCE,
            )
            document_count = 1
        await persistence.record_source_usage(
            run=run,
            source=source,
            status_value=(
                ResearchRunSourceUsageStatus.USED
                if document_count
                else ResearchRunSourceUsageStatus.NO_RESULTS
            ),
            query_text=resource_id_or_url,
            documents_found=document_count,
            documents_used=document_count,
            latency_ms=execution_ms,
            started_at=source_started,
        )
        await persistence.complete_run(run)
        return ProviderExecutionResult(
            output=output,
            metadata={
                **self.execution_metadata(
                    source=source,
                    provider=provider,
                    success=True,
                    execution_time_ms=execution_ms,
                ),
                "research_run_id": str(run.id),
            },
        )

    async def scrape_resource(self, *, url: str) -> ProviderExecutionResult:
        return await self.fetch_resource(
            resource_id_or_url=url,
            provider_type=ResearchSourceProviderType.FIRECRAWL,
        )

    async def get_trend_score(
        self,
        *,
        query: str,
        filters: Mapping[str, Any] | None = None,
    ) -> ProviderExecutionResult:
        filters = filters or {}
        started = perf_counter()
        serpapi = await self._source_by_provider_type(ResearchSourceProviderType.SERPAPI)
        pytrends = await self._source_by_provider_type(ResearchSourceProviderType.PYTRENDS)
        fallback_used = False
        source_used: ResearchSource | None = None
        provider_used: ResearchProvider | None = None
        output: dict[str, object] | None = None
        failure_messages: list[str] = []

        if serpapi and self._can_attempt_serpapi(serpapi):
            try:
                provider_used = self.provider_for_source(serpapi)
                source_used = serpapi
                output = await provider_used.search(query, filters)
                result = (
                    (output.get("results") or [None])[0]
                    if isinstance(output.get("results"), list)
                    else None
                )
                if isinstance(result, dict):
                    output = {
                        "trend_available": True,
                        "query": query,
                        "score": result.get("trend_score", 0),
                        "source_used": serpapi.key,
                        "fallback_used": False,
                        "result": result,
                    }
            except Exception as exc:
                failure_messages.append(safe_provider_error(exc))

        if output is None and pytrends and self._source_is_enabled(pytrends):
            try:
                fallback_used = True
                provider_used = self.provider_for_source(pytrends)
                source_used = pytrends
                pytrends_output = await provider_used.search(query, filters)
                result = (
                    (pytrends_output.get("results") or [None])[0]
                    if isinstance(pytrends_output.get("results"), list)
                    else None
                )
                if isinstance(result, dict):
                    output = {
                        "trend_available": True,
                        "query": query,
                        "score": result.get("trend_score", 0),
                        "source_used": pytrends.key,
                        "fallback_used": True,
                        "result": result,
                    }
            except Exception as exc:
                failure_messages.append(safe_provider_error(exc))

        execution_ms = round((perf_counter() - started) * 1000)
        if output is None:
            output = {
                "trend_available": False,
                "query": query,
                "message": "Trend not available",
                "fallback_used": fallback_used,
                "failures": failure_messages,
            }
        if getattr(self, "session", None) is None:
            return ProviderExecutionResult(
                output=output,
                metadata={
                    "source_key": source_used.key if source_used else None,
                    "provider_type": source_used.provider_type.value if source_used else None,
                    "provider_mode": provider_used.provider_mode.value if provider_used else None,
                    "execution_time_ms": execution_ms,
                    "fallback_used": fallback_used,
                    "success": bool(output.get("trend_available")),
                },
            )
        persistence = ResearchPersistenceService(self.session)
        run = await persistence.start_run(
            run_type=ResearchRunType.TOPIC_GENERATION,
            query_text=query,
            metadata_json={"filters": dict(filters), "fallback_used": fallback_used},
            enabled_source_count=len([source for source in (serpapi, pytrends) if source]),
        )
        if source_used is not None:
            result = output.get("result") if isinstance(output.get("result"), dict) else None
            if result is not None:
                await persistence.persist_document(
                    run=run,
                    source=source_used,
                    document=result,
                    used_in_output=True,
                    ledger_type=DiscoveryLedgerType.TOPIC_SUPPORT,
                )
            await persistence.record_source_usage(
                run=run,
                source=source_used,
                status_value=(
                    ResearchRunSourceUsageStatus.USED
                    if output.get("trend_available")
                    else ResearchRunSourceUsageStatus.NO_RESULTS
                ),
                query_text=query,
                documents_found=1 if result else 0,
                documents_used=1 if result else 0,
                latency_ms=execution_ms,
                started_at=datetime.now(UTC),
            )
            await persistence.complete_run(run)
        else:
            await persistence.fail_run(
                run,
                failure_reason=", ".join(failure_messages) or "Trend not available",
            )

        return ProviderExecutionResult(
            output=output,
            metadata={
                "source_key": source_used.key if source_used else None,
                "provider_type": source_used.provider_type.value if source_used else None,
                "provider_mode": provider_used.provider_mode.value if provider_used else None,
                "execution_time_ms": execution_ms,
                "fallback_used": fallback_used,
                "success": bool(output.get("trend_available")),
                "research_run_id": str(run.id),
            },
        )

    async def calculate_provider_scores(
        self,
        *,
        normalized_result: Mapping[str, Any],
        source_key: str | None = None,
        provider_type: ResearchSourceProviderType | None = None,
    ) -> ProviderExecutionResult:
        source = await self._single_source(
            source_key=source_key,
            provider_type=provider_type,
            fallback_category=ResearchSourceCategory.DISCOVERY,
        )
        provider = self.provider_for_source(source)
        started = perf_counter()
        scores = provider.calculate_provider_scores(normalized_result)
        execution_ms = round((perf_counter() - started) * 1000)
        return ProviderExecutionResult(
            output={
                "provider_type": source.provider_type.value,
                "provider_mode": provider.provider_mode.value,
                "source_key": source.key,
                "scores": scores,
            },
            metadata=self.execution_metadata(
                source=source,
                provider=provider,
                success=True,
                execution_time_ms=execution_ms,
            ),
        )

    def provider_for_source(self, source: ResearchSource) -> ResearchProvider:
        if not self._source_is_enabled(source):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Research source {source.key} is disabled.",
            )
        credential = self.credential_provider.credential_for(
            source.provider_type,
            self._source_config(source),
        )
        if not credential.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    f"{credential.env_name or 'Provider credentials'} must be configured before "
                    f"{source.name} can run."
                ),
            )
        provider_class = REAL_PROVIDER_CLASSES.get(source.provider_type)
        if provider_class is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported research provider type: {source.provider_type.value}",
            )
        return provider_class(
            source_key=source.key,
            provider_mode=ProviderMode.REAL,
            api_key=credential.value,
        )

    def source_payload(self, source: ResearchSource) -> dict[str, object]:
        provider_mode = self.credential_provider.provider_mode(
            source.provider_type,
            self._source_config(source),
        )
        missing_configuration = self.credential_provider.missing_configuration(
            source.provider_type,
            self._source_config(source),
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
            "config_json": self.source_service.config_service.redact_config(
                self._source_config(source)
            ),
            "provider_mode": provider_mode.value,
            "missing_configuration": missing_configuration,
            "configuration_status": self.credential_provider.safe_configuration_status(
                source.provider_type,
                self._source_config(source),
            ),
            "connection_status": source.status.value,
            "last_test_result": source.last_failure_reason
            or ("Not tested" if source.last_checked_at is None else source.status.value),
            "trend_provider_status": self._trend_provider_status(source),
            "created_at": source.created_at,
            "updated_at": source.updated_at,
        }

    def apply_health_result(
        self,
        source: ResearchSource,
        result: ProviderTestResult,
        execution_time_ms: int,
    ) -> None:
        source.status = result.status
        source.quota_status = result.quota_status
        source.last_checked_at = datetime.now(UTC)
        source.average_latency_ms = execution_time_ms
        source.success_rate = self._next_success_rate(source.success_rate, result.success)
        source.recent_failure_count = 0 if result.success else source.recent_failure_count + 1
        source.last_failure_reason = (
            result.message
            if result.status in {ResearchSourceStatus.FAILED, ResearchSourceStatus.WARNING}
            else None
        )

    async def resolve_source(
        self,
        *,
        source_key: str | None = None,
        source_id: UUID | None = None,
        provider_type: ResearchSourceProviderType | None = None,
    ) -> ResearchSource:
        await self.source_service.ensure_defaults()
        if source_id is not None:
            source = await self.session.get(ResearchSource, source_id)
        elif source_key:
            result = await self.session.execute(
                select(ResearchSource).where(ResearchSource.key == source_key)
            )
            source = result.scalar_one_or_none()
        elif provider_type is not None:
            source = await self._source_by_provider_type(provider_type)
        else:
            source = None
        if source is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Research source not found",
            )
        return source

    async def _execution_sources(
        self,
        *,
        source_key: str | None,
        provider_type: ResearchSourceProviderType | None,
        category: ResearchSourceCategory | None,
    ) -> list[ResearchSource]:
        if source_key or provider_type:
            return [
                await self.resolve_source(source_key=source_key, provider_type=provider_type)
            ]
        return await self.source_service.list_enabled_sources(category=category)

    async def _single_source(
        self,
        *,
        source_key: str | None,
        provider_type: ResearchSourceProviderType | None,
        fallback_category: ResearchSourceCategory,
    ) -> ResearchSource:
        if source_key or provider_type:
            return await self.resolve_source(source_key=source_key, provider_type=provider_type)
        sources = await self.source_service.list_enabled_sources(category=fallback_category)
        if not sources:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No enabled research source is available",
            )
        return sources[0]

    async def _source_by_provider_type(
        self,
        provider_type: ResearchSourceProviderType,
    ) -> ResearchSource | None:
        await self.source_service.ensure_defaults()
        result = await self.session.execute(
            select(ResearchSource).where(ResearchSource.provider_type == provider_type)
        )
        return result.scalar_one_or_none()

    def _can_attempt_serpapi(self, source: ResearchSource) -> bool:
        provider_mode = self.credential_provider.provider_mode(
            source.provider_type,
            self._source_config(source),
        )
        return (
            self._source_is_enabled(source)
            and source.status not in {ResearchSourceStatus.FAILED, ResearchSourceStatus.DISABLED}
            and provider_mode == ProviderMode.REAL
            and source.quota_status not in {"quota_exhausted", "disabled", "failed"}
        )

    def _source_is_enabled(self, source: ResearchSource) -> bool:
        return source.enabled and source.status != ResearchSourceStatus.DISABLED

    def _source_config(self, source: ResearchSource) -> Mapping[str, object] | None:
        config_json = getattr(source, "config_json", None)
        return config_json if isinstance(config_json, Mapping) else None

    def _next_success_rate(self, current_rate: float, success: bool) -> float:
        previous = max(0, min(float(current_rate or 0), 1))
        sample = 1.0 if success else 0.0
        return round((previous * 0.8) + (sample * 0.2), 4)

    def _research_run_type(
        self,
        filters: Mapping[str, Any],
        default: ResearchRunType,
    ) -> ResearchRunType:
        value = filters.get("run_type")
        if value in (None, ""):
            caller_context = filters.get("_caller_context")
            if isinstance(caller_context, Mapping):
                value = caller_context.get("workflow_stage")
        try:
            return ResearchRunType(str(value)) if value else default
        except ValueError:
            return default

    def _ledger_type(self, filters: Mapping[str, Any]) -> DiscoveryLedgerType:
        value = filters.get("ledger_type")
        try:
            return DiscoveryLedgerType(str(value)) if value else DiscoveryLedgerType.SOURCE
        except ValueError:
            return DiscoveryLedgerType.SOURCE

    def _context_uuid(self, filters: Mapping[str, Any], key: str) -> UUID | None:
        value = filters.get(key)
        if value in (None, ""):
            caller_context = filters.get("_caller_context")
            if isinstance(caller_context, Mapping):
                value = caller_context.get(key)
                if value in (None, "") and key == "initiated_by_user_id":
                    value = caller_context.get("caller_id")
        try:
            return UUID(str(value)) if value not in (None, "") else None
        except ValueError:
            return None

    def _trend_provider_status(self, source: ResearchSource) -> str | None:
        if source.provider_type == ResearchSourceProviderType.SERPAPI:
            if self.credential_provider.missing_configuration(
                source.provider_type,
                self._source_config(source),
            ):
                return "fallback_to_pytrends"
            if source.status == ResearchSourceStatus.FAILED:
                return "fallback_to_pytrends"
            return "primary"
        if source.provider_type == ResearchSourceProviderType.PYTRENDS:
            return "fallback"
        return None

    def execution_metadata(
        self,
        *,
        source: ResearchSource,
        provider: ResearchProvider,
        success: bool,
        execution_time_ms: int,
    ) -> dict[str, object]:
        return {
            "provider_used": source.provider_type.value,
            "provider_type": source.provider_type.value,
            "provider_mode": provider.provider_mode.value,
            "source_used": source.key,
            "source_key": source.key,
            "execution_time_ms": execution_time_ms,
            "success": success,
        }


def safe_provider_error(exc: Exception) -> str:
    detail = str(exc)
    if not detail:
        return "Provider request failed"
    sensitive_markers = ("key=", "api_key", "token", "secret", "authorization")
    lowered = detail.lower()
    if any(marker in lowered for marker in sensitive_markers):
        return "Provider request failed"
    return detail[:240]
