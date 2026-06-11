from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.db.types import (
    ResearchConfidenceLevel,
    ResearchSourceProviderType,
)
from app.modules.research.scoring import (
    AuthorScoringService,
    ConfidenceLevelService,
    EngagementScoringService,
    FreshnessScoringService,
    TierScoringService,
    TrendScoringService,
    clamp_score,
    composite_score_for,
)
from app.research.providers.registry import ProviderExecutionResult


def _document(
    provider_type: ResearchSourceProviderType,
    *,
    metadata: dict[str, object] | None = None,
    scores: dict[str, object] | None = None,
    author: str | None = "Research Desk",
    published_at: datetime | None = None,
    url: str | None = "https://example.com/research",
):
    return SimpleNamespace(
        id=uuid4(),
        title="AI operations",
        provider_type=provider_type,
        raw_metadata_json={"metadata": metadata or {}, "scores": scores or {}},
        author=author,
        published_at=published_at,
        url=url,
    )


def _source(provider_type: ResearchSourceProviderType):
    return SimpleNamespace(provider_type=provider_type, key=provider_type.value, name="Source")


def test_tier_mapping_is_correct() -> None:
    service = TierScoringService()

    assert service.score("S") == 100
    assert service.score("A") == 85
    assert service.score("B") == 70
    assert service.score("C") == 50
    assert service.score("D") == 25


def test_composite_formula_is_exact() -> None:
    score = composite_score_for(
        tier_score=90,
        engagement_score=70,
        freshness_score=85,
        author_score=80,
    )

    assert score == 83


def test_confidence_mapping_is_correct() -> None:
    service = ConfidenceLevelService()

    assert service.level_for(85) == ResearchConfidenceLevel.HIGH
    assert service.level_for(65) == ResearchConfidenceLevel.MEDIUM
    assert service.level_for(40) == ResearchConfidenceLevel.LOW
    assert service.level_for(39) == ResearchConfidenceLevel.WEAK


def test_freshness_score_is_correct() -> None:
    service = FreshnessScoringService()
    now = datetime.now(UTC)

    assert service.score(now - timedelta(days=3)) == 100
    assert service.score(now - timedelta(days=20)) == 85
    assert service.score(now - timedelta(days=60)) == 70
    assert service.score(now - timedelta(days=200)) == 50
    assert service.score(now - timedelta(days=500)) == 30
    assert service.score(None) == 45


def test_engagement_score_uses_provider_metadata() -> None:
    service = EngagementScoringService()

    reddit = _document(
        ResearchSourceProviderType.REDDIT_JSON,
        metadata={"score": 20, "num_comments": 10},
    )
    hn = _document(
        ResearchSourceProviderType.HN_ALGOLIA,
        metadata={"points": 40, "num_comments": 20},
    )
    youtube = _document(
        ResearchSourceProviderType.YOUTUBE_DATA_API,
        metadata={"view_count": 10_000, "like_count": 500, "comment_count": 5},
    )
    exa = _document(ResearchSourceProviderType.EXA, metadata={"score": 0.82})

    assert service.score(reddit) == 40
    assert service.score(hn) == 70
    assert service.score(youtube) == 25
    assert service.score(exa) == 82


def test_author_score_fallback_works() -> None:
    document = _document(
        ResearchSourceProviderType.GROK_X,
        author=None,
        url=None,
    )

    assert AuthorScoringService().score(document, _source(ResearchSourceProviderType.GROK_X)) == 50


def test_score_values_never_exceed_zero_to_one_hundred() -> None:
    assert clamp_score(-10) == 0
    assert clamp_score(120) == 100


async def test_trend_score_uses_registry_result(monkeypatch) -> None:
    class FakeRegistry:
        def __init__(self, session):
            self.session = session

        async def get_trend_score(self, *, query, filters):
            return ProviderExecutionResult(
                output={
                    "trend_available": True,
                    "score": 91,
                    "source_used": "serpapi",
                },
                metadata={"fallback_used": False},
            )

    import app.research.providers.registry as registry_module

    monkeypatch.setattr(registry_module, "ResearchProviderRegistry", FakeRegistry)
    document = _document(ResearchSourceProviderType.EXA)

    result = await TrendScoringService(session=None).score(
        document,
        use_provider_fallback=True,
    )

    assert result["trend_available"] is True
    assert result["trend_score"] == 91
    assert result["trend_source"] == "serpapi"


async def test_trend_unavailable_does_not_block_pipeline(monkeypatch) -> None:
    class FakeRegistry:
        def __init__(self, session):
            self.session = session

        async def get_trend_score(self, *, query, filters):
            raise RuntimeError("provider failed")

    import app.research.providers.registry as registry_module

    monkeypatch.setattr(registry_module, "ResearchProviderRegistry", FakeRegistry)
    document = _document(ResearchSourceProviderType.EXA)

    result = await TrendScoringService(session=None).score(
        document,
        use_provider_fallback=True,
    )

    assert result["trend_available"] is False
    assert result["trend_failure_reason"] == "Trend not available. This does not block generation."
