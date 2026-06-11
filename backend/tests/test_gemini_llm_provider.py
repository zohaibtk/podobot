import httpx
import pytest

from app.agents.llm.gemini import GeminiLLMProvider


@pytest.mark.anyio
async def test_gemini_provider_retries_transient_statuses_without_query_key() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(503, request=request, json={"error": "temporarily unavailable"})
        return httpx.Response(
            200,
            request=request,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        '{"episodes":[{"title":"Pilot",'
                                        '"premise":"Open the arc."}]}'
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        )

    provider = GeminiLLMProvider(
        api_key="test-key",
        max_retries=2,
        retry_backoff_seconds=0,
        transport=httpx.MockTransport(handler),
    )

    response = await provider.generate_json("Generate an episode plan.")

    assert response["episodes"] == [{"title": "Pilot", "premise": "Open the arc."}]
    assert len(requests) == 2
    assert all("key=" not in str(request.url) for request in requests)
    assert all(request.headers["x-goog-api-key"] == "test-key" for request in requests)


@pytest.mark.anyio
async def test_gemini_provider_does_not_retry_non_transient_status() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(400, request=request, json={"error": "bad request"})

    provider = GeminiLLMProvider(
        api_key="test-key",
        max_retries=2,
        retry_backoff_seconds=0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RuntimeError, match="Gemini request failed with status 400"):
        await provider.generate_json("Generate an episode plan.")

    assert len(requests) == 1
