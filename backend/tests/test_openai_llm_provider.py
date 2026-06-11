import json

import httpx
import pytest

from app.agents.llm.openai import OpenAILLMProvider


@pytest.mark.anyio
async def test_openai_provider_retries_transient_statuses_with_bearer_auth() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(503, request=request, json={"error": "try again"})
        return httpx.Response(
            200,
            request=request,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"episodes":[{"title":"Primary plan",'
                                '"premise":"Use OpenAI first."}]}'
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 4, "completion_tokens": 8, "total_tokens": 12},
            },
        )

    provider = OpenAILLMProvider(
        api_key="openai-test-key",
        max_retries=2,
        retry_backoff_seconds=0,
        transport=httpx.MockTransport(handler),
    )

    response = await provider.generate_json("Generate an episode plan.")

    assert response["episodes"] == [
        {"title": "Primary plan", "premise": "Use OpenAI first."}
    ]
    assert len(requests) == 2
    assert all("key=" not in str(request.url) for request in requests)
    assert all(
        request.headers["authorization"] == "Bearer openai-test-key"
        for request in requests
    )
    assert str(requests[-1].url) == "https://api.openai.com/v1/chat/completions"
    payload = json.loads(requests[-1].content)
    assert payload["model"] == "gpt-4.1-mini"
    assert payload["response_format"] == {"type": "json_object"}


@pytest.mark.anyio
async def test_openai_provider_tries_fallback_model_when_project_lacks_access() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        payload = json.loads(request.content)
        if payload["model"] == "gpt-5-mini":
            return httpx.Response(
                403,
                request=request,
                json={
                    "error": {
                        "message": (
                            "Project `proj_123` does not have access to model `gpt-5-mini`"
                        )
                    }
                },
            )
        return httpx.Response(
            200,
            request=request,
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    provider = OpenAILLMProvider(
        api_key="openai-test-key",
        model="gpt-5-mini",
        fallback_models=["gpt-4.1-mini"],
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )

    response = await provider.generate_text("Return ok.")

    assert [json.loads(request.content)["model"] for request in requests] == [
        "gpt-5-mini",
        "gpt-4.1-mini",
    ]
    assert response.output["text"] == "ok"
    assert response.metadata["model"] == "gpt-4.1-mini"


@pytest.mark.anyio
async def test_openai_provider_discovers_accessible_chat_model() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v1/models":
            return httpx.Response(
                200,
                request=request,
                json={
                    "data": [
                        {"id": "text-embedding-3-small"},
                        {"id": "gpt-4o-2024-11-20"},
                    ]
                },
            )

        payload = json.loads(request.content)
        if payload["model"] in {"gpt-5-mini", "gpt-4.1-mini"}:
            return httpx.Response(
                403,
                request=request,
                json={
                    "error": {
                        "message": (
                            f"Project `proj_123` does not have access to model "
                            f"`{payload['model']}`"
                        )
                    }
                },
            )
        return httpx.Response(
            200,
            request=request,
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    provider = OpenAILLMProvider(
        api_key="openai-test-key",
        model="gpt-5-mini",
        fallback_models=["gpt-4.1-mini"],
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )

    response = await provider.generate_text("Return ok.")

    chat_models = [
        json.loads(request.content)["model"]
        for request in requests
        if request.method == "POST"
    ]
    assert chat_models == ["gpt-5-mini", "gpt-4.1-mini", "gpt-4o-2024-11-20"]
    assert any(request.url.path == "/v1/models" for request in requests)
    assert response.output["text"] == "ok"
    assert response.metadata["model"] == "gpt-4o-2024-11-20"


@pytest.mark.anyio
async def test_openai_provider_does_not_retry_non_transient_status() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            401,
            request=request,
            json={"error": {"message": "invalid api key"}},
        )

    provider = OpenAILLMProvider(
        api_key="openai-test-key",
        max_retries=2,
        retry_backoff_seconds=0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RuntimeError, match="OpenAI request failed with status 401"):
        await provider.generate_json("Generate an episode plan.")

    assert len(requests) == 1
