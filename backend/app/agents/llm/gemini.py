import json
from asyncio import sleep
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import httpx

from app.agents.llm.base import LLMRequest, LLMResponse
from app.core.config import settings

TRANSIENT_GEMINI_STATUSES = {429, 500, 502, 503, 504}


class GeminiLLMProvider:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 30,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.8,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model or settings.gemini_model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self.transport = transport

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("Gemini API key must be configured in Integrations.")

        raw = await self._generate_content(self._agent_prompt(request), json_mode=True)
        output = self._extract_json(raw)
        output.setdefault("summary", self._fallback_summary(request))
        output["needs_approval"] = True
        return LLMResponse(
            output=output,
            metadata={
                "provider": "gemini",
                "model": self.model,
                "prompt_key": request.prompt_key,
                "prompt_version": request.prompt_version,
                "generated_at": datetime.now(UTC).isoformat(),
                **self._usage_metadata(raw),
            },
        )

    async def generate_text(
        self,
        prompt: str,
        *,
        context: Mapping[str, object] | None = None,
    ) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("Gemini API key must be configured in Integrations.")

        raw = await self._generate_content(
            self._text_prompt(prompt, context or {}),
            json_mode=False,
        )
        text = self._extract_text(raw)
        return LLMResponse(
            output={
                "text": text,
                "confidence": 0.82 if text else 0.0,
            },
            metadata={
                "provider": "gemini",
                "model": self.model,
                "generated_at": datetime.now(UTC).isoformat(),
                **self._usage_metadata(raw),
            },
        )

    async def generate_json(self, prompt: str) -> dict[str, object]:
        if not self.api_key:
            raise RuntimeError("Gemini API key must be configured in Integrations.")

        raw = await self._generate_content(prompt, json_mode=True)
        return self._extract_json(raw)

    async def validate_output(self, output: Mapping[str, object]) -> LLMResponse:
        checks = [
            {
                "name": "object_output",
                "passed": isinstance(output, Mapping),
                "message": "Output is structured.",
            },
            {
                "name": "approval_gate",
                "passed": bool(output.get("needs_approval", True)),
                "message": "Human approval gates are preserved.",
            },
        ]
        return LLMResponse(
            output={
                "valid": all(bool(check["passed"]) for check in checks),
                "checks": checks,
            },
            metadata={
                "provider": "gemini",
                "model": self.model,
                "validated_at": datetime.now(UTC).isoformat(),
            },
        )

    async def _generate_content(self, prompt: str, *, json_mode: bool) -> dict[str, object]:
        body: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
            },
        }
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"

        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.post(
                        self._generate_content_url(),
                        headers={"x-goog-api-key": self.api_key},
                        json=body,
                    )
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as exc:
                    if self._should_retry(exc.response.status_code, attempt):
                        await self._sleep_before_retry(attempt)
                        continue
                    raise RuntimeError(
                        f"Gemini request failed with status {exc.response.status_code}"
                    ) from exc
                except httpx.HTTPError as exc:
                    if self._should_retry(None, attempt):
                        await self._sleep_before_retry(attempt)
                        continue
                    raise RuntimeError("Gemini request failed") from exc

        raise RuntimeError("Gemini request failed")

    def _should_retry(self, status_code: int | None, attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False
        return status_code is None or status_code in TRANSIENT_GEMINI_STATUSES

    async def _sleep_before_retry(self, attempt: int) -> None:
        if self.retry_backoff_seconds == 0:
            return
        await sleep(self.retry_backoff_seconds * (2**attempt))

    def _generate_content_url(self) -> str:
        return (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )

    def _usage_metadata(self, raw: Mapping[str, object]) -> dict[str, object]:
        usage = raw.get("usageMetadata")
        if not isinstance(usage, Mapping):
            return {
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cached_tokens": 0,
                    "reasoning_tokens": 0,
                    "total_tokens": 0,
                }
            }
        prompt_tokens = self._metadata_int(usage.get("promptTokenCount"))
        completion_tokens = self._metadata_int(usage.get("candidatesTokenCount"))
        cached_tokens = self._metadata_int(usage.get("cachedContentTokenCount"))
        reasoning_tokens = self._metadata_int(usage.get("thoughtsTokenCount"))
        total_tokens = self._metadata_int(usage.get("totalTokenCount"))
        if total_tokens == 0:
            total_tokens = prompt_tokens + completion_tokens + reasoning_tokens
        return {
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cached_tokens": cached_tokens,
                "reasoning_tokens": reasoning_tokens,
                "total_tokens": total_tokens,
            },
            "usage_metadata": dict(usage),
        }

    def _metadata_int(self, value: object) -> int:
        if isinstance(value, bool) or value is None:
            return 0
        try:
            return max(int(value), 0)
        except (TypeError, ValueError):
            return 0

    def _agent_prompt(self, request: LLMRequest) -> str:
        return (
            "You are the production LLM provider for PodoBot. "
            "Return only a compact JSON object. The JSON must include summary, "
            "recommendations, risks, next_actions, and needs_approval=true. "
            "Preserve human approval checkpoints and do not claim work has been "
            "completed unless the input proves it.\n\n"
            f"Agent: {request.agent_key}\n"
            f"Prompt key: {request.prompt_key} v{request.prompt_version}\n"
            f"Template:\n{request.template_body}\n\n"
            f"Input JSON:\n{json.dumps(request.input_payload, default=str)}"
        )

    def _text_prompt(self, prompt: str, context: Mapping[str, object]) -> str:
        return (
            "Generate concise production workflow text for PodoBot. "
            "Be specific, operational, and preserve human approval checkpoints.\n\n"
            f"Prompt:\n{prompt}\n\n"
            f"Context JSON:\n{json.dumps(context, default=str)}"
        )

    def _extract_json(self, raw: Mapping[str, object]) -> dict[str, object]:
        text = self._extract_text(raw).strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"summary": text or "Gemini returned no structured content."}
        return parsed if isinstance(parsed, dict) else {"summary": str(parsed)}

    def _extract_text(self, raw: Mapping[str, object]) -> str:
        candidates = raw.get("candidates", [])
        if not isinstance(candidates, list) or not candidates:
            return ""
        content = candidates[0].get("content") if isinstance(candidates[0], dict) else {}
        parts = content.get("parts", []) if isinstance(content, dict) else []
        texts = [
            str(part.get("text"))
            for part in parts
            if isinstance(part, dict) and part.get("text")
        ]
        return "\n".join(texts)

    def _fallback_summary(self, request: LLMRequest) -> str:
        return f"Gemini generated workflow support for {request.agent_key}."
