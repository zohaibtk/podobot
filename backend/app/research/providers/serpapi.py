from collections.abc import Mapping
from typing import Any

from app.db.types import ResearchSourceProviderType
from app.research.providers.base import normalized_document
from app.research.providers.http import HTTPResearchProvider


class SerpApiTrendsProvider(HTTPResearchProvider):
    provider_type = ResearchSourceProviderType.SERPAPI

    async def test_connection(self):
        await self._get_json(
            "https://serpapi.com/search.json",
            params={"engine": "google_trends", "q": "podcast", "api_key": self.api_key},
        )
        return self._test_success(message="SerpAPI trends are reachable.", latency_ms=180)

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
        filters = filters or {}
        raw = await self._get_json(
            "https://serpapi.com/search.json",
            params={
                "engine": "google_trends",
                "q": query,
                "date": str(filters.get("date") or "today 3-m"),
                "api_key": self.api_key,
            },
        )
        normalized = self.normalize({"query": query, **raw})
        metadata = normalized["metadata"] if isinstance(normalized.get("metadata"), dict) else {}
        return {
            **normalized,
            "trend_available": True,
            "trend_score": metadata.get("trend_score", 0),
            "source_used": self.source_key,
            "fallback_used": False,
        }

    def normalize(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        metadata = self.extract_metadata(raw_result)
        query = str(raw_result.get("query") or "trend")
        document = normalized_document(
            provider_type=self.provider_type,
            provider_mode=self.provider_mode,
            source_key=self.source_key,
            title=f"Trend score for {query}",
            url=None,
            content=f"Trend lookup for {query}.",
            snippet=f"Trend score {metadata.get('trend_score', 0)}",
            metadata=metadata,
        )
        document["scores"] = self.calculate_provider_scores(document)
        return document

    def extract_metadata(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        timeline = raw_result.get("interest_over_time")
        values: list[float] = []
        if isinstance(timeline, dict):
            for item in timeline.get("timeline_data", []):
                if isinstance(item, dict):
                    extracted = item.get("values", [])
                    if extracted and isinstance(extracted[0], dict):
                        values.append(float(extracted[0].get("extracted_value") or 0))
        score = round(sum(values) / len(values), 2) if values else 0
        return {
            "trend_score": score,
            "timeline_points": len(values),
            "quota_state": raw_result.get("search_metadata", {}).get("status")
            if isinstance(raw_result.get("search_metadata"), dict)
            else None,
        }

    def calculate_provider_scores(self, normalized_result: Mapping[str, Any]) -> dict[str, object]:
        metadata = normalized_result.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        return self._scores(
            normalized_result,
            engagement=float(metadata.get("trend_score") or 0),
            authority=0.7,
        )
