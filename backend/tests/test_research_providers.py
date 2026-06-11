from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.db.types import ResearchSourceProviderType, ResearchSourceStatus
from app.mcp.adapters import research as research_mcp_module
from app.mcp.adapters.research import ResearchMCPAdapter
from app.mcp.client.base import MCPClientRequest
from app.modules.research_sources.service import ResearchSourceConfigService
from app.research.providers.base import ProviderMode, ProviderTestResult
from app.research.providers.exa import ExaResearchProvider
from app.research.providers.firecrawl import FirecrawlScrapingProvider
from app.research.providers.gemini import GeminiResearchClassifierProvider
from app.research.providers.grok import GrokResearchProvider
from app.research.providers.groq import GroqResearchProvider
from app.research.providers.hn import HackerNewsAlgoliaResearchProvider
from app.research.providers.openai import OpenAIResearchProvider
from app.research.providers.pytrends import PytrendsFallbackProvider
from app.research.providers.reddit import RedditResearchProvider
from app.research.providers.registry import (
    ProviderExecutionResult,
    ResearchProviderRegistry,
    safe_provider_error,
)
from app.research.providers.serpapi import SerpApiTrendsProvider
from app.research.providers.youtube import YouTubeResearchProvider


def _source(
    provider_type: ResearchSourceProviderType,
    *,
    key: str | None = None,
    enabled: bool = True,
    status: ResearchSourceStatus = ResearchSourceStatus.HEALTHY,
    config_json: dict[str, object] | None = None,
):
    return SimpleNamespace(
        key=key or provider_type.value,
        name=key or provider_type.value,
        provider_type=provider_type,
        config_json=config_json or {},
        enabled=enabled,
        status=status,
        quota_status="available",
        success_rate=0.5,
        recent_failure_count=0,
    )


def test_provider_registry_returns_correct_real_provider() -> None:
    registry = ResearchProviderRegistry(session=None)
    config_json = ResearchSourceConfigService().store_api_key({}, "yt-test-key")

    provider = registry.provider_for_source(
        _source(
            ResearchSourceProviderType.YOUTUBE_DATA_API,
            key="youtube_data_api",
            config_json=config_json,
        )
    )

    assert isinstance(provider, YouTubeResearchProvider)
    assert provider.provider_mode == ProviderMode.REAL


def test_provider_registry_returns_grok_provider_when_key_configured() -> None:
    registry = ResearchProviderRegistry(session=None)
    config_json = ResearchSourceConfigService().store_api_key({}, "xai-test-key")

    provider = registry.provider_for_source(
        _source(
            ResearchSourceProviderType.GROK_X,
            key="grok_x",
            config_json=config_json,
        )
    )

    assert isinstance(provider, GrokResearchProvider)
    assert provider.provider_mode == ProviderMode.REAL


def test_provider_registry_returns_openai_provider_when_key_configured() -> None:
    registry = ResearchProviderRegistry(session=None)
    config_json = ResearchSourceConfigService().store_api_key({}, "openai-test-key")

    provider = registry.provider_for_source(
        _source(
            ResearchSourceProviderType.OPENAI,
            key="openai",
            config_json=config_json,
        )
    )

    assert isinstance(provider, OpenAIResearchProvider)
    assert provider.provider_mode == ProviderMode.REAL


def test_provider_registry_returns_groq_provider_when_key_configured() -> None:
    registry = ResearchProviderRegistry(session=None)
    config_json = ResearchSourceConfigService().store_api_key({}, "groq-test-key")

    provider = registry.provider_for_source(
        _source(
            ResearchSourceProviderType.GROQ,
            key="groq",
            config_json=config_json,
        )
    )

    assert isinstance(provider, GroqResearchProvider)
    assert provider.provider_mode == ProviderMode.REAL


def test_provider_registry_rejects_missing_required_credentials() -> None:
    registry = ResearchProviderRegistry(session=None)

    with pytest.raises(HTTPException) as exc:
        registry.provider_for_source(_source(ResearchSourceProviderType.EXA, key="exa"))

    assert exc.value.status_code == 503
    assert "Exa API key" in exc.value.detail


