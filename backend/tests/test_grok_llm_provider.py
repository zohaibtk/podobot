import json

import httpx
import pytest

from app.agents.llm.database import DatabaseLLMProvider
from app.agents.llm.grok import GrokLLMProvider


@pytest.mark.anyio
async def test_grok_provider_retries_transient_statuses_with_bearer_auth() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(503, request=request, json={"error": "temporarily unavailable"})
        return httpx.Response(
            200,
            request=request,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"episodes":[{"title":"Fallback",'
                                '"premise":"Keep planning online."}]}'
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 4, "completion_tokens": 8, "total_tokens": 12},
            },
        )

    provider = GrokLLMProvider(
        api_key="xai-test-key",
        max_retries=2,
        retry_backoff_seconds=0,
        transport=httpx.MockTransport(handler),
    )

    response = await provider.generate_json("Generate an episode plan.")

    assert response["episodes"] == [
        {"title": "Fallback", "premise": "Keep planning online."}
    ]
    assert len(requests) == 2
    assert all("key=" not in str(request.url) for request in requests)
    assert all(request.headers["authorization"] == "Bearer xai-test-key" for request in requests)
    payload = json.loads(requests[-1].content)
    assert payload["model"] == "grok-latest"
    assert payload["response_format"] == {"type": "json_object"}


@pytest.mark.anyio
async def test_grok_provider_normalizes_legacy_model_alias() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            request=request,
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    provider = GrokLLMProvider(
        api_key="xai-test-key",
        model="grok-4.3",
        transport=httpx.MockTransport(handler),
    )

    response = await provider.generate_text("Return ok.")

    payload = json.loads(requests[-1].content)
    assert payload["model"] == "grok-latest"
    assert response.metadata["model"] == "grok-latest"


@pytest.mark.anyio
async def test_grok_provider_does_not_retry_non_transient_status() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(401, request=request, json={"error": "bad key"})

    provider = GrokLLMProvider(
        api_key="xai-test-key",
        max_retries=2,
        retry_backoff_seconds=0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RuntimeError, match="Grok request failed with status 401: bad key"):
        await provider.generate_json("Generate an episode plan.")

    assert len(requests) == 1


@pytest.mark.anyio
async def test_database_llm_provider_uses_openai_before_fallbacks() -> None:
    class WorkingOpenAI:
        async def generate_json(self, prompt: str) -> dict[str, object]:
            return {"provider": "openai", "prompt": prompt}

    class FailingGemini:
        async def generate_json(self, prompt: str) -> dict[str, object]:
            raise AssertionError("Gemini should not run before OpenAI.")

    provider = DatabaseLLMProvider(session=None)  # type: ignore[arg-type]

    async def configured_providers():
        return [
            ("openai", WorkingOpenAI()),
            ("gemini", FailingGemini()),
        ]

    provider._configured_providers = configured_providers  # type: ignore[method-assign]

    result = await provider.generate_json("keep going")

    assert result == {"provider": "openai", "prompt": "keep going"}


@pytest.mark.anyio
async def test_database_llm_provider_falls_back_to_gemini_when_openai_fails() -> None:
    class FailingOpenAI:
        async def generate_json(self, prompt: str) -> dict[str, object]:
            raise RuntimeError("OpenAI request failed")

    class WorkingGemini:
        async def generate_json(self, prompt: str) -> dict[str, object]:
            return {"provider": "gemini", "prompt": prompt}

    class UnusedGrok:
        async def generate_json(self, prompt: str) -> dict[str, object]:
            raise AssertionError("Groq should not run before Gemini.")

    provider = DatabaseLLMProvider(session=None)  # type: ignore[arg-type]

    async def configured_providers():
        return [
            ("openai", FailingOpenAI()),
            ("gemini", WorkingGemini()),
            ("groq", UnusedGrok()),
        ]

    provider._configured_providers = configured_providers  # type: ignore[method-assign]

    result = await provider.generate_json("keep going")

    assert result == {"provider": "gemini", "prompt": "keep going"}


@pytest.mark.anyio
async def test_database_llm_provider_falls_back_to_groq_after_openai_and_gemini_fail() -> None:
    class FailingOpenAI:
        async def generate_json(self, prompt: str) -> dict[str, object]:
            raise RuntimeError("OpenAI request failed")

    class FailingGemini:
        async def generate_json(self, prompt: str) -> dict[str, object]:
            raise RuntimeError("Gemini request failed")

    class WorkingGroq:
        async def generate_json(self, prompt: str) -> dict[str, object]:
            return {"provider": "groq", "prompt": prompt}

    class UnusedGrok:
        async def generate_json(self, prompt: str) -> dict[str, object]:
            raise AssertionError("Grok should not run before Groq.")

    provider = DatabaseLLMProvider(session=None)  # type: ignore[arg-type]

    async def configured_providers():
        return [
            ("openai", FailingOpenAI()),
            ("gemini", FailingGemini()),
            ("groq", WorkingGroq()),
            ("grok", UnusedGrok()),
        ]

    provider._configured_providers = configured_providers  # type: ignore[method-assign]

    result = await provider.generate_json("keep going")

    assert result == {"provider": "groq", "prompt": "keep going"}


@pytest.mark.anyio
async def test_database_llm_provider_falls_back_to_grok_after_primary_chain_fails() -> None:
    class FailingProvider:
        def __init__(self, label: str) -> None:
            self.label = label

        async def generate_json(self, prompt: str) -> dict[str, object]:
            raise RuntimeError(f"{self.label} request failed")

    class WorkingGrok:
        async def generate_json(self, prompt: str) -> dict[str, object]:
            return {"provider": "grok", "prompt": prompt}

    provider = DatabaseLLMProvider(session=None)  # type: ignore[arg-type]

    async def configured_providers():
        return [
            ("openai", FailingProvider("OpenAI")),
            ("gemini", FailingProvider("Gemini")),
            ("groq", FailingProvider("Groq")),
            ("grok", WorkingGrok()),
        ]

    provider._configured_providers = configured_providers  # type: ignore[method-assign]

    result = await provider.generate_json("keep going")

    assert result == {"provider": "grok", "prompt": "keep going"}


@pytest.mark.anyio
async def test_database_llm_provider_reports_when_no_llm_keys_are_saved() -> None:
    provider = DatabaseLLMProvider(session=None)  # type: ignore[arg-type]

    async def configured_providers():
        return []

    provider._configured_providers = configured_providers  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="OpenAI, Gemini, Groq, or Grok API key"):
        await provider.generate_json("keep going")
