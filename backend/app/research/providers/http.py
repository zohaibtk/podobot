from collections.abc import Mapping
from typing import Any

import httpx

from app.db.types import ResearchSourceProviderType, ResearchSourceStatus
from app.research.providers.base import ProviderMode, ProviderTestResult


class HTTPResearchProvider:
    provider_type: ResearchSourceProviderType

    def __init__(
        self,
        *,
        source_key: str,
        provider_mode: ProviderMode = ProviderMode.REAL,
        api_key: str | None = None,
        timeout_seconds: int = 20,
    ) -> None:
        self.source_key = source_key
        self.provider_mode = provider_mode
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def _get_json(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, object]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(
                    f"Provider request failed with status {exc.response.status_code}"
                ) from exc
            except httpx.HTTPError as exc:
                raise RuntimeError("Provider request failed") from exc

    async def _post_json(
        self,
        url: str,
        *,
        json_body: Mapping[str, Any],
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, object]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.post(url, params=params, headers=headers, json=json_body)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(
                    f"Provider request failed with status {exc.response.status_code}"
                ) from exc
            except httpx.HTTPError as exc:
                raise RuntimeError("Provider request failed") from exc

    def _scores(
        self,
        normalized_result: Mapping[str, Any],
        *,
        engagement: float = 0,
        authority: float = 0.5,
    ) -> dict[str, object]:
        content = str(normalized_result.get("content") or normalized_result.get("snippet") or "")
        return {
            "engagement": round(max(0, engagement), 3),
            "authority": round(max(0, min(authority, 1)), 3),
            "content_depth": min(len(content), 5000),
            "freshness_hint": normalized_result.get("published_at"),
        }

    def _test_success(self, *, message: str, latency_ms: int = 120) -> ProviderTestResult:
        return ProviderTestResult(
            success=True,
            status=ResearchSourceStatus.HEALTHY,
            message=message,
            latency_ms=latency_ms,
            quota_status="available",
            provider_mode=self.provider_mode,
            missing_configuration=False,
        )
