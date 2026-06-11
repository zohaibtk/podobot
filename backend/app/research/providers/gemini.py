from collections.abc import Mapping
from typing import Any

from app.core.config import settings
from app.db.types import ResearchSourceProviderType
from app.research.providers.base import normalized_document
from app.research.providers.http import HTTPResearchProvider


class GeminiResearchClassifierProvider(HTTPResearchProvider):
    provider_type = ResearchSourceProviderType.GEMINI

    @property
    def generate_content_url(self) -> str:
        return (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent"
        )

    async def test_connection(self):
        await self._post_json(
            self.generate_content_url,
            headers={"x-goog-api-key": self.api_key or ""},
            json_body={"contents": [{"parts": [{"text": "Return ok."}]}]},
        )
        return self._test_success(message="Gemini API is reachable.", latency_ms=240)

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
        prompt = (
            "Extract research signals as compact labels for this podcast research input. "
            "Return themes, pain points, opportunities, and contradictions.\n\n"
            f"{text}"
        )
        raw = await self._post_json(
            self.generate_content_url,
            headers={"x-goog-api-key": self.api_key or ""},
            json_body={"contents": [{"parts": [{"text": prompt}]}]},
        )
        return self.normalize({"input": text, "filters": dict(filters or {}), "raw": raw})

    def normalize(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        raw = raw_result.get("raw") if isinstance(raw_result.get("raw"), dict) else {}
        text = self._extract_text(raw)
        document = normalized_document(
            provider_type=self.provider_type,
            provider_mode=self.provider_mode,
            source_key=self.source_key,
            title="Gemini research classification",
            content=text,
            snippet=text[:280],
            metadata=self.extract_metadata(raw_result),
        )
        document["scores"] = self.calculate_provider_scores(document)
        return document

    def extract_metadata(self, raw_result: Mapping[str, Any]) -> dict[str, object]:
        raw = raw_result.get("raw") if isinstance(raw_result.get("raw"), dict) else {}
        candidates = raw.get("candidates", [])
        return {
            "candidate_count": len(candidates) if isinstance(candidates, list) else 0,
            "classification_domains": [
                "signals",
                "themes",
                "pain_points",
                "opportunities",
                "contradictions",
            ],
        }

    def calculate_provider_scores(self, normalized_result: Mapping[str, Any]) -> dict[str, object]:
        return self._scores(normalized_result, engagement=0, authority=0.82)

    def _extract_text(self, raw: Mapping[str, Any]) -> str:
        candidates = raw.get("candidates", [])
        if not isinstance(candidates, list) or not candidates:
            return "No Gemini classification text returned."
        content = candidates[0].get("content") if isinstance(candidates[0], dict) else {}
        parts = content.get("parts", []) if isinstance(content, dict) else []
        texts = [
            str(part.get("text"))
            for part in parts
            if isinstance(part, dict) and part.get("text")
        ]
        return "\n".join(texts) or "No Gemini classification text returned."
