from app.modules.strategy.opportunity import (
    StrategyOpportunityEngine,
    StrategyQueryProfile,
    _fingerprint,
    _opportunity_score,
    _themes_for_documents,
)


def _engine() -> StrategyOpportunityEngine:
    return object.__new__(StrategyOpportunityEngine)


def _document(
    title: str,
    *,
    source_key: str,
    profile: StrategyQueryProfile,
    url: str | None = None,
    content: str | None = None,
    authority: float | None = None,
    engagement: float | None = None,
    content_depth: int = 900,
    freshness_hint: str | None = None,
) -> dict[str, object]:
    body = content or (
        "Enterprise AI operators are testing workflow automation, governance, "
        "and measurable adoption signals."
    )
    default_authority = 0.7 if source_key == "exa" else 0.65
    default_engagement = 80 if source_key == "youtube_data_api" else 20
    return {
        "title": title,
        "url": url or f"https://example.com/{source_key}/{title.lower().replace(' ', '-')}",
        "content": body,
        "snippet": body[:180],
        "source_key": source_key,
        "_strategy_profile": profile.key,
        "_strategy_query": profile.query,
        "scores": {
            "authority": authority if authority is not None else default_authority,
            "engagement": engagement if engagement is not None else default_engagement,
            "content_depth": content_depth,
            "freshness_hint": freshness_hint,
        },
    }


def test_strategy_titles_are_synthesized_instead_of_copying_source_titles() -> None:
    engine = _engine()
    profile = StrategyQueryProfile(
        key="governance_risk",
        title_focus="AI Governance Operating Models",
        audience_hint="CIOs and risk owners",
        query="AI governance operating model risk controls adoption evidence",
    )
    documents = [
        _document(
            "Artificial Intelligence in Business | Podcast Series | BCG",
            source_key="exa",
            profile=profile,
        )
    ]

    title = engine._series_title(documents, _themes_for_documents(documents), 1, profile)

    assert title.startswith("AI Governance Operating Models")
    assert title != "Artificial Intelligence in Business"
    assert "Podcast" not in title


def test_strategy_grouping_keeps_profiles_and_sources_diverse() -> None:
    engine = _engine()
    profile_a = StrategyQueryProfile(
        key="agentic_workflows",
        title_focus="Agentic Workflow ROI",
        audience_hint="Operators",
        query="agentic workflow automation ROI",
    )
    profile_b = StrategyQueryProfile(
        key="vertical_ai",
        title_focus="Vertical AI Markets",
        audience_hint="Founders",
        query="vertical AI market signals",
    )
    documents = [
        _document("Agent workflow case study", source_key="exa", profile=profile_a),
        _document(
            "Agent workflow operator evidence",
            source_key="youtube_data_api",
            profile=profile_a,
        ),
        _document("Vertical AI funding signal", source_key="exa", profile=profile_b),
        _document("Vertical AI buyer workflow", source_key="youtube_data_api", profile=profile_b),
    ]

    groups = engine._group_documents(documents, profiles=(profile_a, profile_b))

    assert [group[0]["_strategy_profile"] for group in groups] == [
        "agentic_workflows",
        "vertical_ai",
    ]
    assert all(
        {document["source_key"] for document in group} == {"exa", "youtube_data_api"}
        for group in groups
    )


def test_strategy_dedupe_skips_recently_used_documents() -> None:
    engine = _engine()
    profile = StrategyQueryProfile(
        key="gtm_ai",
        title_focus="AI-Native GTM",
        audience_hint="Growth leaders",
        query="AI GTM automation evidence",
    )
    repeated = _document(
        "Repeated source",
        source_key="exa",
        profile=profile,
        url="https://example.com/repeated",
    )
    fresh = _document(
        "Fresh source",
        source_key="exa",
        profile=profile,
        url="https://example.com/fresh",
    )

    deduped = engine._dedupe_documents(
        [repeated, fresh],
        blocked={_fingerprint("https://example.com/repeated")},
    )

    assert [document["title"] for document in deduped] == ["Fresh source"]


def test_strategy_scoring_components_vary_with_evidence_strength() -> None:
    engine = _engine()
    profile = StrategyQueryProfile(
        key="agentic_workflows",
        title_focus="Agentic Workflow ROI",
        audience_hint="Enterprise operators",
        query="agentic workflow automation ROI",
    )
    strong_content = (
        "Enterprise CIO operators are funding agentic workflow pilots with measurable "
        "ROI, procurement evidence, governance controls, deployment benchmarks, and "
        "fresh operating-model case studies."
    )
    weak_content = "Generic AI automation summary."
    strong_documents = [
        _document(
            "Agentic workflow ROI benchmark",
            source_key="exa",
            profile=profile,
            content=strong_content,
            authority=0.84,
            engagement=1800,
            content_depth=2200,
            freshness_hint="2026-06-01",
        ),
        _document(
            "Enterprise agent operating model",
            source_key="youtube_data_api",
            profile=profile,
            content=strong_content,
            authority=0.72,
            engagement=2600,
            content_depth=1800,
            freshness_hint="2026-06-02",
        ),
        _document(
            "AI workflow governance case study",
            source_key="firecrawl",
            profile=profile,
            content=strong_content,
            authority=0.68,
            engagement=420,
            content_depth=1600,
            freshness_hint="2026-06-03",
        ),
        _document(
            "Automation ROI adoption signal",
            source_key="hn_algolia",
            profile=profile,
            content=strong_content,
            authority=0.63,
            engagement=880,
            content_depth=1400,
            freshness_hint="2026-06-04",
        ),
    ]
    weak_documents = [
        _document(
            "AI automation overview",
            source_key="firecrawl",
            profile=profile,
            content=weak_content,
            authority=0.42,
            engagement=0,
            content_depth=80,
        ),
        _document(
            "AI automation overview update",
            source_key="firecrawl",
            profile=profile,
            content=weak_content,
            authority=0.42,
            engagement=0,
            content_depth=80,
        ),
    ]
    strong_themes = _themes_for_documents(strong_documents)
    weak_themes = _themes_for_documents(weak_documents)

    strong_score, strong_breakdown = _opportunity_score(
        research_confidence=engine._research_confidence(strong_documents),
        source_coverage=engine._source_coverage_score(strong_documents),
        trend_strength=engine._trend_strength_score(
            {"trend_available": True, "current_trend": 28, "trend_velocity": 14},
            strong_documents,
            strong_themes,
        ),
        audience_fit=engine._audience_intelligence(strong_documents)["fit_score"],
        content_depth=engine._content_depth_score(strong_documents, strong_themes, 8),
        competition_signal=engine._competition_signal(strong_documents, strong_themes),
    )
    weak_score, weak_breakdown = _opportunity_score(
        research_confidence=engine._research_confidence(weak_documents),
        source_coverage=engine._source_coverage_score(weak_documents),
        trend_strength=engine._trend_strength_score(
            {"trend_available": True, "current_trend": 4, "trend_velocity": 1},
            weak_documents,
            weak_themes,
        ),
        audience_fit=engine._audience_intelligence(weak_documents)["fit_score"],
        content_depth=engine._content_depth_score(weak_documents, weak_themes, 2),
        competition_signal=engine._competition_signal(weak_documents, weak_themes),
    )

    assert strong_score > weak_score + 18
    assert strong_breakdown["source_coverage"] > weak_breakdown["source_coverage"]
    assert strong_breakdown["trend_strength"] > weak_breakdown["trend_strength"]
    assert strong_breakdown["content_depth"] > weak_breakdown["content_depth"]
