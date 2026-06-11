from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from app.db.types import ResearchSourceProviderType, ResearchSourceStatus


class ProviderMode(StrEnum):
    REAL = "real"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ProviderTestResult:
    success: bool
    status: ResearchSourceStatus
    message: str
    latency_ms: int
    quota_status: str = "unknown"
    provider_mode: ProviderMode = ProviderMode.REAL
    missing_configuration: bool = False


class ResearchProvider(Protocol):
    provider_type: ResearchSourceProviderType
    provider_mode: ProviderMode
    source_key: str

    async def test_connection(self) -> ProviderTestResult:
        ...

    async def search(
        self,
        query: str,
        filters: Mapping[str, Any] | None = None,
    ) -> dict[str, object]:
        ...

    async def fetch_resource(self, resource_id_or_url: str) -> dict[str, object]:
        ...

    def normalize(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        ...

    def extract_metadata(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        ...

    def calculate_provider_scores(self, normalized_result: Mapping[str, Any]) -> dict[str, object]:
        ...


def normalized_document(
    *,
    provider_type: ResearchSourceProviderType,
    provider_mode: ProviderMode,
    source_key: str,
    title: str,
    url: str | None = None,
    content: str | None = None,
    snippet: str | None = None,
    author: str | None = None,
    published_at: str | None = None,
    metadata: dict[str, object] | None = None,
    scores: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "id": url or f"{source_key}:{title}".lower().replace(" ", "-")[:120],
        "title": title,
        "url": url,
        "content": content,
        "snippet": snippet,
        "author": author,
        "published_at": published_at,
        "provider_type": provider_type.value,
        "provider_mode": provider_mode.value,
        "source_key": source_key,
        "metadata": metadata or {},
        "scores": scores or {},
    }
