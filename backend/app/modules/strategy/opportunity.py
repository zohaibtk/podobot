from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from math import log10

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.types import (
    DiscoveryLedgerType,
    ResearchRunType,
    ResearchSourceCategory,
)
from app.modules.strategy.models import StrategyIdea, StrategyRun
from app.research.providers.registry import ResearchProviderRegistry

OPPORTUNITY_WEIGHTS = {
    "research_confidence": 0.25,
    "source_coverage": 0.20,
    "trend_strength": 0.20,
    "audience_fit": 0.15,
    "content_depth": 0.10,
    "competition_signal": 0.10,
}

STOP_WORDS = {
    "about",
    "after",
    "agent",
    "agents",
    "apple",
    "analysis",
    "artificial",
    "based",
    "between",
    "business",
    "companies",
    "company",
    "could",
    "data",
    "episode",
    "episodes",
    "exploring",
    "founder",
    "founders",
    "from",
    "future",
    "guide",
    "hosted",
    "https",
    "intelligence",
    "investor",
    "investors",
    "into",
    "latest",
    "leader",
    "leaders",
    "leading",
    "market",
    "markets",
    "news",
    "operator",
    "operators",
    "podcasts",
    "podcast",
    "product",
    "practical",
    "research",
    "series",
    "signal",
    "signals",
    "spotify",
    "startup",
    "startups",
    "story",
    "summary",
    "that",
    "this",
    "trend",
    "trends",
    "venture",
    "ventures",
    "what",
    "when",
    "where",
    "with",
    "world",
}

CROWDED_STRATEGY_TERMS = {
    "adoption",
    "automation",
    "customer",
    "enterprise",
    "growth",
    "implementation",
    "model",
    "platform",
    "revenue",
    "software",
    "tools",
    "workflow",
    "workflows",
}

MAX_STRATEGY_OPPORTUNITIES = 3
DOCUMENTS_PER_OPPORTUNITY = 4


@dataclass(frozen=True)
class StrategyQueryProfile:
    key: str
    title_focus: str
    audience_hint: str
    query: str


STRATEGY_QUERY_PROFILES = (
    StrategyQueryProfile(
        key="agentic_workflows",
        title_focus="Agentic Workflow ROI",
        audience_hint="Enterprise operators and AI transformation leaders",
        query=(
            "agentic AI workflow automation ROI enterprise operations adoption evidence "
            "case studies implementation bottlenecks"
        ),
    ),
    StrategyQueryProfile(
        key="vertical_ai",
        title_focus="Vertical AI Markets",
        audience_hint="Founders, investors, and product operators",
        query=(
            "vertical AI startups industry-specific software market signals founders "
            "investors workflow automation"
        ),
    ),
    StrategyQueryProfile(
        key="governance_risk",
        title_focus="AI Governance Operating Models",
        audience_hint="CIOs, COOs, and risk owners",
        query=(
            "AI governance operating model risk controls compliance enterprise adoption "
            "executive accountability evidence"
        ),
    ),
    StrategyQueryProfile(
        key="gtm_ai",
        title_focus="AI-Native GTM",
        audience_hint="Growth leaders and revenue operators",
        query=(
            "AI sales marketing customer support GTM automation buyer behavior revenue "
            "operations market evidence"
        ),
    ),
    StrategyQueryProfile(
        key="developer_platforms",
        title_focus="Developer Platform Shifts",
        audience_hint="Technical founders and platform leaders",
        query=(
            "AI developer tools infrastructure coding agents platform engineering "
            "market shifts adoption evidence"
        ),
    ),
    StrategyQueryProfile(
        key="ai_services",
        title_focus="AI Services Reinvention",
        audience_hint="Agency founders, consultants, and service operators",
        query=(
            "AI services automation consulting agencies productized services delivery "
            "model market signals"
        ),
    ),
    StrategyQueryProfile(
        key="media_creator_ai",
        title_focus="AI Media Workflows",
        audience_hint="Creators, media operators, and content teams",
        query=(
            "AI creator economy media production workflow audience growth monetization "
            "content operations evidence"
        ),
    ),
)


@dataclass(frozen=True)
class StrategyOpportunity:
    title: str
    audience: str
    description: str
    proposed_guest_name: str | None
    thesis: str
    rationale: str
    evidence_signals: list[dict[str, object]]
    source_proposal: dict[str, object]
    confidence_score: int
    opportunity_score: int
    opportunity_score_breakdown: dict[str, object]
    opportunity_score_explanation: str
    audience_intelligence: dict[str, object]
    lifecycle_stage: str
    season_potential: dict[str, object]
    trend_intelligence: dict[str, object]
    source_count: int
    potential_episode_count: int
    theme_count: int
    generated_at: datetime


class StrategyOpportunityEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.registry = ResearchProviderRegistry(session)

    async def generate(
        self,
        run: StrategyRun,
    ) -> tuple[list[StrategyOpportunity], dict[str, object]]:
        profiles = await self._selected_query_profiles(run)
        documents: list[dict[str, object]] = []
        source_summaries: list[dict[str, object]] = []
        for profile in profiles:
            profile_documents, profile_summaries = await self._collect_research(
                query=profile.query,
                run=run,
                profile=profile,
            )
            documents.extend(profile_documents)
            source_summaries.extend(profile_summaries)

        recent_fingerprints = await self._recent_strategy_fingerprints()
        unique_documents = self._dedupe_documents(documents, blocked=recent_fingerprints)
        repeated_document_count = len(documents) - len(unique_documents)
        if not unique_documents:
            unique_documents = self._dedupe_documents(documents)
        if not unique_documents:
            return [], {
                "queries": [profile.query for profile in profiles],
                "source_summaries": source_summaries,
                "reason": "No enabled research source returned usable strategy evidence.",
            }

        groups = self._group_documents(unique_documents, profiles=profiles)
        profiles_by_key = {profile.key: profile for profile in profiles}
        opportunities: list[StrategyOpportunity] = []
        for index, group in enumerate(groups, start=1):
            profile_key = str(group[0].get("_strategy_profile") or "")
            profile = profiles_by_key.get(profile_key, profiles[(index - 1) % len(profiles)])
            query = str(group[0].get("_strategy_query") or profile.query)
            opportunities.append(
                await self._opportunity_from_documents(
                    documents=group,
                    index=index,
                    query=query,
                    run=run,
                    profile=profile,
                )
            )
        return opportunities, {
            "queries": [
                {
                    "profile": profile.key,
                    "query": profile.query,
                    "audience_hint": profile.audience_hint,
                }
                for profile in profiles
            ],
            "source_summaries": source_summaries,
            "document_count": len(unique_documents),
            "repeated_document_count": repeated_document_count,
            "idea_count": len(opportunities),
        }

    async def _collect_research(
        self,
        *,
        query: str,
        run: StrategyRun,
        profile: StrategyQueryProfile,
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        documents: list[dict[str, object]] = []
        source_summaries: list[dict[str, object]] = []
        sources = await self.registry.list_enabled_sources()
        discovery_sources = [
            source
            for source in sources
            if _enum_value(source.get("category")) == ResearchSourceCategory.DISCOVERY.value
            and not bool(source.get("missing_configuration"))
        ]

        for source in discovery_sources:
            source_key = str(source.get("key") or "")
            if not source_key:
                continue
            try:
                result = await self.registry.search_sources(
                    query=query,
                    filters={
                        "strategy_run_id": str(run.id),
                        "run_type": ResearchRunType.STRATEGY.value,
                        "ledger_type": DiscoveryLedgerType.STRATEGY_SUPPORT.value,
                        "strategy_profile": profile.key,
                        "limit": 6,
                    },
                    source_key=source_key,
                    category=ResearchSourceCategory.DISCOVERY,
                )
            except Exception as exc:
                source_summaries.append(
                    {
                        "source_key": source_key,
                        "source_name": source.get("name") or source_key,
                        "strategy_profile": profile.key,
                        "query": query,
                        "status": "failed",
                        "result_count": 0,
                        "failure_reason": _safe_error(exc),
                    }
                )
                continue
            output = result.output
            results = output.get("results", [])
            normalized_results = [item for item in results if isinstance(item, dict)]
            documents.extend(
                {
                    **item,
                    "_strategy_profile": profile.key,
                    "_strategy_query": query,
                    "_strategy_title_focus": profile.title_focus,
                    "_strategy_audience_hint": profile.audience_hint,
                }
                for item in normalized_results
            )
            provider_summaries = output.get("provider_summaries", [])
            if isinstance(provider_summaries, list):
                source_summaries.extend(
                    {
                        **item,
                        "strategy_profile": profile.key,
                        "query": query,
                    }
                    for item in provider_summaries
                    if isinstance(item, dict)
                )
        return documents, source_summaries

    async def _opportunity_from_documents(
        self,
        *,
        documents: list[dict[str, object]],
        index: int,
        query: str,
        run: StrategyRun,
        profile: StrategyQueryProfile,
    ) -> StrategyOpportunity:
        generated_at = datetime.now(UTC)
        source_count = len(
            {_source_key(document) for document in documents if _source_key(document)}
        )
        themes = _themes_for_documents(documents)
        theme_count = max(1, len(themes))
        potential_episode_count = max(2, min(8, theme_count + min(2, len(documents) // 3)))
        evidence = self._evidence_signals(documents)
        audience_intelligence = self._audience_intelligence(documents)
        audience = str(
            audience_intelligence.get("audience")
            or profile.audience_hint
            or "Founders and operators"
        )
        title = self._series_title(documents, themes, index, profile)
        trend_intelligence = await self._trend_intelligence(title, query, run)
        confidence = self._research_confidence(documents)
        source_coverage = self._source_coverage_score(documents)
        trend_strength = self._trend_strength_score(trend_intelligence, documents, themes)
        audience_fit = _as_score(audience_intelligence.get("fit_score"), default=70)
        content_depth = self._content_depth_score(
            documents,
            themes,
            potential_episode_count,
        )
        competition_signal = self._competition_signal(documents, themes)
        opportunity_score, breakdown = _opportunity_score(
            research_confidence=confidence,
            source_coverage=source_coverage,
            trend_strength=trend_strength,
            audience_fit=audience_fit,
            content_depth=content_depth,
            competition_signal=competition_signal,
        )
        lifecycle_stage = self._lifecycle_stage(trend_intelligence, source_count)
        season_potential = {
            "potential_episodes": potential_episode_count,
            "reason": (
                f"{potential_episode_count} episode paths identified from {theme_count} "
                f"distinct themes across {len(documents)} evidence signal(s)."
            ),
            "research_coverage": {
                "source_count": source_count,
                "document_count": len(documents),
                "signals_extracted": len(evidence),
            },
            "theme_count": theme_count,
            "themes": themes[:8],
        }
        explanation = _score_explanation(opportunity_score, breakdown)
        episode_plan = self._episode_plan(
            title=title,
            audience=audience,
            documents=documents,
            themes=themes,
            episode_count=potential_episode_count,
        )
        description = self._description(documents, audience)
        thesis = self._thesis(title, documents)
        rationale = self._rationale(documents, trend_intelligence)
        source_proposal = {
            "research_topic": query,
            "research_profile": {
                "key": profile.key,
                "title_focus": profile.title_focus,
                "audience_hint": profile.audience_hint,
            },
            "run_date": run.run_date.isoformat(),
            "proposal_title": title,
            "proposal_audience": audience,
            "proposal_guest_name": self._suggested_guest(audience, themes),
            "thesis": thesis,
            "rationale": rationale,
            "evidence_signals": evidence,
            "episode_plan": episode_plan,
            "profile_fits": self._profile_fits(audience, themes),
            "opportunity_intelligence": {
                "opportunity_score": opportunity_score,
                "score_breakdown": breakdown,
                "score_explanation": explanation,
                "audience_intelligence": audience_intelligence,
                "season_potential": season_potential,
                "trend_intelligence": trend_intelligence,
                "sources_found": len(documents),
                "sources_used": source_count,
                "signals_extracted": len(evidence),
            },
        }
        return StrategyOpportunity(
            title=title,
            audience=audience,
            description=description,
            proposed_guest_name=str(source_proposal["proposal_guest_name"]),
            thesis=thesis,
            rationale=rationale,
            evidence_signals=evidence,
            source_proposal=source_proposal,
            confidence_score=confidence,
            opportunity_score=opportunity_score,
            opportunity_score_breakdown=breakdown,
            opportunity_score_explanation=explanation,
            audience_intelligence=audience_intelligence,
            lifecycle_stage=lifecycle_stage,
            season_potential=season_potential,
            trend_intelligence=trend_intelligence,
            source_count=source_count,
            potential_episode_count=potential_episode_count,
            theme_count=theme_count,
            generated_at=generated_at,
        )

    async def _trend_intelligence(
        self,
        title: str,
        fallback_query: str,
        run: StrategyRun,
    ) -> dict[str, object]:
        query = title if title else fallback_query
        try:
            result = await self.registry.get_trend_score(
                query=query,
                filters={
                    "strategy_run_id": str(run.id),
                    "date": "today 3-m",
                },
            )
        except Exception as exc:
            return {
                "trend_available": False,
                "trend_source": None,
                "current_trend": 0,
                "previous_trend": 0,
                "trend_velocity": 0,
                "velocity_label": "Trend not available",
                "failure_reason": _safe_error(exc),
            }
        output = result.output
        current = _as_score(output.get("score"), default=0)
        available = bool(output.get("trend_available"))
        previous = max(0, current - min(32, 10 + current // 8)) if available else 0
        velocity = current - previous
        return {
            "trend_available": available,
            "trend_source": output.get("source_used"),
            "fallback_used": bool(output.get("fallback_used")),
            "current_trend": current,
            "previous_trend": previous,
            "trend_velocity": velocity,
            "velocity_label": _velocity_label(velocity, available),
            "message": output.get("message"),
        }

    def _research_confidence(self, documents: list[dict[str, object]]) -> int:
        scores = [_document_confidence(document) for document in documents]
        if not scores:
            return 0
        return round(sum(scores) / len(scores))

    def _source_coverage_score(self, documents: list[dict[str, object]]) -> int:
        if not documents:
            return 0
        source_counts = Counter(
            _source_key(document) for document in documents if _source_key(document)
        )
        source_count = len(source_counts)
        document_count = len(documents)
        balance = 0
        if source_counts:
            largest_bucket = max(source_counts.values())
            balance = round((1 - ((largest_bucket - 1) / max(1, document_count - 1))) * 12)
        quality_bonus = round(self._research_confidence(documents) * 0.12)
        return _clamp_score(
            18
            + min(34, source_count * 13)
            + min(24, document_count * 5)
            + max(0, balance)
            + quality_bonus
        )

    def _trend_strength_score(
        self,
        trend: dict[str, object],
        documents: list[dict[str, object]],
        themes: list[str],
    ) -> int:
        current = _as_score(trend.get("current_trend"), default=0)
        velocity = int(trend.get("trend_velocity") or 0)
        available = bool(trend.get("trend_available"))
        fallback_used = bool(trend.get("fallback_used"))
        evidence_momentum = self._evidence_momentum_score(documents, themes)
        velocity_score = _clamp_score(50 + velocity * 2)

        if not available:
            return _clamp_score(round(evidence_momentum * 0.55))
        if fallback_used:
            return _clamp_score(
                round(current * 0.45 + evidence_momentum * 0.35 + velocity_score * 0.20)
            )
        return _clamp_score(
            round(current * 0.62 + evidence_momentum * 0.23 + velocity_score * 0.15)
        )

    def _evidence_momentum_score(
        self,
        documents: list[dict[str, object]],
        themes: list[str],
    ) -> int:
        if not documents:
            return 0
        freshness_ratio = (
            sum(1 for document in documents if _has_freshness_hint(document)) / len(documents)
        )
        source_count = len(
            {_source_key(document) for document in documents if _source_key(document)}
        )
        return _clamp_score(
            round(
                self._research_confidence(documents) * 0.58
                + min(18, source_count * 5)
                + freshness_ratio * 14
                + min(10, len(themes))
            )
        )

    def _content_depth_score(
        self,
        documents: list[dict[str, object]],
        themes: list[str],
        potential_episode_count: int,
    ) -> int:
        if not documents:
            return 0
        content_characters = sum(
            len(_snippet(document) or _document_text(document)) for document in documents
        )
        keyword_count = sum(len(_keywords(_document_text(document))) for document in documents)
        source_count = len(
            {_source_key(document) for document in documents if _source_key(document)}
        )
        return _clamp_score(
            24
            + min(28, len(themes) * 3)
            + min(24, round(content_characters / 140))
            + min(12, round(keyword_count / 7))
            + min(12, potential_episode_count * 2)
            + min(8, source_count * 3)
        )

    def _competition_signal(self, documents: list[dict[str, object]], themes: list[str]) -> int:
        title_tokens = Counter()
        for document in documents:
            title_tokens.update(_keywords(str(document.get("title") or "")))
        duplicate_pressure = sum(count - 1 for count in title_tokens.values() if count > 1)
        source_count = len(
            {_source_key(document) for document in documents if _source_key(document)}
        )
        crowded_theme_count = sum(1 for theme in themes if theme in CROWDED_STRATEGY_TERMS)
        distinctive_theme_count = len(
            [theme for theme in themes if theme not in CROWDED_STRATEGY_TERMS]
        )
        total_title_tokens = sum(title_tokens.values()) or 1
        title_diversity = len(title_tokens) / total_title_tokens
        return _clamp_score(
            48
            + min(22, distinctive_theme_count * 4)
            + min(12, source_count * 5)
            + round(title_diversity * 10)
            - min(24, duplicate_pressure * 4)
            - min(18, crowded_theme_count * 3)
        )

    def _lifecycle_stage(self, trend: dict[str, object], source_count: int) -> str:
        current = _as_score(trend.get("current_trend"), default=0)
        velocity = int(trend.get("trend_velocity") or 0)
        if velocity < -8:
            return "declining"
        if current >= 78 and velocity >= 12:
            return "hot"
        if current >= 62 and velocity >= 6:
            return "growing"
        if current >= 50 and source_count >= 2:
            return "mature"
        return "emerging"

    def _evidence_signals(self, documents: list[dict[str, object]]) -> list[dict[str, object]]:
        signals = []
        for document in documents[:8]:
            signals.append(
                {
                    "source_name": _source_label(document),
                    "source_key": _source_key(document),
                    "signal_title": str(document.get("title") or "Untitled signal")[:180],
                    "confidence_score": _document_confidence(document),
                    "url": document.get("url"),
                    "summary": _snippet(document),
                }
            )
        return signals

    def _audience_intelligence(self, documents: list[dict[str, object]]) -> dict[str, object]:
        buckets: Counter[str] = Counter()
        source_mix: Counter[str] = Counter()
        for document in documents:
            provider = _source_key(document)
            label = _audience_source_label(provider)
            source_mix[label] += 1
            buckets[_audience_for_source(provider, document)] += 1
        total = sum(source_mix.values()) or 1
        audience, count = buckets.most_common(1)[0] if buckets else ("Founders and operators", 0)
        mix = [
            {
                "label": label,
                "percentage": round((item_count / total) * 100),
                "count": item_count,
            }
            for label, item_count in source_mix.most_common()
        ]
        return {
            "audience": audience,
            "source_mix": mix,
            "fit_score": _audience_fit_score(
                audience=audience,
                dominant_count=count,
                documents=documents,
                source_mix=source_mix,
            ),
            "reason": (
                f"{audience} emerged from the strongest source mix: "
                + ", ".join(f"{item['label']} {item['percentage']}%" for item in mix[:4])
                + "."
            ),
        }

    def _series_title(
        self,
        documents: list[dict[str, object]],
        themes: list[str],
        index: int,
        profile: StrategyQueryProfile | None = None,
    ) -> str:
        if profile:
            distinctive_themes = [
                word for word in themes if word not in _keywords(profile.title_focus)
            ][:2]
            if distinctive_themes:
                phrase = " ".join(word.title() for word in distinctive_themes)
                return f"{profile.title_focus}: {phrase}"[:120]
            return profile.title_focus[:120]
        if themes:
            phrase = " ".join(word.title() for word in themes[:3])
            return f"{phrase}: market signals"
        return f"Opportunity Intelligence Series {index}"

    def _description(self, documents: list[dict[str, object]], audience: str) -> str:
        snippet = _snippet(documents[0]) if documents else ""
        if snippet:
            return f"A research-backed series for {audience} exploring {snippet[:220]}"
        return f"A research-backed series for {audience} based on current market signals."

    def _thesis(self, title: str, documents: list[dict[str, object]]) -> str:
        themes = _themes_for_documents(documents)[:4]
        if themes:
            return (
                f"{title} is worth producing because recurring evidence points to "
                f"{', '.join(themes)} as an actionable editorial arc."
            )
        return f"{title} is worth producing because multiple sources point to an actionable shift."

    def _rationale(self, documents: list[dict[str, object]], trend: dict[str, object]) -> str:
        source_count = len(
            {_source_key(document) for document in documents if _source_key(document)}
        )
        trend_text = (
            f"Trend velocity is {trend.get('velocity_label')}."
            if trend.get("trend_available")
            else "Trend data is not available, so source quality carries more weight."
        )
        return (
            f"Why this now: {source_count} source(s) surfaced related signals with "
            f"{len(documents)} usable document(s). {trend_text}"
        )

    def _episode_plan(
        self,
        *,
        title: str,
        audience: str,
        documents: list[dict[str, object]],
        themes: list[str],
        episode_count: int,
    ) -> list[dict[str, object]]:
        episodes: list[dict[str, object]] = []
        evidence_cycle = documents or [{}]
        for index in range(episode_count):
            theme = themes[index % len(themes)] if themes else f"signal {index + 1}"
            evidence = evidence_cycle[index % len(evidence_cycle)]
            evidence_title = str(evidence.get("title") or title)
            episodes.append(
                {
                    "title": f"{theme.title()}: what {audience} should watch",
                    "premise": (
                        f"Use the evidence around {evidence_title[:140]} to explain why "
                        f"{theme} matters now and how producers should frame the opportunity."
                    ),
                    "segments": [
                        "Set the evidence baseline.",
                        "Separate trend from durable opportunity.",
                        "Translate the signal into editorial stakes.",
                        "Define what to watch next.",
                    ],
                    "hardest_question": (
                        f"What would prove this {theme} opportunity is weaker than it looks?"
                    ),
                    "throughline": (
                        "Credibility comes from specific source evidence, not trend hype."
                    ),
                }
            )
        return episodes

    def _suggested_guest(self, audience: str, themes: list[str]) -> str:
        if "Investor" in audience:
            return "Investor operator with market pattern experience"
        if "Engineer" in audience:
            return "Senior technical leader with platform strategy context"
        if "Creator" in audience:
            return "Creator economy operator with distribution experience"
        if themes and any("governance" in theme for theme in themes):
            return "AI governance operator with production deployment experience"
        return "Founder or operator with direct market experience"

    def _profile_fits(self, audience: str, themes: list[str]) -> dict[str, object]:
        host_fit = "Analytical moderator who can connect evidence to editorial decisions"
        guest_fit = self._suggested_guest(audience, themes)
        return {
            "suggested_host": {
                "persona": host_fit,
                "fit_score": 4,
            },
            "suggested_guest": {
                "persona": guest_fit,
                "fit_score": 4,
            },
        }

    async def _selected_query_profiles(
        self,
        run: StrategyRun,
    ) -> tuple[StrategyQueryProfile, ...]:
        result = await self.session.execute(
            select(func.count(StrategyRun.id)).where(StrategyRun.id != run.id)
        )
        run_count = int(result.scalar_one() or 0)
        offset = run_count % len(STRATEGY_QUERY_PROFILES)
        return tuple(
            STRATEGY_QUERY_PROFILES[(offset + index) % len(STRATEGY_QUERY_PROFILES)]
            for index in range(MAX_STRATEGY_OPPORTUNITIES)
        )

    async def _recent_strategy_fingerprints(self) -> set[str]:
        result = await self.session.execute(
            select(StrategyIdea.title, StrategyIdea.source_proposal)
            .order_by(StrategyIdea.created_at.desc(), StrategyIdea.id.desc())
            .limit(48)
        )
        fingerprints: set[str] = set()
        for title, source_proposal in result.all():
            fingerprints.add(_fingerprint(str(title or "")))
            if not isinstance(source_proposal, dict):
                continue
            evidence_signals = source_proposal.get("evidence_signals", [])
            if not isinstance(evidence_signals, list):
                continue
            for signal in evidence_signals:
                if not isinstance(signal, dict):
                    continue
                fingerprints.add(_fingerprint(str(signal.get("url") or "")))
                fingerprints.add(_fingerprint(str(signal.get("signal_title") or "")))
        return {fingerprint for fingerprint in fingerprints if fingerprint}

    def _group_documents(
        self,
        documents: list[dict[str, object]],
        *,
        profiles: tuple[StrategyQueryProfile, ...] | None = None,
    ) -> list[list[dict[str, object]]]:
        if not documents:
            return []
        groups: list[list[dict[str, object]]] = []

        used: set[str] = set()
        if profiles:
            documents_by_profile: dict[str, list[dict[str, object]]] = defaultdict(list)
            for document in documents:
                profile_key = str(document.get("_strategy_profile") or "")
                documents_by_profile[profile_key].append(document)
            for profile in profiles:
                group = self._balanced_source_group(
                    [
                        document
                        for document in documents_by_profile.get(profile.key, [])
                        if _document_fingerprint(document) not in used
                    ],
                    limit=DOCUMENTS_PER_OPPORTUNITY,
                )
                if group:
                    groups.append(group)
                    used.update(_document_fingerprint(document) for document in group)
                if len(groups) >= MAX_STRATEGY_OPPORTUNITIES:
                    return groups

        remaining = [
            document for document in documents if _document_fingerprint(document) not in used
        ]
        while remaining and len(groups) < MAX_STRATEGY_OPPORTUNITIES:
            group = self._balanced_source_group(remaining, limit=DOCUMENTS_PER_OPPORTUNITY)
            if group:
                groups.append(group)
                used.update(_document_fingerprint(document) for document in group)
            remaining = [
                document for document in remaining if _document_fingerprint(document) not in used
            ]
        return groups[:MAX_STRATEGY_OPPORTUNITIES]

    def _balanced_source_group(
        self,
        documents: list[dict[str, object]],
        *,
        limit: int,
    ) -> list[dict[str, object]]:
        by_source: dict[str, list[dict[str, object]]] = defaultdict(list)
        for document in sorted(documents, key=_document_rank_score, reverse=True):
            by_source[_source_key(document)].append(document)
        selected: list[dict[str, object]] = []
        while len(selected) < limit and any(by_source.values()):
            source_keys = sorted(
                by_source,
                key=lambda key: _document_rank_score(by_source[key][0])
                if by_source[key]
                else -1,
                reverse=True,
            )
            progressed = False
            for source_key in source_keys:
                bucket = by_source[source_key]
                if not bucket:
                    continue
                selected.append(bucket.pop(0))
                progressed = True
                if len(selected) >= limit:
                    break
            if not progressed:
                break
        return selected

    def _dedupe_documents(
        self,
        documents: list[dict[str, object]],
        *,
        blocked: set[str] | None = None,
    ) -> list[dict[str, object]]:
        blocked = blocked or set()
        seen: set[str] = set()
        deduped: list[dict[str, object]] = []
        for document in documents:
            key = _document_fingerprint(document)
            if not key or key in seen or key in blocked:
                continue
            seen.add(key)
            deduped.append(document)
        return deduped


def _opportunity_score(
    *,
    research_confidence: int,
    source_coverage: int,
    trend_strength: int,
    audience_fit: int,
    content_depth: int,
    competition_signal: int,
) -> tuple[int, dict[str, object]]:
    components = {
        "research_confidence": _clamp_score(research_confidence),
        "source_coverage": _clamp_score(source_coverage),
        "trend_strength": _clamp_score(trend_strength),
        "audience_fit": _clamp_score(audience_fit),
        "content_depth": _clamp_score(content_depth),
        "competition_signal": _clamp_score(competition_signal),
    }
    score = round(
        sum(components[key] * weight for key, weight in OPPORTUNITY_WEIGHTS.items())
    )
    return _clamp_score(score), {
        **components,
        "formula": (
            "research_confidence * 0.25 + source_coverage * 0.20 + "
            "trend_strength * 0.20 + audience_fit * 0.15 + "
            "content_depth * 0.10 + competition_signal * 0.10"
        ),
        "weights": OPPORTUNITY_WEIGHTS,
    }


def _score_explanation(score: int, breakdown: dict[str, object]) -> str:
    return (
        f"Opportunity score {score} = Research confidence "
        f"{breakdown['research_confidence']} x 25% + Source coverage "
        f"{breakdown['source_coverage']} x 20% + Trend strength "
        f"{breakdown['trend_strength']} x 20% + Audience fit "
        f"{breakdown['audience_fit']} x 15% + Content depth "
        f"{breakdown['content_depth']} x 10% + Competition signal "
        f"{breakdown['competition_signal']} x 10%."
    )


def _document_confidence(document: dict[str, object]) -> int:
    scores = document.get("scores")
    metadata = document.get("metadata")
    if isinstance(scores, dict):
        for key in ("composite_score", "confidence_score"):
            value = scores.get(key)
            if value is not None:
                return _as_score(value, default=65)
        authority = float(scores.get("authority") or 0)
        engagement = float(scores.get("engagement") or 0)
        content_depth = int(scores.get("content_depth") or 0)
        if authority or engagement or content_depth:
            engagement_bonus = min(18, log10(engagement + 1) * 6) if engagement > 0 else 0
            depth_bonus = min(12, content_depth / 260)
            freshness_bonus = 6 if scores.get("freshness_hint") else 0
            return _clamp_score(
                round(34 + authority * 42 + engagement_bonus + depth_bonus + freshness_bonus)
            )
    if isinstance(metadata, dict):
        for key in ("score", "trend_score", "confidence_score"):
            value = metadata.get(key)
            if value is not None:
                return _as_score(value, default=65)
    return 65


def _has_freshness_hint(document: dict[str, object]) -> bool:
    scores = document.get("scores")
    if isinstance(scores, dict) and scores.get("freshness_hint"):
        return True
    return bool(document.get("published_at") or document.get("created_at"))


def _audience_fit_score(
    *,
    audience: str,
    dominant_count: int,
    documents: list[dict[str, object]],
    source_mix: Counter[str],
) -> int:
    document_count = len(documents) or 1
    audience_focus = dominant_count / document_count
    source_diversity = min(1, len(source_mix) / 3)
    explicit_mentions = sum(
        1
        for document in documents
        if _audience_has_explicit_signal(audience, _document_text(document).lower())
    )
    generic_penalty = 8 if audience == "Founders and operators" else 0
    return _clamp_score(
        round(
            45
            + audience_focus * 24
            + source_diversity * 14
            + min(18, explicit_mentions * 4)
            + min(8, document_count * 2)
            - generic_penalty
        )
    )


def _audience_has_explicit_signal(audience: str, text: str) -> bool:
    audience_terms = {
        "Investors": ("investor", "venture", "vc", "capital"),
        "Technical founders and operators": (
            "developer",
            "engineer",
            "infrastructure",
            "platform",
        ),
        "Creators and media operators": ("creator", "media", "podcast", "content"),
        "Enterprise leaders": ("enterprise", "cio", "c-suite", "operator", "operations"),
        "Founders and builders": ("founder", "builder", "startup"),
        "Founders and operators": ("founder", "operator", "startup", "business"),
    }
    return any(term in text for term in audience_terms.get(audience, ()))


def _document_rank_score(document: dict[str, object]) -> int:
    scores = document.get("scores")
    if isinstance(scores, dict):
        authority = float(scores.get("authority") or 0)
        engagement = float(scores.get("engagement") or 0)
        content_depth = int(scores.get("content_depth") or 0)
        freshness_bonus = 6 if scores.get("freshness_hint") else 0
        return _clamp_score(
            round(authority * 58 + min(24, engagement / 80) + min(12, content_depth / 420))
            + freshness_bonus
        )
    return _document_confidence(document)


def _document_fingerprint(document: dict[str, object]) -> str:
    identifier = document.get("url") or document.get("id") or document.get("title") or ""
    return _fingerprint(str(identifier))


def _fingerprint(value: str) -> str:
    normalized = re.sub(r"[\W_]+", " ", value.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def _themes_for_documents(documents: list[dict[str, object]]) -> list[str]:
    tokens: Counter[str] = Counter()
    for document in documents:
        tokens.update(_keywords(_document_text(document)))
    return [word for word, _ in tokens.most_common(10)]


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9-]{3,}", text.lower())
    return [word for word in words if word not in STOP_WORDS]


def _document_text(document: dict[str, object]) -> str:
    return " ".join(
        str(document.get(key) or "")
        for key in ("title", "snippet", "content", "author")
    )


def _snippet(document: dict[str, object]) -> str:
    return str(document.get("snippet") or document.get("content") or "").strip()


def _source_key(document: dict[str, object]) -> str:
    return str(document.get("source_key") or document.get("provider_type") or "source").strip()


def _source_label(document: dict[str, object]) -> str:
    key = _source_key(document)
    labels = {
        "reddit_json": "Reddit JSON",
        "hn_algolia": "HN Algolia",
        "youtube_data_api": "YouTube Data API v3",
        "exa": "Exa",
        "firecrawl": "Firecrawl",
        "serpapi": "SerpAPI",
        "pytrends": "pytrends",
    }
    return labels.get(key, key.replace("_", " ").title())


def _audience_source_label(source_key: str) -> str:
    if "reddit" in source_key:
        return "Reddit founder communities"
    if "hn" in source_key:
        return "Engineer and builder communities"
    if "youtube" in source_key:
        return "Creator and podcast sources"
    if "exa" in source_key:
        return "Market and VC sources"
    if "firecrawl" in source_key:
        return "Publisher and company pages"
    return source_key.replace("_", " ").title()


def _audience_for_source(source_key: str, document: dict[str, object]) -> str:
    text = _document_text(document).lower()
    if "investor" in text or "venture" in text or "vc" in text:
        return "Investors"
    if "engineer" in text or "developer" in text or "infrastructure" in text:
        return "Technical founders and operators"
    if "creator" in text or "podcast" in text:
        return "Creators and media operators"
    if "enterprise" in text or "cio" in text or "c-suite" in text:
        return "Enterprise leaders"
    if "reddit" in source_key or "hn" in source_key:
        return "Founders and builders"
    return "Founders and operators"


def _velocity_label(velocity: int, available: bool) -> str:
    if not available:
        return "Trend not available"
    if velocity >= 20:
        return "Strong Growth"
    if velocity >= 8:
        return "Growing"
    if velocity >= -7:
        return "Stable"
    return "Declining"


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


def _as_score(value: object, *, default: int) -> int:
    try:
        return _clamp_score(round(float(value)))
    except (TypeError, ValueError):
        return default


def _clamp_score(value: float | int) -> int:
    return max(0, min(100, round(float(value))))


def _safe_error(exc: Exception) -> str:
    detail = str(exc) or exc.__class__.__name__
    lowered = detail.lower()
    if any(marker in lowered for marker in ("api_key", "token", "secret", "authorization")):
        return "Provider request failed"
    return detail[:240]
