from collections.abc import Mapping
from typing import Any

from app.db.types import ResearchSourceProviderType
from app.research.providers.base import normalized_document
from app.research.providers.http import HTTPResearchProvider


class HackerNewsAlgoliaResearchProvider(HTTPResearchProvider):
    provider_type = ResearchSourceProviderType.HN_ALGOLIA

    async def test_connection(self):
        await self._get_json(
            "https://hn.algolia.com/api/v1/search",
            params={"query": "ai", "hitsPerPage": 1},
        )
        return self._test_success(message="HN Algolia is reachable.", latency_ms=120)

    async def search(
        self,
        query: str,
        filters: Mapping[str, Any] | None = None,
    ) -> dict[str, object]:
        filters = filters or {}
        endpoint = "search_by_date" if filters.get("sort") == "date" else "search"
        raw = await self._get_json(
            f"https://hn.algolia.com/api/v1/{endpoint}",
            params={"query": query, "hitsPerPage": int(filters.get("limit", 10))},
        )
        hits = raw.get("hits", [])
        results = [self.normalize(hit) for hit in hits if isinstance(hit, dict)]
        return {
            "query": query,
            "provider_type": self.provider_type.value,
            "provider_mode": self.provider_mode.value,
            "source_key": self.source_key,
            "results": results,
        }

    async def fetch_resource(self, resource_id_or_url: str) -> dict[str, object]:
        object_id = resource_id_or_url.rsplit("/", 1)[-1]
        raw = await self._get_json(f"https://hn.algolia.com/api/v1/items/{object_id}")
        document = self.normalize(raw)
        return {
            "provider_type": self.provider_type.value,
            "provider_mode": self.provider_mode.value,
            "source_key": self.source_key,
            "document": document,
        }

    def normalize(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        title = str(
            raw_result.get("title")
            or raw_result.get("story_title")
            or raw_result.get("text")
            or "HN result"
        )
        snippet = str(
            raw_result.get("comment_text")
            or raw_result.get("story_text")
            or raw_result.get("text")
            or ""
        )
        item_id = raw_result.get("objectID") or raw_result.get("id") or ""
        url = str(
            raw_result.get("url")
            or raw_result.get("story_url")
            or f"https://news.ycombinator.com/item?id={item_id}"
        )
        document = normalized_document(
            provider_type=self.provider_type,
            provider_mode=self.provider_mode,
            source_key=self.source_key,
            title=title,
            url=url,
            content=snippet,
            snippet=snippet[:280],
            author=str(raw_result.get("author") or ""),
            published_at=str(raw_result.get("created_at") or ""),
            metadata=self.extract_metadata(raw_result),
        )
        document["scores"] = self.calculate_provider_scores(document)
        return document

    def extract_metadata(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        return {
            "object_id": raw_result.get("objectID") or raw_result.get("id"),
            "points": raw_result.get("points", 0),
            "num_comments": raw_result.get("num_comments", 0),
            "tags": raw_result.get("_tags", []),
        }

    def calculate_provider_scores(self, normalized_result: Mapping[str, Any]) -> dict[str, object]:
        metadata = normalized_result.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        engagement = (
            float(metadata.get("points") or 0)
            + float(metadata.get("num_comments") or 0) * 1.5
        )
        return self._scores(normalized_result, engagement=engagement, authority=0.62)
