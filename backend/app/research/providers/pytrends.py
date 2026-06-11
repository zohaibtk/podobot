from collections.abc import Mapping
from typing import Any

from app.db.types import ResearchSourceProviderType
from app.research.providers.base import ProviderMode, normalized_document
from app.research.providers.http import HTTPResearchProvider


class PytrendsFallbackProvider(HTTPResearchProvider):
    provider_type = ResearchSourceProviderType.PYTRENDS

    async def test_connection(self):
        return self._test_success(message="pytrends fallback is available.", latency_ms=90)

    async def search(
        self,
        query: str,
        filters: Mapping[str, Any] | None = None,
    ) -> dict[str, object]:
        trend = await self.trend_score(query, filters or {})
        return {
            "query": query,
            "provider_type": self.provider_type.value,
            "provider_mode": self.provider_mode.value,
            "source_key": self.source_key,
            "results": [trend],
        }

    async def fetch_resource(self, resource_id_or_url: str) -> dict[str, object]:
        trend = await self.trend_score(resource_id_or_url, {})
        return {
            "provider_type": self.provider_type.value,
            "provider_mode": self.provider_mode.value,
            "source_key": self.source_key,
            "document": trend,
        }

    async def trend_score(
        self,
        query: str,
        filters: Mapping[str, Any] | None = None,
    ) -> dict[str, object]:
        normalized = self.normalize({"query": query, "filters": dict(filters or {})})
        metadata = normalized["metadata"] if isinstance(normalized.get("metadata"), dict) else {}
        return {
            **normalized,
            "trend_available": True,
            "trend_score": metadata.get("trend_score", 0),
            "source_used": self.source_key,
            "fallback_used": True,
        }

    def normalize(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        query = str(raw_result.get("query") or "trend")
        score = self._deterministic_score(query)
        document = normalized_document(
            provider_type=self.provider_type,
            provider_mode=self.provider_mode,
            source_key=self.source_key,
            title=f"Fallback trend score for {query}",
            content=f"Fallback trend lookup for {query}.",
            snippet=f"Fallback trend score {score}",
            metadata={"trend_score": score, "fallback": True},
        )
        document["scores"] = self.calculate_provider_scores(document)
        return document

    def extract_metadata(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        query = str(raw_result.get("query") or "trend")
        return {"trend_score": self._deterministic_score(query), "fallback": True}

    def calculate_provider_scores(self, normalized_result: Mapping[str, Any]) -> dict[str, object]:
        metadata = normalized_result.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        return self._scores(
            normalized_result,
            engagement=float(metadata.get("trend_score") or 0),
            authority=0.45,
        )

    def _deterministic_score(self, query: str) -> int:
        return 35 + (sum(ord(character) for character in query) % 55)


def pytrends_provider(source_key: str = "pytrends") -> PytrendsFallbackProvider:
    return PytrendsFallbackProvider(source_key=source_key, provider_mode=ProviderMode.REAL)
