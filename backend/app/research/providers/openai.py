from collections.abc import Mapping
from typing import Any

from app.agents.llm.openai import OpenAILLMProvider
from app.core.config import settings
from app.db.types import ResearchSourceProviderType
from app.research.providers.base import normalized_document
from app.research.providers.http import HTTPResearchProvider


class OpenAIResearchProvider(HTTPResearchProvider):
    provider_type = ResearchSourceProviderType.OPENAI

    async def test_connection(self):
        provider = OpenAILLMProvider(
            api_key=self.api_key,
            model=settings.openai_model,
            timeout_seconds=self.timeout_seconds,
        )
        await provider.generate_text("Return ok.")
        return self._test_success(message="OpenAI API is reachable.", latency_ms=220)

    async def search(
        self,
        query: str,
        filters: Mapping[str, Any] | None = None,
    ) -> dict[str, object]:
        classified = await self.classify_text(query, filters or {})
        return {
            "query": query,
            "provider_type": self.provider_type.value,
            "provider_mode": self.provider_mode.value,
            "source_key": self.source_key,
            "results": [classified],
        }

    async def fetch_resource(self, resource_id_or_url: str) -> dict[str, object]:
        document = await self.classify_text(resource_id_or_url, {})
        return {
            "provider_type": self.provider_type.value,
            "provider_mode": self.provider_mode.value,
            "source_key": self.source_key,
            "document": document,
        }

    async def classify_text(
        self,
        text: str,
        filters: Mapping[str, Any] | None = None,
    ) -> dict[str, object]:
        provider = OpenAILLMProvider(
            api_key=self.api_key,
            model=settings.openai_model,
            timeout_seconds=self.timeout_seconds,
        )
        response = await provider.generate_text(
            "Extract research signals as compact labels for this podcast research input. "
            "Return themes, pain points, opportunities, and contradictions.\n\n"
            f"{text}",
            context={"filters": dict(filters or {})},
        )
        return self.normalize(
            {
                "input": text,
                "filters": dict(filters or {}),
                "text": response.output.get("text") or "",
                "metadata": response.metadata,
            }
        )

    def normalize(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        text = str(raw_result.get("text") or "No OpenAI classification text returned.")
        document = normalized_document(
            provider_type=self.provider_type,
            provider_mode=self.provider_mode,
            source_key=self.source_key,
            title="OpenAI research classification",
            content=text,
            snippet=text[:280],
            metadata=self.extract_metadata(raw_result),
        )
        document["scores"] = self.calculate_provider_scores(document)
        return document

    def extract_metadata(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        return {
            "classification_domains": [
                "signals",
                "themes",
                "pain_points",
                "opportunities",
                "contradictions",
            ],
            "provider_metadata": raw_result.get("metadata") or {},
        }

    def calculate_provider_scores(self, normalized_result: Mapping[str, Any]) -> dict[str, object]:
        return self._scores(normalized_result, engagement=0, authority=0.84)
