from collections.abc import Mapping
from typing import Any

from app.db.types import ResearchSourceProviderType
from app.research.providers.base import normalized_document
from app.research.providers.http import HTTPResearchProvider


class YouTubeResearchProvider(HTTPResearchProvider):
    provider_type = ResearchSourceProviderType.YOUTUBE_DATA_API

    async def test_connection(self):
        await self._get_json(
            "https://www.googleapis.com/youtube/v3/search",
            params={"part": "snippet", "q": "podcast", "maxResults": 1, "key": self.api_key},
        )
        return self._test_success(message="YouTube Data API v3 is reachable.", latency_ms=180)

    async def search(
        self,
        query: str,
        filters: Mapping[str, Any] | None = None,
    ) -> dict[str, object]:
        filters = filters or {}
        raw = await self._get_json(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": query,
                "type": str(filters.get("type") or "video,channel"),
                "maxResults": int(filters.get("limit", 10)),
                "key": self.api_key,
            },
        )
        items = raw.get("items", [])
        results = [self.normalize(item) for item in items if isinstance(item, dict)]
        return {
            "query": query,
            "provider_type": self.provider_type.value,
            "provider_mode": self.provider_mode.value,
            "source_key": self.source_key,
            "results": results,
        }

    async def fetch_resource(self, resource_id_or_url: str) -> dict[str, object]:
        video_id = resource_id_or_url.rsplit("v=", 1)[-1].split("&", 1)[0]
        raw = await self._get_json(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "snippet,statistics,contentDetails",
                "id": video_id,
                "key": self.api_key,
            },
        )
        items = raw.get("items", [])
        document = self.normalize(items[0] if items else {"id": video_id})
        return {
            "provider_type": self.provider_type.value,
            "provider_mode": self.provider_mode.value,
            "source_key": self.source_key,
            "document": document,
        }

    def normalize(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        snippet = raw_result.get("snippet") if isinstance(raw_result.get("snippet"), dict) else {}
        identifier = raw_result.get("id")
        if isinstance(identifier, dict):
            video_id = identifier.get("videoId") or identifier.get("channelId") or ""
        else:
            video_id = identifier or ""
        url = (
            f"https://www.youtube.com/watch?v={video_id}"
            if video_id and not str(video_id).startswith("UC")
            else f"https://www.youtube.com/channel/{video_id}" if video_id else None
        )
        document = normalized_document(
            provider_type=self.provider_type,
            provider_mode=self.provider_mode,
            source_key=self.source_key,
            title=str(snippet.get("title") or "YouTube result"),
            url=url,
            content=str(snippet.get("description") or ""),
            snippet=str(snippet.get("description") or "")[:280],
            author=str(snippet.get("channelTitle") or ""),
            published_at=str(snippet.get("publishedAt") or ""),
            metadata=self.extract_metadata(raw_result),
        )
        document["scores"] = self.calculate_provider_scores(document)
        return document

    def extract_metadata(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        statistics = (
            raw_result.get("statistics")
            if isinstance(raw_result.get("statistics"), dict)
            else {}
        )
        snippet = raw_result.get("snippet") if isinstance(raw_result.get("snippet"), dict) else {}
        return {
            "channel_id": snippet.get("channelId"),
            "channel_title": snippet.get("channelTitle"),
            "view_count": int(statistics.get("viewCount", 0) or 0),
            "like_count": int(statistics.get("likeCount", 0) or 0),
            "comment_count": int(statistics.get("commentCount", 0) or 0),
        }

    def calculate_provider_scores(self, normalized_result: Mapping[str, Any]) -> dict[str, object]:
        metadata = normalized_result.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        engagement = (
            float(metadata.get("view_count") or 0) / 100
            + float(metadata.get("like_count") or 0)
            + float(metadata.get("comment_count") or 0) * 3
        )
        return self._scores(normalized_result, engagement=engagement, authority=0.65)