def test_provider_registry_rejects_missing_grok_key() -> None:
    registry = ResearchProviderRegistry(session=None)

    with pytest.raises(HTTPException) as exc:
        registry.provider_for_source(_source(ResearchSourceProviderType.GROK_X, key="grok_x"))

    assert exc.value.status_code == 503
    assert "Grok API key" in exc.value.detail


def test_provider_registry_rejects_missing_openai_key() -> None:
    registry = ResearchProviderRegistry(session=None)

    with pytest.raises(HTTPException) as exc:
        registry.provider_for_source(_source(ResearchSourceProviderType.OPENAI, key="openai"))

    assert exc.value.status_code == 503
    assert "OpenAI API key" in exc.value.detail


def test_provider_registry_rejects_missing_groq_key() -> None:
    registry = ResearchProviderRegistry(session=None)

    with pytest.raises(HTTPException) as exc:
        registry.provider_for_source(_source(ResearchSourceProviderType.GROQ, key="groq"))

    assert exc.value.status_code == 503
    assert "Groq API key" in exc.value.detail


def test_disabled_source_cannot_execute() -> None:
    registry = ResearchProviderRegistry(session=None)

    with pytest.raises(HTTPException):
        registry.provider_for_source(
            _source(
                ResearchSourceProviderType.REDDIT_JSON,
                enabled=False,
                status=ResearchSourceStatus.DISABLED,
            )
        )


def test_missing_configuration_is_visible_as_unavailable() -> None:
    registry = ResearchProviderRegistry(session=None)
    mode = registry.credential_provider.provider_mode(ResearchSourceProviderType.FIRECRAWL)

    assert mode == ProviderMode.UNAVAILABLE
    assert registry.credential_provider.missing_configuration(
        ResearchSourceProviderType.FIRECRAWL
    )


async def test_reddit_provider_search_works(monkeypatch) -> None:
    async def fake_get_json(self, *args, **kwargs):
        return {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "AI podcast operations",
                            "permalink": "/r/podcasts/comments/1",
                            "selftext": "Operators discuss research workflows.",
                            "score": 12,
                            "num_comments": 5,
                        }
                    }
                ]
            }
        }

    monkeypatch.setattr(RedditResearchProvider, "_get_json", fake_get_json)
    provider = RedditResearchProvider(source_key="reddit_json")

    result = await provider.search("ai podcast", {})

    assert result["results"][0]["title"] == "AI podcast operations"
    assert result["results"][0]["provider_type"] == "reddit_json"


async def test_hn_provider_search_works(monkeypatch) -> None:
    async def fake_get_json(self, *args, **kwargs):
        return {"hits": [{"title": "Agent workflows", "url": "https://example.com", "points": 42}]}

    monkeypatch.setattr(HackerNewsAlgoliaResearchProvider, "_get_json", fake_get_json)
    provider = HackerNewsAlgoliaResearchProvider(source_key="hn_algolia")

    result = await provider.search("agents", {})

    assert result["results"][0]["title"] == "Agent workflows"


async def test_youtube_provider_search_works(monkeypatch) -> None:
    async def fake_get_json(self, *args, **kwargs):
        return {
            "items": [
                {
                    "id": {"videoId": "abc123"},
                    "snippet": {
                        "title": "Podcast AI",
                        "description": "A video about AI podcasts.",
                        "channelTitle": "Ops Channel",
                    },
                }
            ]
        }

    monkeypatch.setattr(YouTubeResearchProvider, "_get_json", fake_get_json)
    provider = YouTubeResearchProvider(source_key="youtube_data_api", api_key="yt")

    result = await provider.search("podcast ai", {})

    assert result["results"][0]["url"] == "https://www.youtube.com/watch?v=abc123"


async def test_exa_provider_search_works(monkeypatch) -> None:
    async def fake_post_json(self, *args, **kwargs):
        return {"results": [{"title": "Deep topic", "url": "https://example.com", "score": 0.8}]}

    monkeypatch.setattr(ExaResearchProvider, "_post_json", fake_post_json)
    provider = ExaResearchProvider(source_key="exa", api_key="exa")

    result = await provider.search("topic", {})

    assert result["results"][0]["metadata"]["score"] == 0.8


