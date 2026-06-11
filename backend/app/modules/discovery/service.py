import re
from collections.abc import Iterable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.types import (
    DiscoveryLedgerType,
    DiscoverySourceStatus,
    DiscoveryStatus,
    NarrativeStatus,
    SeriesStage,
    SeriesStatus,
)
from app.modules.discovery.models import DiscoveryLedgerEntry
from app.modules.narratives.models import Narrative
from app.modules.research.models import ResearchDocument, ResearchRun
from app.modules.research.service import ResearchPersistenceService
from app.modules.research_sources.models import ResearchSource
from app.modules.series.service import SeriesService
from app.research.providers.registry import ResearchProviderRegistry


class DiscoveryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.series_service = SeriesService(session)

    async def get_workspace(self, series_id: UUID):
        series = await self.series_service.get_series(series_id)
        if series.discovery_status == DiscoveryStatus.RUNNING and not await self._ledger(series.id):
            series.discovery_status = DiscoveryStatus.PENDING
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def run_discovery(self, series_id: UUID):
        series = await self.series_service.get_series(series_id)
        selected_narrative = await self._selected_narrative(series.id)
        if selected_narrative:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Discovery cannot be re-run after a narrative has been selected. "
                    "Regenerate narratives from the existing research ledger instead."
                ),
            )

        series.discovery_status = DiscoveryStatus.RUNNING
        await self.session.flush()

        query = self._query_for_series(series)
        result = await ResearchProviderRegistry(self.session).search_sources(
            query=query,
            filters={
                "series_id": str(series.id),
                "ledger_type": DiscoveryLedgerType.NARRATIVE_SUPPORT.value,
                "limit": 6,
            },
        )
        research_run_id = self._research_run_id(result.metadata)
        documents = (
            await self._documents_for_run(research_run_id, series)
            if research_run_id
            else []
        )

        if not documents:
            series.discovery_status = DiscoveryStatus.FAILED
            series.status = SeriesStatus.RESEARCHING
            await self.session.commit()
            return await self._workspace_response(series.id)

        await self._clear_unselected_discovery(series.id)
        await self._create_ledger_from_documents(series.id, documents)
        await self._create_narratives_from_ledger(series.id)
        series.discovery_status = DiscoveryStatus.COMPLETE
        series.current_stage = SeriesStage.DISCOVERY
        series.status = SeriesStatus.RESEARCHING
        await self.session.commit()
        return await self._workspace_response(series.id)

    async def regenerate_narratives(self, series_id: UUID):
        series = await self.series_service.get_series(series_id)
        ledger = await self._ledger(series.id)
        if not ledger:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Discovery research is required before narrative regeneration.",
            )

        await self.session.execute(
            update(Narrative)
            .where(
                Narrative.series_id == series_id,
                Narrative.is_selected.is_(False),
                Narrative.status == NarrativeStatus.CANDIDATE,
            )
            .values(status=NarrativeStatus.RETIRED)
        )
        await self._create_narratives_from_ledger(series.id)
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def select_narrative(self, series_id: UUID, narrative_id: UUID):
        series = await self.series_service.get_series(series_id)
        narrative = await self.session.get(Narrative, narrative_id)
        if narrative is None or narrative.series_id != series_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Narrative not found",
            )
        previous_selected = await self._selected_narrative(series.id)
        if series.plan_locked_at is not None and (
            previous_selected is None or previous_selected.id != narrative.id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Narrative selection cannot change after the episode plan is locked",
            )

        await self.session.execute(
            update(Narrative)
            .where(Narrative.series_id == series_id, Narrative.status != NarrativeStatus.RETIRED)
            .values(is_selected=False, status=NarrativeStatus.CANDIDATE, selected_at=None)
        )
        narrative.is_selected = True
        narrative.status = NarrativeStatus.SELECTED
        narrative.selected_at = func.now()
        series.current_stage = SeriesStage.PLAN
        series.status = SeriesStatus.PLANNING
        series.discovery_status = DiscoveryStatus.COMPLETE
        from app.modules.episodes.service import EpisodePlanService

        await EpisodePlanService(self.session).ensure_generated_plan(
            series,
            narrative,
            replace_existing=previous_selected is not None and previous_selected.id != narrative.id,
        )
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def _workspace_response(self, series_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        await self.session.refresh(series)
        ledger = await self._ledger(series_id)
        narratives = await self._visible_narratives(series_id)
        selected = next((narrative for narrative in narratives if narrative.is_selected), None)

        completed = sum(1 for entry in ledger if entry.status == DiscoverySourceStatus.COMPLETE)
        progress_percent = round((completed / len(ledger)) * 100) if ledger else 0

        return {
            "series": series,
            "progress_percent": progress_percent,
            "ledger": await self._ledger_payloads(series_id, ledger),
            "narratives": narratives,
            "selected_narrative_id": selected.id if selected else None,
            "research_activity": await self._research_activity(series_id),
        }

    async def _ledger(self, series_id: UUID) -> list[DiscoveryLedgerEntry]:
        result = await self.session.execute(
            select(DiscoveryLedgerEntry)
            .where(DiscoveryLedgerEntry.series_id == series_id)
            .order_by(DiscoveryLedgerEntry.sort_order.asc())
        )
        return list(result.scalars().all())

    async def _selected_narrative(self, series_id: UUID) -> Narrative | None:
        result = await self.session.execute(
            select(Narrative).where(
                Narrative.series_id == series_id,
                Narrative.status == NarrativeStatus.SELECTED,
                Narrative.is_selected.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def _visible_narratives(self, series_id: UUID) -> list[Narrative]:
        result = await self.session.execute(
            select(Narrative)
            .where(Narrative.series_id == series_id, Narrative.status != NarrativeStatus.RETIRED)
            .order_by(
                Narrative.generation.desc(),
                Narrative.created_at.asc(),
            )
        )
        return list(result.scalars().all())

    async def _documents_for_run(
        self,
        research_run_id: UUID,
        series: object,
    ) -> list[tuple[ResearchDocument, ResearchSource]]:
        result = await self.session.execute(
            select(ResearchDocument, ResearchSource)
            .join(ResearchSource, ResearchSource.id == ResearchDocument.source_id)
            .where(ResearchDocument.research_run_id == research_run_id)
            .order_by(ResearchDocument.composite_score.desc(), ResearchDocument.created_at.desc())
            .limit(40)
        )
        return self._rank_documents_for_series(series, list(result.all()))

    async def _clear_unselected_discovery(self, series_id: UUID) -> None:
        await self.session.execute(
            delete(DiscoveryLedgerEntry).where(DiscoveryLedgerEntry.series_id == series_id)
        )
        await self.session.execute(
            update(Narrative)
            .where(
                Narrative.series_id == series_id,
                Narrative.status == NarrativeStatus.CANDIDATE,
                Narrative.is_selected.is_(False),
            )
            .values(status=NarrativeStatus.RETIRED)
        )
        await self.session.flush()

    async def _create_ledger_from_documents(
        self,
        series_id: UUID,
        documents: list[tuple[ResearchDocument, ResearchSource]],
    ) -> None:
        existing = await self._ledger(series_id)
        if existing:
            return

        for index, (document, source) in enumerate(documents[:5], start=1):
            score = document.composite_score or document.engagement_score or 70
            self.session.add(
                DiscoveryLedgerEntry(
                    series_id=series_id,
                    source_name=source.name,
                    source_type=source.provider_type.value.replace("_", " "),
                    source_url=document.url or f"https://research.local/documents/{document.id}",
                    status=DiscoverySourceStatus.COMPLETE,
                    signal_title=document.title,
                    signal_summary=self._signal_summary(document),
                    confidence_score=max(0, min(int(score), 100)),
                    sort_order=index,
                )
            )
        await self.session.flush()

    async def _ledger_payloads(
        self,
        series_id: UUID,
        ledger: list[DiscoveryLedgerEntry],
    ) -> list[dict[str, object]]:
        if not ledger:
            return []

        documents = await self._documents_for_ledger(series_id, ledger)
        payloads: list[dict[str, object]] = []
        for entry in ledger:
            document = self._matched_document(entry, documents)
            payload = {
                "id": entry.id,
                "series_id": entry.series_id,
                "source_name": entry.source_name,
                "source_type": entry.source_type,
                "source_url": entry.source_url,
                "status": entry.status,
                "signal_title": entry.signal_title,
                "signal_summary": entry.signal_summary,
                "confidence_score": entry.confidence_score,
                "sort_order": entry.sort_order,
                "created_at": entry.created_at,
                "updated_at": entry.updated_at,
                "tier": None,
                "tier_score": None,
                "engagement_score": None,
                "freshness_score": None,
                "author_score": None,
                "composite_score": None,
                "confidence_level": None,
                "trend_score": None,
                "trend_available": None,
                "score_explanation_json": self._fallback_score_explanation(entry),
            }
            if document:
                payload.update(
                    {
                        "tier": document.tier,
                        "tier_score": document.tier_score,
                        "engagement_score": document.engagement_score,
                        "freshness_score": document.freshness_score,
                        "author_score": document.author_score,
                        "composite_score": document.composite_score,
                        "confidence_level": document.confidence_level,
                        "trend_score": document.trend_score,
                        "trend_available": document.trend_available,
                        "score_explanation_json": document.score_explanation_json or {},
                    }
                )
            payloads.append(payload)
        return payloads

    async def _documents_for_ledger(
        self,
        series_id: UUID,
        ledger: list[DiscoveryLedgerEntry],
    ) -> list[ResearchDocument]:
        urls = {
            entry.source_url
            for entry in ledger
            if entry.source_url and not entry.source_url.startswith("https://research.local")
        }
        titles = {entry.signal_title for entry in ledger if entry.signal_title}
        conditions = []
        if urls:
            conditions.append(ResearchDocument.url.in_(urls))
        if titles:
            conditions.append(ResearchDocument.title.in_(titles))
        if not conditions:
            return []

        result = await self.session.execute(
            select(ResearchDocument)
            .join(ResearchRun, ResearchRun.id == ResearchDocument.research_run_id)
            .where(ResearchRun.series_id == series_id, or_(*conditions))
            .order_by(ResearchDocument.created_at.desc())
            .limit(max(len(ledger) * 3, 10))
        )
        documents = list(result.scalars().all())
        if documents:
            return documents

        result = await self.session.execute(
            select(ResearchDocument)
            .where(or_(*conditions))
            .order_by(ResearchDocument.created_at.desc())
            .limit(max(len(ledger) * 3, 10))
        )
        return list(result.scalars().all())

    async def _create_narratives_from_ledger(self, series_id: UUID) -> None:
        series = await self.series_service.get_series(series_id)
        ledger = await self._ledger(series_id)
        if not ledger:
            return

        generation = await self._next_narrative_generation(series_id)
        signals = [
            {
                "source_name": entry.source_name,
                "signal_title": entry.signal_title,
                "confidence_score": entry.confidence_score,
            }
            for entry in ledger[:3]
        ]
        confidence = round(sum(entry.confidence_score for entry in ledger) / len(ledger))
        candidates = self._narrative_candidates(series, ledger, generation)
        for offset, (title, summary, thesis) in enumerate(candidates):
            self.session.add(
                Narrative(
                    series_id=series_id,
                    title=title,
                    thesis=thesis,
                    summary=summary,
                    confidence_score=max(0, min(confidence - offset * 4, 100)),
                    supporting_signals=signals,
                    generation=generation,
                    status=NarrativeStatus.CANDIDATE,
                    is_selected=False,
                )
            )
        await self.session.flush()

    async def _next_narrative_generation(self, series_id: UUID) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.max(Narrative.generation), 0)).where(
                Narrative.series_id == series_id
            )
        )
        return int(result.scalar_one() or 0) + 1

    async def _research_activity(self, series_id: UUID) -> dict[str, object]:
        service = ResearchPersistenceService(self.session)
        runs = await service.list_runs(series_id=series_id, page=1, page_size=5)
        latest = runs["items"][0] if runs["items"] else None
        source_activity = []
        ledger_counts = await self._ledger_counts_by_source(series_id)
        if latest:
            usage = await service.list_source_usage(
                research_run_id=latest["id"],
                page=1,
                page_size=50,
                sort="started_at",
            )
            source_activity = [
                {
                    **item,
                    "documents_used": ledger_counts.get(
                        self._source_activity_count_key(item),
                        0,
                    ),
                }
                for item in usage["items"]
            ]
        ledger_used_count = sum(item["documents_used"] for item in source_activity)
        return {
            "run_count": runs["total"],
            "latest_run": latest,
            "latest_run_status": latest["status"] if latest else None,
            "sources_queried": latest["successful_source_count"] if latest else 0,
            "sources_failed": latest["failed_source_count"] if latest else 0,
            "sources_skipped": latest["skipped_source_count"] if latest else 0,
            "documents_found": latest["total_documents_found"] if latest else 0,
            "documents_used": ledger_used_count,
            "source_activity": source_activity,
        }

    def _narrative_candidates(
        self,
        series: object,
        ledger: list[DiscoveryLedgerEntry],
        generation: int,
    ) -> list[tuple[str, str, str]]:
        title_seed = self._compact_text(getattr(series, "name", "") or "Series", 70)
        audience = self._compact_text(
            getattr(series, "audience", "") or "the intended audience",
            110,
        )
        audience_short = self._compact_text(audience, 48)
        focus = self._series_focus_phrase(series)
        focus_short = self._compact_text(focus, 56).rstrip(".")
        signal_clauses = [self._signal_clause(entry) for entry in ledger[:3]]
        signal_titles = [
            self._compact_text(getattr(entry, "signal_title", "") or "", 80).rstrip(".")
            for entry in ledger[:3]
            if getattr(entry, "signal_title", None)
        ]
        top_signal = signal_clauses[0] if signal_clauses else focus
        second_signal = signal_clauses[1] if len(signal_clauses) > 1 else top_signal
        evidence_pair = self._join_phrases(signal_clauses[:2]) or focus
        title_signal = signal_titles[0] if signal_titles else focus_short

        candidate_pool = [
            (
                self._narrative_title(title_seed, f"signals behind {focus_short}"),
                (
                    f"Build the story around {evidence_pair}. The arc keeps {focus} tied "
                    "to concrete source signals instead of a generic topic tour."
                ),
                (
                    f"{audience} should understand why {focus} matters now, where the "
                    "evidence is strongest, and what would change the decision."
                ),
            ),
            (
                self._narrative_title(title_seed, f"{audience_short} decision path"),
                (
                    f"A decision-led narrative that starts with {top_signal} and turns "
                    "the research into choices, tradeoffs, and next actions."
                ),
                (
                    f"The strongest conversation is not whether {focus} is interesting; "
                    f"it is how {audience} should evaluate it using the captured signals."
                ),
            ),
            (
                self._narrative_title(title_seed, f"risks in {title_signal}"),
                (
                    f"A sharper arc that stress-tests {focus} by comparing {evidence_pair} "
                    "and naming where confidence is still thin."
                ),
                (
                    f"{audience} need a balanced read on {focus}: what the evidence supports, "
                    "what remains uncertain, and what to watch next."
                ),
            ),
            (
                self._narrative_title(title_seed, f"operator playbook for {focus_short}"),
                (
                    f"Use {top_signal} as the opening signal, then translate {second_signal} "
                    "into practical operating moves."
                ),
                (
                    f"The series should help {audience} convert {focus} from abstract trend "
                    "into a sequence of operational decisions."
                ),
            ),
            (
                self._narrative_title(title_seed, f"who wins with {focus_short}"),
                (
                    f"A market-facing narrative that uses {evidence_pair} to identify who "
                    "benefits, who is exposed, and which assumptions deserve scrutiny."
                ),
                (
                    f"The useful angle for {audience} is how {focus} changes incentives, "
                    "adoption timing, and the shape of advantage."
                ),
            ),
            (
                self._narrative_title(title_seed, f"evidence tension in {focus_short}"),
                (
                    f"Frame the episode arc around the tension between {top_signal} and "
                    f"{second_signal}, then separate durable signal from noise."
                ),
                (
                    f"{audience} should leave with a testable view of {focus}, not just "
                    "a summary of familiar headlines."
                ),
            ),
        ]

        start = ((max(generation, 1) - 1) * 3) % len(candidate_pool)
        candidates = [
            candidate_pool[(start + offset) % len(candidate_pool)]
            for offset in range(min(3, len(candidate_pool)))
        ]
        return [
            (
                self._compact_text(title, 160),
                self._compact_text(summary, 360),
                self._compact_text(thesis, 320),
            )
            for title, summary, thesis in candidates
        ]

    async def _ledger_counts_by_source(self, series_id: UUID) -> dict[tuple[str, str], int]:
        ledger = await self._ledger(series_id)
        counts: dict[tuple[str, str], int] = {}
        for entry in ledger:
            key = (
                entry.source_name.strip().lower(),
                entry.source_type.replace("_", " ").strip().lower(),
            )
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _source_activity_count_key(self, item: dict[str, object]) -> tuple[str, str]:
        provider = item.get("provider_type")
        provider_value = getattr(provider, "value", provider)
        return (
            str(item.get("source_name") or "").strip().lower(),
            str(provider_value or "").replace("_", " ").strip().lower(),
        )

    def _query_for_series(self, series: object) -> str:
        parts = [
            getattr(series, "description", ""),
            getattr(series, "name", ""),
            getattr(series, "audience", ""),
            getattr(series, "guest_name", "") or "",
        ]
        query = " ".join(part.strip() for part in parts if part and part.strip())
        return self._compact_text(query, 500)

    def _research_run_id(self, metadata: dict[str, object]) -> UUID | None:
        value = metadata.get("research_run_id")
        try:
            return UUID(str(value)) if value else None
        except ValueError:
            return None

    def _signal_summary(self, document: ResearchDocument) -> str:
        summary = document.content_excerpt or document.normalized_content
        if summary:
            return summary[:500]
        return (
            "This source was captured during provider-backed discovery and should be "
            "reviewed before selecting the final narrative direction."
        )

    def _compact_title(self, title: str) -> str:
        return self._compact_text(title, 72)

    def _compact_text(self, text: object, max_length: int) -> str:
        clean = " ".join(str(text or "").split())
        if len(clean) <= max_length:
            return clean
        return f"{clean[: max_length - 3].rstrip()}..."

    def _series_focus_phrase(self, series: object) -> str:
        description = self._strip_series_prefix(getattr(series, "description", "") or "")
        if description:
            return self._compact_text(description, 120).rstrip(".")
        name = self._compact_text(getattr(series, "name", "") or "", 120).rstrip(".")
        return name or "the topic"

    def _strip_series_prefix(self, text: str) -> str:
        clean = " ".join(text.split()).strip()
        if not clean:
            return ""
        stripped = re.sub(
            (
                r"^(?:a|an|the)?\s*"
                r"(?:research-backed|focused|practical|executive|weekly)?\s*"
                r"(?:podcast|show|series|briefing|briefings|conversation|conversations)\s+"
                r"(?:about|on|for|exploring)\s+"
            ),
            "",
            clean,
            flags=re.IGNORECASE,
        ).strip()
        stripped = re.sub(r"^(?:about|on|for|exploring)\s+", "", stripped, flags=re.IGNORECASE)
        return stripped or clean

    def _signal_clause(self, entry: DiscoveryLedgerEntry) -> str:
        title = self._compact_text(getattr(entry, "signal_title", "") or "", 92).rstrip(".")
        summary = self._compact_text(getattr(entry, "signal_summary", "") or "", 118).rstrip(".")
        if title and summary and summary.casefold() not in title.casefold():
            return f"{title}: {summary}"
        return title or summary

    def _join_phrases(self, phrases: list[str]) -> str:
        clean = [phrase for phrase in phrases if phrase]
        if not clean:
            return ""
        if len(clean) == 1:
            return clean[0]
        return "; ".join(clean[:-1]) + f"; and {clean[-1]}"

    def _narrative_title(self, title_seed: str, fragment: str) -> str:
        clean_fragment = self._compact_text(fragment, 74).rstrip(".")
        if clean_fragment.casefold() in title_seed.casefold():
            return title_seed
        return self._compact_text(f"{title_seed}: {clean_fragment}", 160)

    def _rank_documents_for_series(
        self,
        series: object,
        rows: list[tuple[ResearchDocument, ResearchSource]],
    ) -> list[tuple[ResearchDocument, ResearchSource]]:
        weighted_terms = self._weighted_series_terms(series)
        ranked: list[tuple[int, int, ResearchDocument, ResearchSource]] = []
        seen: set[str] = set()
        for document, source in rows:
            dedupe_key = self._document_dedupe_key(document, source)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            relevance = self._document_relevance_score(document, weighted_terms)
            quality = int(document.composite_score or document.engagement_score or 0)
            ranked.append((relevance, quality, document, source))

        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        relevant = [item for item in ranked if item[0] >= 15]
        selected = relevant if len(relevant) >= 3 else [item for item in ranked if item[0] > 0]
        if not selected:
            selected = ranked[:5]
        balanced = self._source_balanced_selection(selected, limit=8)
        return [(document, source) for _, _, document, source in balanced]

    def _source_balanced_selection(
        self,
        ranked_items: list[tuple[int, int, ResearchDocument, ResearchSource]],
        *,
        limit: int,
    ) -> list[tuple[int, int, ResearchDocument, ResearchSource]]:
        chosen: list[tuple[int, int, ResearchDocument, ResearchSource]] = []
        remaining = ranked_items[:]
        source_counts: dict[str, int] = {}
        while remaining and len(chosen) < limit:
            best_index = 0
            best_key = self._source_balance_key(remaining[0][3])
            best_sort = (
                source_counts.get(best_key, 0),
                -remaining[0][0],
                -remaining[0][1],
                0,
            )
            for index, item in enumerate(remaining[1:], start=1):
                source_key = self._source_balance_key(item[3])
                sort_key = (
                    source_counts.get(source_key, 0),
                    -item[0],
                    -item[1],
                    index,
                )
                if sort_key < best_sort:
                    best_index = index
                    best_key = source_key
                    best_sort = sort_key
            chosen.append(remaining.pop(best_index))
            source_counts[best_key] = source_counts.get(best_key, 0) + 1
        return chosen

    def _source_balance_key(self, source: ResearchSource) -> str:
        for attribute in ("id", "key", "name", "provider_type"):
            value = getattr(source, attribute, None)
            if value:
                return str(value)
        return "unknown"

    def _weighted_series_terms(self, series: object) -> dict[str, int]:
        weights: dict[str, int] = {}
        weighted_fields = [
            (getattr(series, "description", "") or "", 5),
            (getattr(series, "name", "") or "", 3),
            (getattr(series, "audience", "") or "", 2),
            (getattr(series, "guest_name", "") or "", 1),
        ]
        for text, weight in weighted_fields:
            for token in self._tokens(text):
                weights[token] = max(weights.get(token, 0), weight)
        return weights

    def _document_relevance_score(
        self,
        document: ResearchDocument,
        weighted_terms: dict[str, int],
    ) -> int:
        if not weighted_terms:
            return 0
        title_terms = set(self._tokens(document.title))
        body_terms = set(
            self._tokens(
                " ".join(
                    [
                        document.content_excerpt or "",
                        document.normalized_content or "",
                        document.author or "",
                        document.url or "",
                    ]
                )
            )
        )
        matched = 0
        maximum = 0
        for term, weight in weighted_terms.items():
            maximum += weight * 8
            if self._term_matches(term, title_terms):
                matched += weight * 8
            elif self._term_matches(term, body_terms):
                matched += weight * 4
        if maximum <= 0:
            return 0
        return max(0, min(round((matched / maximum) * 100), 100))

    def _term_matches(self, term: str, haystack: Iterable[str]) -> bool:
        if term in haystack:
            return True
        if len(term) < 5:
            return False
        prefix = term[:5]
        return any(
            candidate.startswith(prefix) or prefix.startswith(candidate[:5])
            for candidate in haystack
        )

    def _tokens(self, text: str | None) -> list[str]:
        if not text:
            return []
        stopwords = {
            "about",
            "across",
            "after",
            "also",
            "and",
            "are",
            "audience",
            "before",
            "between",
            "but",
            "can",
            "for",
            "from",
            "has",
            "have",
            "how",
            "into",
            "its",
            "need",
            "not",
            "our",
            "podcast",
            "series",
            "show",
            "that",
            "the",
            "their",
            "this",
            "through",
            "to",
            "what",
            "when",
            "where",
            "who",
            "why",
            "with",
        }
        tokens: list[str] = []
        for raw in re.findall(r"[a-zA-Z0-9+#]+", text.lower()):
            token = self._stem_token(raw)
            if token and token not in stopwords:
                tokens.append(token)
        return tokens

    def _stem_token(self, token: str) -> str:
        if token in {"ai", "ml", "ux", "b2b", "b2c"}:
            return token
        if len(token) > 5 and token.endswith("ies"):
            return f"{token[:-3]}y"
        if len(token) > 6 and token.endswith("ing"):
            return token[:-3]
        if len(token) > 5 and token.endswith("es"):
            return token[:-2]
        if len(token) > 4 and token.endswith("s"):
            return token[:-1]
        return token

    def _document_dedupe_key(
        self,
        document: ResearchDocument,
        source: ResearchSource,
    ) -> str:
        if document.url:
            return f"url:{document.url.split('?')[0].rstrip('/')}"
        return f"title:{source.id}:{' '.join(self._tokens(document.title))}"

    def _matched_document(
        self,
        entry: DiscoveryLedgerEntry,
        documents: list[ResearchDocument],
    ) -> ResearchDocument | None:
        source_url = entry.source_url.split("?")[0].rstrip("/") if entry.source_url else ""
        title_key = " ".join(self._tokens(entry.signal_title))
        for document in documents:
            document_url = document.url.split("?")[0].rstrip("/") if document.url else ""
            if source_url and document_url and source_url == document_url:
                return document
            if title_key and title_key == " ".join(self._tokens(document.title)):
                return document
        return None

    def _fallback_score_explanation(
        self,
        entry: DiscoveryLedgerEntry,
    ) -> dict[str, object]:
        score = max(0, min(int(entry.confidence_score), 100))
        return {
            "formula": (
                "tier_score * 0.50 + engagement_score * 0.25 + "
                "freshness_score * 0.15 + author_score * 0.10"
            ),
            "composite_score": score,
            "confidence_level": "Medium" if score >= 65 else "Low" if score >= 40 else "Weak",
            "explanation": (
                f"Confidence {score}% is the ledger confidence captured for this source. "
                "Component scores were not available for this legacy entry."
            ),
        }
