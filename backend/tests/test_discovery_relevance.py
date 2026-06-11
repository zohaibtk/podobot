from types import SimpleNamespace

from app.modules.discovery.service import DiscoveryService


def test_discovery_ranker_prefers_description_relevant_documents_and_dedupes() -> None:
    service = DiscoveryService(session=None)  # type: ignore[arg-type]
    series = SimpleNamespace(
        name="Local Loyalty",
        audience="Independent coffee shop owners",
        description="Customer loyalty programs for independent coffee shops",
        guest_name=None,
    )
    rows = [
        (
            _document(
                title="Enterprise AI agents implementation guide",
                summary="Autonomous AI agents and enterprise governance patterns.",
                url="https://example.com/ai-agents",
                composite_score=96,
            ),
            _source("exa"),
        ),
        (
            _document(
                title="Coffee shop loyalty program playbook",
                summary="Independent cafes use customer loyalty programs to retain local regulars.",
                url="https://example.com/coffee-loyalty?utm=one",
                composite_score=68,
            ),
            _source("exa"),
        ),
        (
            _document(
                title="Coffee shop loyalty program playbook",
                summary="Independent cafes use customer loyalty programs to retain local regulars.",
                url="https://example.com/coffee-loyalty?utm=two",
                composite_score=67,
            ),
            _source("exa"),
        ),
    ]

    ranked = service._rank_documents_for_series(series, rows)

    assert ranked[0][0].title == "Coffee shop loyalty program playbook"
    assert len(ranked) == 1


def test_discovery_ranker_balances_relevant_sources() -> None:
    service = DiscoveryService(session=None)  # type: ignore[arg-type]
    series = SimpleNamespace(
        name="Local Loyalty",
        audience="Independent coffee shop owners",
        description="Customer loyalty programs for independent coffee shops",
        guest_name=None,
    )
    rows = [
        (
            _document(
                title="Coffee loyalty benchmark",
                summary="Independent coffee shops use loyalty rewards to retain regulars.",
                url="https://example.com/exa-1",
                composite_score=96,
            ),
            _source("exa"),
        ),
        (
            _document(
                title="Coffee loyalty app playbook",
                summary="Cafe owners compare punch cards, apps, and SMS loyalty programs.",
                url="https://example.com/exa-2",
                composite_score=95,
            ),
            _source("exa"),
        ),
        (
            _document(
                title="Coffee shops test SMS loyalty",
                summary="Independent cafe teams are using SMS rewards for repeat visits.",
                url="https://example.com/hn-1",
                composite_score=72,
            ),
            _source("hn"),
        ),
        (
            _document(
                title="Cafe owners share loyalty rewards",
                summary="Community operators discuss loyalty programs and local regulars.",
                url="https://example.com/reddit-1",
                composite_score=70,
            ),
            _source("reddit"),
        ),
    ]

    ranked = service._rank_documents_for_series(series, rows)

    assert len({source.id for _, source in ranked[:3]}) == 3


def test_discovery_narrative_candidates_use_description_and_signals() -> None:
    service = DiscoveryService(session=None)  # type: ignore[arg-type]
    series = SimpleNamespace(
        name="Local Loyalty",
        audience="Independent coffee shop owners",
        description="A focused series on customer loyalty programs for independent coffee shops.",
        guest_name=None,
    )
    ledger = [
        _ledger_entry(
            title="Cafes use SMS rewards to retain regulars",
            summary="Neighborhood cafes are pairing mobile rewards with loyalty programs.",
            source="Community Signal",
            confidence=88,
        ),
        _ledger_entry(
            title="Punch cards are moving into lightweight apps",
            summary="Operators want loyalty tools without enterprise CRM overhead.",
            source="Retail Radar",
            confidence=80,
        ),
    ]

    candidates = service._narrative_candidates(series, ledger, generation=1)
    regenerated = service._narrative_candidates(series, ledger, generation=2)
    combined = " ".join(" ".join(candidate) for candidate in candidates).lower()

    assert len(candidates) == 3
    assert "loyalty" in combined
    assert "coffee shops" in combined
    assert "sms rewards" in combined
    assert "evidence to operating cadence" not in combined
    assert {candidate[0] for candidate in candidates} != {
        candidate[0] for candidate in regenerated
    }


def _document(
    *,
    title: str,
    summary: str,
    url: str,
    composite_score: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        title=title,
        content_excerpt=summary,
        normalized_content=summary,
        author=None,
        url=url,
        composite_score=composite_score,
        engagement_score=50,
    )


def _source(source_id: str) -> SimpleNamespace:
    return SimpleNamespace(id=source_id)


def _ledger_entry(
    *,
    title: str,
    summary: str,
    source: str,
    confidence: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        source_name=source,
        signal_title=title,
        signal_summary=summary,
        confidence_score=confidence,
    )
