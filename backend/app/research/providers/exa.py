from collections.abc import Mapping
from typing import Any

from app.db.types import ResearchSourceProviderType
from app.research.providers.base import normalized_document
from app.research.providers.http import HTTPResearchProvider


class ExaResearchProvider(HTTPResearchProvider):
    provider_type = ResearchSourceProviderType.EXA

    async def test_connection(self):
        await self._post_json(
            "https://api.exa.ai/search",
            json_body={"query": "podcast research", "numResults": 1},
            headers=self._headers(),
        )
        return self._test_success(message="Exa is reachable.", latency_ms=220)

    async def search(
        self,
        query: str,
        filters: Mapping[str, Any] | None = None,
    ) -> dict[str, object]:
        filters = filters or {}
        include_domains = filters.get("include_domains")
        body: dict[str, object] = {
            "query": query,
            "numResults": int(filters.get("limit", 10)),
            "contents": {"text": True, "summary": True},
        }
        if include_domains:
            body["includeDomains"] = include_domains
        if filters.get("category") == "substack":
            body["includeDomains"] = ["substack.com"]
        raw = await self._post_json(
            "https://api.exa.ai/search",
            json_body=body,
            headers=self._headers(),
        )
        results_raw = raw.get("results", [])
        results = [self.normalize(item) for item in results_raw if isinstance(item, dict)]
        return {
            "query": query,
            "provider_type": self.provider_type.value,
            "provider_mode": self.provider_mode.value,
            "source_key": self.source_key,
            "results": results,
        }

    async def fetch_resource(self, resource_id_or_url: str) -> dict[str, object]:
        raw = await self._post_json(
            "https://api.exa.ai/contents",
            json_body={"urls": [resource_id_or_url], "text": True, "summary": True},
            headers=self._headers(),
        )
        results = raw.get("results", [])
        document = self.normalize(results[0] if results else {"url": resource_id_or_url})
        return {
            "provider_type": self.provider_type.value,
            "provider_mode": self.provider_mode.value,
            "source_key": self.source_key,
            "document": document,
        }

    def normalize(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        content = str(raw_result.get("text") or raw_result.get("summary") or "")
        document = normalized_document(
            provider_type=self.provider_type,
            provider_mode=self.provider_mode,
            source_key=self.source_key,
            title=str(raw_result.get("title") or raw_result.get("url") or "Exa result"),
            url=str(raw_result.get("url") or ""),
            content=content,
            snippet=str(raw_result.get("summary") or content)[:280],
            author=str(raw_result.get("author") or ""),
            published_at=str(raw_result.get("publishedDate") or ""),
            metadata=self.extract_metadata(raw_result),
        )
        document["scores"] = self.calculate_provider_scores(document)
        return document

    def extract_metadata(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        return {
            "id": raw_result.get("id"),
            "score": raw_result.get("score", 0),
            "domain": raw_result.get("domain"),
        }

    def calculate_provider_scores(self, normalized_result: Mapping[str, Any]) -> dict[str, object]:
        metadata = normalized_result.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        return self._scores(
            normalized_result,
            engagement=float(metadata.get("score") or 0) * 100,
            authority=0.72,
        )

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}
