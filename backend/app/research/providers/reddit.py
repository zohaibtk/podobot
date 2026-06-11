from collections.abc import Mapping
from typing import Any

from app.db.types import ResearchSourceProviderType
from app.research.providers.base import normalized_document
from app.research.providers.http import HTTPResearchProvider


class RedditResearchProvider(HTTPResearchProvider):
    provider_type = ResearchSourceProviderType.REDDIT_JSON

    async def test_connection(self):
        await self._get_json(
            "https://www.reddit.com/search.json",
            params={"q": "podcast", "limit": 1},
        )
        return self._test_success(message="Reddit JSON is reachable.", latency_ms=140)

    async def search(
        self,
        query: str,
        filters: Mapping[str, Any] | None = None,
    ) -> dict[str, object]:
        filters = filters or {}
        subreddit = str(filters.get("subreddit") or "").strip().strip("/")
        url = (
            f"https://www.reddit.com/r/{subreddit}/search.json"
            if subreddit
            else "https://www.reddit.com/search.json"
        )
        raw = await self._get_json(
            url,
            params={
                "q": query,
                "limit": int(filters.get("limit", 10)),
                "restrict_sr": "on" if subreddit else "off",
                "sort": str(filters.get("sort", "relevance")),
            },
            headers={"User-Agent": "PodoBotResearch/1.0"},
        )
        children = (
            raw.get("data", {}).get("children", [])
            if isinstance(raw.get("data"), dict)
            else []
        )
        results = [
            self.normalize(item.get("data", item))
            for item in children
            if isinstance(item, dict)
        ]
        return self._search_payload(query, results)

    async def fetch_resource(self, resource_id_or_url: str) -> dict[str, object]:
        url = resource_id_or_url
        if not url.endswith(".json"):
            url = f"{url.rstrip('/')}.json"
        raw = await self._get_json(url, headers={"User-Agent": "PodoBotResearch/1.0"})
        first = raw[0] if isinstance(raw, list) and raw else raw
        document = self.normalize(first.get("data", first) if isinstance(first, dict) else {})
        return self._document_payload(document)

    def normalize(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        metadata = self.extract_metadata(raw_result)
        document = normalized_document(
            provider_type=self.provider_type,
            provider_mode=self.provider_mode,
            source_key=self.source_key,
            title=str(
                raw_result.get("title")
                or raw_result.get("link_title")
                or "Reddit discussion"
            ),
            url=self._url(raw_result),
            content=str(raw_result.get("selftext") or raw_result.get("body") or ""),
            snippet=str(raw_result.get("selftext") or raw_result.get("body") or "")[:280],
            author=str(raw_result.get("author") or ""),
            published_at=str(raw_result.get("created_utc") or ""),
            metadata=metadata,
        )
        document["scores"] = self.calculate_provider_scores(document)
        return document

    def extract_metadata(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        return {
            "subreddit": raw_result.get("subreddit"),
            "score": raw_result.get("score", 0),
            "num_comments": raw_result.get("num_comments", 0),
            "upvote_ratio": raw_result.get("upvote_ratio"),
        }

    def calculate_provider_scores(self, normalized_result: Mapping[str, Any]) -> dict[str, object]:
        metadata = normalized_result.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        engagement = (
            float(metadata.get("score") or 0)
            + float(metadata.get("num_comments") or 0) * 2
        )
        return self._scores(normalized_result, engagement=engagement, authority=0.58)

    def _url(self, raw_result: Mapping[str, Any]) -> str:
        permalink = raw_result.get("permalink")
        if permalink:
            return f"https://www.reddit.com{permalink}"
        return str(raw_result.get("url") or "")

    def _search_payload(self, query: str, results: list[dict[str, object]]) -> dict[str, object]:
        return {
            "query": query,
            "provider_type": self.provider_type.value,
            "provider_mode": self.provider_mode.value,
            "source_key": self.source_key,
            "results": results,
        }

    def _document_payload(self, document: dict[str, object]) -> dict[str, object]:
        return {
            "provider_type": self.provider_type.value,
            "provider_mode": self.provider_mode.value,
            "source_key": self.source_key,
            "document": document,
        }
