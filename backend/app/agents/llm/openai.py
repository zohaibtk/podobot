import json
from asyncio import sleep
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import httpx

from app.agents.llm.base import LLMRequest, LLMResponse
from app.core.config import settings

TRANSIENT_OPENAI_STATUSES = {429, 500, 502, 503, 504}
OPENAI_NON_CHAT_MODEL_MARKERS = (
    "audio",
    "dall-e",
    "embedding",
    "image",
    "moderation",
    "realtime",
    "search",
    "speech",
    "transcribe",
    "tts",
    "whisper",
)
OPENAI_CHAT_MODEL_PRIORITIES = (
    "gpt-4.1-mini",
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4.1",
    "gpt-4.1-nano",
    "gpt-4-turbo",
    "gpt-4",
    "chatgpt-4o-latest",
    "gpt-3.5-turbo",
    "o4-mini",
    "o3-mini",
    "o3",
    "o1",
)


class OpenAILLMProvider:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        fallback_models: list[str] | None = None,
        timeout_seconds: int = 30,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.8,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model or settings.openai_model
        self.fallback_models = (
            fallback_models
            if fallback_models is not None
            else self._model_list(settings.openai_fallback_models)
        )
        self._discovered_models: list[str] | None = None
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self.transport = transport

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("OpenAI API key must be configured in Integrations.")

        raw, model = await self._chat_completion(self._agent_prompt(request), json_mode=True)
        output = self._extract_json(raw)
        output.setdefault("summary", self._fallback_summary(request))
        output["needs_approval"] = True
        return LLMResponse(
            output=output,
            metadata={
                "provider": "openai",
                "model": model,
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
            raise RuntimeError("OpenAI API key must be configured in Integrations.")

        raw, model = await self._chat_completion(
            self._text_prompt(prompt, context or {}),
            json_mode=False,
        )
        text = self._extract_text(raw)
        return LLMResponse(
            output={
                "text": text,
                "confidence": 0.84 if text else 0.0,
            },
            metadata={
                "provider": "openai",
                "model": model,
                "generated_at": datetime.now(UTC).isoformat(),
                **self._usage_metadata(raw),
            },
        )

    async def generate_json(self, prompt: str) -> dict[str, object]:
        if not self.api_key:
            raise RuntimeError("OpenAI API key must be configured in Integrations.")

        raw, _model = await self._chat_completion(prompt, json_mode=True)
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
                "provider": "openai",
                "model": self.model,
                "validated_at": datetime.now(UTC).isoformat(),
            },
        )

    async def _chat_completion(
        self,
        prompt: str,
        *,
        json_mode: bool,
    ) -> tuple[dict[str, object], str]:
        model_failures: list[str] = []
        tried_models: set[str] = set()
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            for model in self._candidate_models():
                tried_models.add(model)
                result = await self._try_chat_completion(
                    client,
                    model=model,
                    prompt=prompt,
                    json_mode=json_mode,
                )
                if result["success"] is True:
                    return result["raw"], model
                model_failures.append(f"{model}: {result['message']}")

            if model_failures:
                for model in await self._discover_chat_models(client):
                    if model in tried_models:
                        continue
                    tried_models.add(model)
                    result = await self._try_chat_completion(
                        client,
                        model=model,
                        prompt=prompt,
                        json_mode=json_mode,
                    )
                    if result["success"] is True:
                        return result["raw"], model
                    model_failures.append(f"{model}: {result['message']}")

        if model_failures:
            raise RuntimeError(
                "OpenAI request failed for configured or discovered models: "
                + "; ".join(model_failures)
            )
        raise RuntimeError("OpenAI request failed")

    async def _try_chat_completion(
        self,
        client: httpx.AsyncClient,
        *,
        model: str,
        prompt: str,
        json_mode: bool,
    ) -> dict[str, Any]:
        body = self._request_body(model, prompt, json_mode=json_mode)
        for attempt in range(self.max_retries + 1):
            try:
                response = await client.post(
                    self._chat_completions_url(),
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=body,
                )
                response.raise_for_status()
                return {"success": True, "raw": response.json()}
            except httpx.HTTPStatusError as exc:
                if self._should_retry(exc.response.status_code, attempt):
                    await self._sleep_before_retry(attempt)
                    continue
                detail = self._error_detail(exc.response)
                message = (
                    f"OpenAI request failed with status {exc.response.status_code}: {detail}"
                )
                if self._should_try_next_model(exc.response.status_code, detail):
                    return {"success": False, "message": message}
                raise RuntimeError(message) from exc
            except httpx.HTTPError as exc:
                if self._should_retry(None, attempt):
                    await self._sleep_before_retry(attempt)
                    continue
                raise RuntimeError("OpenAI request failed") from exc

        return {"success": False, "message": "OpenAI request failed"}

    async def _discover_chat_models(self, client: httpx.AsyncClient) -> list[str]:
        if self._discovered_models is not None:
            return self._discovered_models

        try:
            response = await client.get(
                self._models_url(),
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            detail = self._error_detail(exc.response)
            self._discovered_models = []
            raise RuntimeError(
                f"OpenAI model discovery failed with status {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.HTTPError as exc:
            self._discovered_models = []
            raise RuntimeError("OpenAI model discovery failed") from exc

        data = payload.get("data") if isinstance(payload, Mapping) else None
        if not isinstance(data, list):
            self._discovered_models = []
            return []

        models = [
            str(item.get("id"))
            for item in data
            if isinstance(item, Mapping)
            and isinstance(item.get("id"), str)
            and self._looks_like_chat_model(str(item.get("id")))
        ]
        self._discovered_models = self._rank_models(models)
        return self._discovered_models

    def _request_body(
        self,
        model: str,
        prompt: str,
        *,
        json_mode: bool,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return concise production workflow output for PodoBot. "
                        "When JSON mode is requested, return only valid JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
        if self._supports_temperature(model):
            body["temperature"] = 0.3
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        return body

    def _should_retry(self, status_code: int | None, attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False
        return status_code is None or status_code in TRANSIENT_OPENAI_STATUSES

    def _should_try_next_model(self, status_code: int, detail: str) -> bool:
        if status_code not in {400, 403, 404}:
            return False
        normalized = detail.lower()
        return "model" in normalized and (
            "access" in normalized
            or "not found" in normalized
            or "does not exist" in normalized
            or "invalid" in normalized
            or "not supported" in normalized
            or "unsupported" in normalized
        )

    def _candidate_models(self) -> list[str]:
        return self._dedupe_model_list([self.model, *self.fallback_models])

    def _model_list(self, raw: str) -> list[str]:
        return [model.strip() for model in raw.split(",") if model.strip()]

    def _dedupe_model_list(self, models: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for model in models:
            if model in seen:
                continue
            seen.add(model)
            deduped.append(model)
        return deduped

    def _looks_like_chat_model(self, model: str) -> bool:
        normalized = model.lower()
        if not (
            normalized.startswith("gpt-")
            or normalized.startswith("chatgpt-")
            or normalized.startswith("o")
        ):
            return False
        return not any(marker in normalized for marker in OPENAI_NON_CHAT_MODEL_MARKERS)

    def _supports_temperature(self, model: str) -> bool:
        return not model.lower().startswith("o")

    def _rank_models(self, models: list[str]) -> list[str]:
        return sorted(
            self._dedupe_model_list(models),
            key=lambda model: (self._model_rank(model), model),
        )

    def _model_rank(self, model: str) -> int:
        if model in OPENAI_CHAT_MODEL_PRIORITIES:
            return OPENAI_CHAT_MODEL_PRIORITIES.index(model)
        for index, prefix in enumerate(OPENAI_CHAT_MODEL_PRIORITIES):
            if model.startswith(f"{prefix}-"):
                return index
        return len(OPENAI_CHAT_MODEL_PRIORITIES)

    async def _sleep_before_retry(self, attempt: int) -> None:
        if self.retry_backoff_seconds == 0:
            return
        await sleep(self.retry_backoff_seconds * (2**attempt))

    def _chat_completions_url(self) -> str:
        return f"{settings.openai_api_base_url.rstrip('/')}/chat/completions"

    def _models_url(self) -> str:
        return f"{settings.openai_api_base_url.rstrip('/')}/models"

    def _error_detail(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            text = response.text.strip()
            return text[:240] if text else "No error detail returned by OpenAI."

        if isinstance(payload, Mapping):
            error = payload.get("error")
            if isinstance(error, Mapping):
                message = error.get("message") or error.get("type") or error.get("code")
                if message:
                    return str(message)[:240]
            if isinstance(error, str):
                return error[:240]
            message = payload.get("message") or payload.get("detail")
            if message:
                return str(message)[:240]
        return json.dumps(payload, default=str)[:240]

    def _usage_metadata(self, raw: Mapping[str, object]) -> dict[str, object]:
        usage = raw.get("usage")
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
        completion_details = usage.get("completion_tokens_details")
        prompt_details = usage.get("prompt_tokens_details")
        completion_details = completion_details if isinstance(completion_details, Mapping) else {}
        prompt_details = prompt_details if isinstance(prompt_details, Mapping) else {}
        return {
            "usage": {
                "prompt_tokens": self._metadata_int(usage.get("prompt_tokens")),
                "completion_tokens": self._metadata_int(usage.get("completion_tokens")),
                "cached_tokens": self._metadata_int(prompt_details.get("cached_tokens")),
                "reasoning_tokens": self._metadata_int(
                    completion_details.get("reasoning_tokens")
                ),
                "total_tokens": self._metadata_int(usage.get("total_tokens")),
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
            "You are the primary production LLM provider for PodoBot. "
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
            return {"summary": text or "OpenAI returned no structured content."}
        return parsed if isinstance(parsed, dict) else {"summary": str(parsed)}

    def _extract_text(self, raw: Mapping[str, object]) -> str:
        choices = raw.get("choices", [])
        if not isinstance(choices, list) or not choices:
            return ""
        choice = choices[0] if isinstance(choices[0], Mapping) else {}
        message = choice.get("message") if isinstance(choice, Mapping) else {}
        if not isinstance(message, Mapping):
            return ""
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(
                str(part.get("text"))
                for part in content
                if isinstance(part, Mapping) and part.get("text")
            )
        return ""

    def _fallback_summary(self, request: LLMRequest) -> str:
        return f"OpenAI generated workflow support for {request.agent_key}."
