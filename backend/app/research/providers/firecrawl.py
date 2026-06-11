from collections.abc import Mapping
from typing import Any

from app.db.types import ResearchSourceProviderType
from app.research.providers.base import normalized_document
from app.research.providers.http import HTTPResearchProvider


class FirecrawlScrapingProvider(HTTPResearchProvider):
    provider_type = ResearchSourceProviderType.FIRECRAWL

    async def test_connection(self):
        return self._test_success(message="Firecrawl adapter is configured.", latency_ms=180)

    async def search(
        self,
        query: str,
        filters: Mapping[str, Any] | None = None,
    ) -> dict[str, object]:
        url = str((filters or {}).get("url") or query)
        fetched = await self.fetch_resource(url)
        return {
            "query": query,
            "provider_type": self.provider_type.value,
            "provider_mode": self.provider_mode.value,
            "source_key": self.source_key,
            "results": [fetched["document"]],
        }

    async def fetch_resource(self, resource_id_or_url: str) -> dict[str, object]:
        raw = await self._post_json(
            "https://api.firecrawl.dev/v1/scrape",
            json_body={"url": resource_id_or_url, "formats": ["markdown", "html"]},
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
        document = self.normalize(data if isinstance(data, dict) else {"url": resource_id_or_url})
        return {
            "provider_type": self.provider_type.value,
            "provider_mode": self.provider_mode.value,
            "source_key": self.source_key,
            "document": document,
        }

    def normalize(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        metadata = self.extract_metadata(raw_result)
        content = str(
            raw_result.get("markdown")
            or raw_result.get("content")
            or raw_result.get("html")
            or ""
        )
        title = str(
            metadata.get("title")
            or raw_result.get("title")
            or raw_result.get("url")
            or "Scraped page"
        )
        document = normalized_document(
            provider_type=self.provider_type,
            provider_mode=self.provider_mode,
            source_key=self.source_key,
            title=title,
            url=str(metadata.get("sourceURL") or raw_result.get("url") or ""),
            content=content,
            snippet=content[:280],
            metadata=metadata,
        )
        document["scores"] = self.calculate_provider_scores(document)
        return document

    def extract_metadata(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        metadata = (
            raw_result.get("metadata")
            if isinstance(raw_result.get("metadata"), dict)
            else {}
        )
        content = str(raw_result.get("markdown") or raw_result.get("content") or "")
        return {
            **metadata,
            "content_length": len(content),
        }

    def calculate_provider_scores(self, normalized_result: Mapping[str, Any]) -> dict[str, object]:
        return self._scores(normalized_result, engagement=0, authority=0.6)
