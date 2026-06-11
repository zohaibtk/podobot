import json

import httpx
import pytest

from app.agents.llm.groq import GroqLLMProvider


@pytest.mark.anyio
async def test_groq_provider_retries_transient_statuses_with_bearer_auth() -> None:
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
                                '{"episodes":[{"title":"Fast fallback",'
                                '"premise":"Keep the workflow moving."}]}'
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 4, "completion_tokens": 8, "total_tokens": 12},
            },
        )

    provider = GroqLLMProvider(
        api_key="groq-test-key",
        max_retries=2,
        retry_backoff_seconds=0,
        transport=httpx.MockTransport(handler),
    )

    response = await provider.generate_json("Generate an episode plan.")

    assert response["episodes"] == [
        {"title": "Fast fallback", "premise": "Keep the workflow moving."}
    ]
    assert len(requests) == 2
    assert all("key=" not in str(request.url) for request in requests)
    assert all(request.headers["authorization"] == "Bearer groq-test-key" for request in requests)
    assert str(requests[-1].url) == "https://api.groq.com/openai/v1/chat/completions"
    payload = json.loads(requests[-1].content)
    assert payload["model"] == "llama-3.3-70b-versatile"
    assert payload["response_format"] == {"type": "json_object"}


@pytest.mark.anyio
async def test_groq_provider_does_not_retry_non_transient_status() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            401,
            request=request,
            json={"error": {"message": "invalid api key"}},
        )

    provider = GroqLLMProvider(
        api_key="groq-test-key",
        max_retries=2,
        retry_backoff_seconds=0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RuntimeError, match="Groq request failed with status 401: invalid api key"):
        await provider.generate_json("Generate an episode plan.")

    assert len(requests) == 1