async def test_gemini_provider_sends_api_key_header(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_post_json(self, url, *, json_body, headers=None, params=None):
        captured["headers"] = dict(headers or {})
        captured["params"] = dict(params or {})
        return {
            "candidates": [
                {"content": {"parts": [{"text": "ok"}]}},
            ],
        }

    monkeypatch.setattr(GeminiResearchClassifierProvider, "_post_json", fake_post_json)
    provider = GeminiResearchClassifierProvider(source_key="gemini", api_key="gem-key")

    await provider.test_connection()

    assert captured["headers"] == {"x-goog-api-key": "gem-key"}
    assert captured["params"] == {}


async def test_firecrawl_provider_scrape_works(monkeypatch) -> None:
    async def fake_post_json(self, *args, **kwargs):
        return {
            "data": {
                "markdown": "# Scraped page",
                "metadata": {"title": "Scraped", "sourceURL": "https://example.com"},
            }
        }

    monkeypatch.setattr(FirecrawlScrapingProvider, "_post_json", fake_post_json)
    provider = FirecrawlScrapingProvider(source_key="firecrawl", api_key="fc")

    result = await provider.fetch_resource("https://example.com")

    assert result["document"]["title"] == "Scraped"
    assert "Scraped page" in result["document"]["content"]


async def test_serpapi_trend_lookup_works(monkeypatch) -> None:
    async def fake_get_json(self, *args, **kwargs):
        return {
            "interest_over_time": {
                "timeline_data": [
                    {"values": [{"extracted_value": 40}]},
                    {"values": [{"extracted_value": 80}]},
                ]
            }
        }

    monkeypatch.setattr(SerpApiTrendsProvider, "_get_json", fake_get_json)
    provider = SerpApiTrendsProvider(source_key="serpapi", api_key="serp")

    result = await provider.trend_score("ai podcast", {})

    assert result["trend_available"] is True
    assert result["trend_score"] == 60


async def test_pytrends_fallback_works() -> None:
    provider = PytrendsFallbackProvider(source_key="pytrends")

    result = await provider.trend_score("ai podcast", {})

    assert result["trend_available"] is True
    assert result["fallback_used"] is True


async def test_trend_unavailable_is_graceful() -> None:
    class NoTrendRegistry(ResearchProviderRegistry):
        def __init__(self):
            pass

        async def _source_by_provider_type(self, provider_type):
            return None

    result = await NoTrendRegistry().get_trend_score(query="missing", filters={})

    assert result.output["trend_available"] is False
    assert result.output["message"] == "Trend not available"


async def test_mcp_tool_calls_provider_registry(monkeypatch) -> None:
    class FakeRegistry:
        async def search_sources(self, **kwargs):
            return ProviderExecutionResult(
                output={"results": [{"title": "Registry result"}], "sources": []},
                metadata={"provider_used": "reddit_json", "source_used": "reddit_json"},
            )

    monkeypatch.setattr(
        research_mcp_module,
        "ResearchProviderRegistry",
        lambda session: FakeRegistry(),
    )
    adapter = ResearchMCPAdapter(session=None)

    response = await adapter.execute(
        MCPClientRequest(
            server_key="research",
            tool_key="research.search_sources",
            input_payload={"query": "agents"},
        )
    )

    assert response.output_payload["results"][0]["title"] == "Registry result"
    assert response.output_metadata["adapter"] == "research-provider-registry"


def test_source_health_metrics_update_from_provider_result() -> None:
    registry = ResearchProviderRegistry(session=None)
    source = _source(ResearchSourceProviderType.REDDIT_JSON)

    registry.apply_health_result(
        source,
        ProviderTestResult(
            success=False,
            status=ResearchSourceStatus.FAILED,
            message="Provider failed",
            latency_ms=250,
            quota_status="failed",
        ),
        execution_time_ms=250,
    )

    assert source.status == ResearchSourceStatus.FAILED
    assert source.average_latency_ms == 250
    assert source.recent_failure_count == 1
    assert source.last_failure_reason == "Provider failed"


def test_secrets_never_appear_in_provider_errors() -> None:
    error = safe_provider_error(RuntimeError("https://example.com?api_key=secret-value"))

    assert error == "Provider request failed"
    assert "secret-value" not in error
