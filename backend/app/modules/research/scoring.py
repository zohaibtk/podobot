from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.types import (
    DiscoveryLedgerType,
    ResearchConfidenceLevel,
    ResearchScoreEntityType,
    ResearchSourceProviderType,
)
from app.modules.research.models import (
    DiscoveryLedgerEntry,
    ResearchDocument,
    ResearchScoreBreakdown,
)
from app.modules.research_sources.models import ResearchSource

FORMULA_VERSION = "prd-r4-v1"
COMPOSITE_FORMULA = (
    "tier_score * 0.50 + engagement_score * 0.25 + "
    "freshness_score * 0.15 + author_score * 0.10"
)
TIER_SCORE_MAP = {"S": 100, "A": 85, "B": 70, "C": 50, "D": 25}
TRUSTED_DOMAINS = {
    "openai.com",
    "anthropic.com",
    "google.com",
    "microsoft.com",
    "youtube.com",
    "news.ycombinator.com",
    "ycombinator.com",
    "reddit.com",
    "arxiv.org",
    "nature.com",
    "mit.edu",
    "stanford.edu",
    "harvard.edu",
}


@dataclass(frozen=True)
class DocumentScore:
    tier: str
    tier_score: int
    engagement_score: int
    freshness_score: int
    author_score: int
    composite_score: int
    trend_score: int | None
    trend_available: bool
    trend_source: str | None
    trend_failure_reason: str | None
    confidence_level: ResearchConfidenceLevel
    explanation_json: dict[str, object]


class TierScoringService:
    provider_tiers = {
        ResearchSourceProviderType.GEMINI: "S",
        ResearchSourceProviderType.EXA: "A",
        ResearchSourceProviderType.YOUTUBE_DATA_API: "A",
        ResearchSourceProviderType.SERPAPI: "A",
        ResearchSourceProviderType.HN_ALGOLIA: "B",
        ResearchSourceProviderType.FIRECRAWL: "B",
        ResearchSourceProviderType.PYTRENDS: "B",
        ResearchSourceProviderType.REDDIT_JSON: "C",
        ResearchSourceProviderType.GROK_X: "C",
        ResearchSourceProviderType.GROQ: "C",
    }

    def classify(self, document: ResearchDocument, source: ResearchSource) -> str:
        domain = domain_for(document.url)
        if domain and trusted_domain(domain):
            if source.provider_type in {
                ResearchSourceProviderType.GEMINI,
                ResearchSourceProviderType.EXA,
                ResearchSourceProviderType.YOUTUBE_DATA_API,
            }:
                return "S"
            return "A"
        metadata = metadata_for(document)
        declared_tier = metadata.get("tier") or metadata.get("source_tier")
        if isinstance(declared_tier, str) and declared_tier.upper() in TIER_SCORE_MAP:
            return declared_tier.upper()
        return self.provider_tiers.get(source.provider_type, "D")

    def score(self, tier: str) -> int:
        return TIER_SCORE_MAP.get(tier.upper(), TIER_SCORE_MAP["D"])


class EngagementScoringService:
    def score(self, document: ResearchDocument) -> int:
        metadata = metadata_for(document)
        provider_type = document.provider_type
        if provider_type == ResearchSourceProviderType.REDDIT_JSON:
            raw = number(metadata.get("score")) + number(metadata.get("num_comments")) * 2
            return clamp_score(raw)
        if provider_type == ResearchSourceProviderType.HN_ALGOLIA:
            raw = number(metadata.get("points")) + number(metadata.get("num_comments")) * 1.5
            return clamp_score(raw)
        if provider_type == ResearchSourceProviderType.YOUTUBE_DATA_API:
            raw = (
                number(metadata.get("view_count")) / 1000
                + number(metadata.get("like_count")) / 100
                + number(metadata.get("comment_count")) * 2
            )
            return clamp_score(raw)
        if provider_type == ResearchSourceProviderType.EXA:
            return clamp_score(number(metadata.get("score")) * 100)
        if provider_type == ResearchSourceProviderType.FIRECRAWL:
            return clamp_score(50 + min(number(metadata.get("content_length")) / 200, 30))
        provider_scores = provider_scores_for(document)
        if "engagement" in provider_scores:
            value = number(provider_scores.get("engagement"))
            return clamp_score(value * 100 if value <= 1 else value)
        return 50


class FreshnessScoringService:
    def score(self, published_at: datetime | None) -> int:
        if published_at is None:
            return 45
        reference = published_at if published_at.tzinfo else published_at.replace(tzinfo=UTC)
        age_days = max((datetime.now(UTC) - reference).days, 0)
        if age_days <= 7:
            return 100
        if age_days <= 30:
            return 85
        if age_days <= 90:
            return 70
        if age_days <= 365:
            return 50
        return 30


class AuthorScoringService:
    provider_authority = {
        ResearchSourceProviderType.OPENAI: 88,
        ResearchSourceProviderType.GEMINI: 85,
        ResearchSourceProviderType.EXA: 72,
        ResearchSourceProviderType.YOUTUBE_DATA_API: 68,
        ResearchSourceProviderType.SERPAPI: 70,
        ResearchSourceProviderType.HN_ALGOLIA: 62,
        ResearchSourceProviderType.FIRECRAWL: 60,
        ResearchSourceProviderType.REDDIT_JSON: 55,
        ResearchSourceProviderType.PYTRENDS: 50,
        ResearchSourceProviderType.GROK_X: 50,
        ResearchSourceProviderType.GROQ: 50,
    }

    def score(self, document: ResearchDocument, source: ResearchSource) -> int:
        score = self.provider_authority.get(source.provider_type, 50)
        metadata = metadata_for(document)
        domain = domain_for(document.url)
        if document.author:
            score += 10
        if trusted_domain(domain):
            score += 10
        if metadata.get("verified") is True or metadata.get("is_verified") is True:
            score += 10
        if metadata.get("channel_id") and metadata.get("channel_title"):
            score += 5
        return clamp_score(score)


class ConfidenceLevelService:
    def level_for(self, composite_score: int) -> ResearchConfidenceLevel:
        if composite_score >= 85:
            return ResearchConfidenceLevel.HIGH
        if composite_score >= 65:
            return ResearchConfidenceLevel.MEDIUM
        if composite_score >= 40:
            return ResearchConfidenceLevel.LOW
        return ResearchConfidenceLevel.WEAK


class ScoreExplanationService:
    def document_explanation(
        self,
        *,
        document: ResearchDocument,
        tier: str,
        tier_score: int,
        engagement_score: int,
        freshness_score: int,
        author_score: int,
        composite_score: int,
        confidence_level: ResearchConfidenceLevel,
        trend_score: int | None,
        trend_available: bool,
        trend_source: str | None,
        trend_failure_reason: str | None,
    ) -> dict[str, object]:
        text = (
            f"Composite score {composite_score} = Tier {tier_score} x 50% + "
            f"Engagement {engagement_score} x 25% + Freshness {freshness_score} x 15% "
            f"+ Author {author_score} x 10%."
        )
        metadata = metadata_for(document)
        return {
            "formula": COMPOSITE_FORMULA,
            "formula_version": FORMULA_VERSION,
            "tier": tier,
            "tier_score": tier_score,
            "engagement_score": engagement_score,
            "freshness_score": freshness_score,
            "author_score": author_score,
            "composite_score": composite_score,
            "confidence_level": confidence_level.value,
            "trend_score": trend_score,
            "trend_available": trend_available,
            "trend_source": trend_source,
            "trend_failure_reason": trend_failure_reason,
            "explanation": text,
            "metadata_used": {
                "provider_type": document.provider_type.value,
                "domain": domain_for(document.url),
                "author_present": bool(document.author),
                "published_at": document.published_at.isoformat()
                if document.published_at
                else None,
                "metadata_keys": sorted(metadata.keys()),
            },
        }

    def weak_entity_explanation(self) -> dict[str, object]:
        return {
            "formula": COMPOSITE_FORMULA,
            "formula_version": FORMULA_VERSION,
            "composite_score": 0,
            "confidence_level": ResearchConfidenceLevel.WEAK.value,
            "explanation": "No supporting evidence available",
            "warning": (
                "Evidence is weak. Review source quality before relying on this recommendation."
            ),
        }


class TrendScoringService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def score(
        self,
        document: ResearchDocument,
        *,
        use_provider_fallback: bool,
    ) -> dict[str, object]:
        metadata = metadata_for(document)
        existing_score = metadata.get("trend_score")
        if existing_score is not None:
            return {
                "trend_score": clamp_score(number(existing_score)),
                "trend_available": True,
                "trend_source": str(metadata.get("source_used") or document.provider_type.value),
                "trend_failure_reason": None,
            }
        if not use_provider_fallback:
            return {
                "trend_score": None,
                "trend_available": False,
                "trend_source": None,
                "trend_failure_reason": "Trend not available. This does not block generation.",
            }
        try:
            from app.research.providers.registry import ResearchProviderRegistry

            result = await ResearchProviderRegistry(self.session).get_trend_score(
                query=document.title,
                filters={"document_id": str(document.id), "classification": "score_trend"},
            )
            output = result.output
            if output.get("trend_available") is True:
                return {
                    "trend_score": clamp_score(
                        number(output.get("score") or output.get("trend_score"))
                    ),
                    "trend_available": True,
                    "trend_source": optional_str(output.get("source_used")),
                    "trend_failure_reason": None,
                }
            return {
                "trend_score": None,
                "trend_available": False,
                "trend_source": None,
                "trend_failure_reason": "Trend not available. This does not block generation.",
            }
        except Exception:
            return {
                "trend_score": None,
                "trend_available": False,
                "trend_source": None,
                "trend_failure_reason": "Trend not available. This does not block generation.",
            }


class ResearchScoringService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.tier = TierScoringService()
        self.engagement = EngagementScoringService()
        self.freshness = FreshnessScoringService()
        self.author = AuthorScoringService()
        self.confidence = ConfidenceLevelService()
        self.explanations = ScoreExplanationService()
        self.trends = TrendScoringService(session)

    async def get_document_score(self, document_id: UUID) -> dict[str, object]:
        document, source = await self._document_with_source(document_id)
        return self._document_score_payload(document, source)

    async def score_document(
        self,
        document_id: UUID,
        *,
        include_trend: bool = True,
        commit: bool = True,
    ) -> dict[str, object]:
        document, source = await self._document_with_source(document_id)
        await self.score_existing_document(
            document,
            source,
            include_trend=include_trend,
        )
        if commit:
            await self.session.commit()
        return self._document_score_payload(document, source)

    async def score_existing_document(
        self,
        document: ResearchDocument,
        source: ResearchSource,
        *,
        include_trend: bool = False,
        flush: bool = True,
    ) -> DocumentScore:
        score = await self.calculate_document_score(
            document,
            source,
            include_trend=include_trend,
        )
        document.tier = score.tier
        document.tier_score = score.tier_score
        document.engagement_score = score.engagement_score
        document.freshness_score = score.freshness_score
        document.author_score = score.author_score
        document.composite_score = score.composite_score
        document.trend_score = score.trend_score
        document.trend_available = score.trend_available
        document.trend_source = score.trend_source
        document.trend_failure_reason = score.trend_failure_reason
        document.confidence_level = score.confidence_level
        document.score_explanation_json = score.explanation_json
        if flush:
            await self.session.flush()
        return score

    async def calculate_document_score(
        self,
        document: ResearchDocument,
        source: ResearchSource,
        *,
        include_trend: bool,
    ) -> DocumentScore:
        tier = self.tier.classify(document, source)
        tier_score = self.tier.score(tier)
        engagement_score = self.engagement.score(document)
        freshness_score = self.freshness.score(document.published_at)
        author_score = self.author.score(document, source)
        composite_score = composite_score_for(
            tier_score=tier_score,
            engagement_score=engagement_score,
            freshness_score=freshness_score,
            author_score=author_score,
        )
        confidence_level = self.confidence.level_for(composite_score)
        trend = await self.trends.score(document, use_provider_fallback=include_trend)
        explanation = self.explanations.document_explanation(
            document=document,
            tier=tier,
            tier_score=tier_score,
            engagement_score=engagement_score,
            freshness_score=freshness_score,
            author_score=author_score,
            composite_score=composite_score,
            confidence_level=confidence_level,
            trend_score=trend["trend_score"] if isinstance(trend["trend_score"], int) else None,
            trend_available=bool(trend["trend_available"]),
            trend_source=optional_str(trend["trend_source"]),
            trend_failure_reason=optional_str(trend["trend_failure_reason"]),
        )
        return DocumentScore(
            tier=tier,
            tier_score=tier_score,
            engagement_score=engagement_score,
            freshness_score=freshness_score,
            author_score=author_score,
            composite_score=composite_score,
            trend_score=trend["trend_score"] if isinstance(trend["trend_score"], int) else None,
            trend_available=bool(trend["trend_available"]),
            trend_source=optional_str(trend["trend_source"]),
            trend_failure_reason=optional_str(trend["trend_failure_reason"]),
            confidence_level=confidence_level,
            explanation_json=explanation,
        )

    async def score_run_documents(self, run_id: UUID) -> dict[str, object]:
        rows = await self.session.execute(
            select(ResearchDocument, ResearchSource)
            .join(ResearchSource, ResearchSource.id == ResearchDocument.source_id)
            .where(ResearchDocument.research_run_id == run_id)
        )
        scored = 0
        for document, source in rows.all():
            await self.score_existing_document(
                document,
                source,
                include_trend=True,
                flush=False,
            )
            scored += 1
        if scored:
            await self.session.flush()
        await self.session.commit()
        return {
            "success": True,
            "message": f"Scored {scored} research document(s).",
            "score_summary": await self.run_score_summary(run_id),
        }

    async def explain_score(self, payload: Mapping[str, object]) -> dict[str, object]:
        tier_score = clamp_score(number(payload.get("tier_score")))
        engagement_score = clamp_score(number(payload.get("engagement_score")))
        freshness_score = clamp_score(number(payload.get("freshness_score")))
        author_score = clamp_score(number(payload.get("author_score")))
        composite_score = composite_score_for(
            tier_score=tier_score,
            engagement_score=engagement_score,
            freshness_score=freshness_score,
            author_score=author_score,
        )
        confidence_level = self.confidence.level_for(composite_score)
        explanation = {
            "formula": COMPOSITE_FORMULA,
            "formula_version": FORMULA_VERSION,
            "tier_score": tier_score,
            "engagement_score": engagement_score,
            "freshness_score": freshness_score,
            "author_score": author_score,
            "composite_score": composite_score,
            "confidence_level": confidence_level.value,
            "explanation": (
                f"Composite score {composite_score} = Tier {tier_score} x 50% + "
                f"Engagement {engagement_score} x 25% + Freshness {freshness_score} x 15% "
                f"+ Author {author_score} x 10%."
            ),
        }
        return explanation

    async def run_score_summary(self, run_id: UUID) -> dict[str, object]:
        rows = await self.session.execute(
            select(ResearchDocument).where(ResearchDocument.research_run_id == run_id)
        )
        documents = list(rows.scalars().all())
        return self._summary_for_documents(documents)

    async def entity_score_breakdown(
        self,
        entity_type: ResearchScoreEntityType,
        entity_id: UUID,
    ) -> dict[str, object]:
        documents = await self._entity_documents(entity_type, entity_id)
        summary = self._summary_for_documents(documents)
        if not documents:
            explanation_json = self.explanations.weak_entity_explanation()
        else:
            explanation_json = {
                "formula": COMPOSITE_FORMULA,
                "formula_version": FORMULA_VERSION,
                "document_count": len(documents),
                "explanation": (
                    f"Entity score {summary['composite_score']} is averaged from "
                    f"{len(documents)} linked research document(s)."
                ),
                "confidence_distribution": summary["confidence_distribution"],
                "tier_distribution": summary["tier_distribution"],
            }
        breakdown = ResearchScoreBreakdown(
            entity_type=entity_type,
            entity_id=entity_id,
            research_run_id=documents[0].research_run_id if documents else None,
            tier_score_avg=summary["tier_score_avg"],
            engagement_score_avg=summary["engagement_score_avg"],
            freshness_score_avg=summary["freshness_score_avg"],
            author_score_avg=summary["author_score_avg"],
            composite_score=summary["composite_score"],
            trend_score=summary["trend_score"],
            trend_available=summary["trend_available"],
            confidence_level=ResearchConfidenceLevel(summary["confidence_level"]),
            formula_version=FORMULA_VERSION,
            explanation_json=explanation_json,
        )
        self.session.add(breakdown)
        await self.session.commit()
        return {
            "id": breakdown.id,
            "entity_type": breakdown.entity_type,
            "entity_id": breakdown.entity_id,
            "research_run_id": breakdown.research_run_id,
            "tier_score_avg": breakdown.tier_score_avg,
            "engagement_score_avg": breakdown.engagement_score_avg,
            "freshness_score_avg": breakdown.freshness_score_avg,
            "author_score_avg": breakdown.author_score_avg,
            "composite_score": breakdown.composite_score,
            "trend_score": breakdown.trend_score,
            "trend_available": breakdown.trend_available,
            "confidence_level": breakdown.confidence_level,
            "formula_version": breakdown.formula_version,
            "explanation_json": breakdown.explanation_json,
            "created_at": breakdown.created_at,
        }

    async def _document_with_source(
        self,
        document_id: UUID,
    ) -> tuple[ResearchDocument, ResearchSource]:
        row = await self.session.execute(
            select(ResearchDocument, ResearchSource)
            .join(ResearchSource, ResearchSource.id == ResearchDocument.source_id)
            .where(ResearchDocument.id == document_id)
        )
        result = row.one_or_none()
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Research document not found",
            )
        return result

    async def _entity_documents(
        self,
        entity_type: ResearchScoreEntityType,
        entity_id: UUID,
    ) -> list[ResearchDocument]:
        if entity_type == ResearchScoreEntityType.RESEARCH_DOCUMENT:
            document = await self.session.get(ResearchDocument, entity_id)
            return [document] if document else []
        statement = (
            select(ResearchDocument)
            .join(DiscoveryLedgerEntry, DiscoveryLedgerEntry.document_id == ResearchDocument.id)
            .distinct()
        )
        if entity_type == ResearchScoreEntityType.STRATEGY_IDEA:
            statement = statement.where(DiscoveryLedgerEntry.strategy_idea_id == entity_id)
        elif entity_type == ResearchScoreEntityType.EPISODE_TOPIC:
            statement = statement.where(DiscoveryLedgerEntry.episode_id == entity_id)
        elif entity_type == ResearchScoreEntityType.NARRATIVE:
            from app.modules.narratives.models import Narrative

            narrative = await self.session.get(Narrative, entity_id)
            if narrative is None:
                return []
            statement = statement.where(
                DiscoveryLedgerEntry.series_id == narrative.series_id,
                DiscoveryLedgerEntry.ledger_type.in_(
                    [
                        DiscoveryLedgerType.NARRATIVE_SUPPORT,
                        DiscoveryLedgerType.NARRATIVE_COUNTER,
                        DiscoveryLedgerType.SOURCE,
                    ]
                ),
            )
        elif entity_type == ResearchScoreEntityType.OUTLINE:
            from app.modules.outlines.models import EpisodeOutline

            outline = await self.session.get(EpisodeOutline, entity_id)
            if outline is None:
                return []
            statement = statement.where(
                DiscoveryLedgerEntry.series_id == outline.series_id,
                DiscoveryLedgerEntry.episode_id == outline.episode_id,
            )
        elif entity_type == ResearchScoreEntityType.BRIEF:
            from app.modules.briefs.models import EpisodeBrief

            brief = await self.session.get(EpisodeBrief, entity_id)
            if brief is None:
                return []
            statement = statement.where(
                DiscoveryLedgerEntry.series_id == brief.series_id,
                DiscoveryLedgerEntry.episode_id == brief.episode_id,
            )
        else:
            return []
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    def _summary_for_documents(self, documents: list[ResearchDocument]) -> dict[str, object]:
        if not documents:
            return {
                "document_count": 0,
                "tier_score_avg": 0,
                "engagement_score_avg": 0,
                "freshness_score_avg": 0,
                "author_score_avg": 0,
                "composite_score": 0,
                "trend_score": None,
                "trend_available": False,
                "confidence_level": ResearchConfidenceLevel.WEAK.value,
                "confidence_distribution": {
                    ResearchConfidenceLevel.HIGH.value: 0,
                    ResearchConfidenceLevel.MEDIUM.value: 0,
                    ResearchConfidenceLevel.LOW.value: 0,
                    ResearchConfidenceLevel.WEAK.value: 0,
                },
                "tier_distribution": {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0},
                "explanation": "No supporting evidence available",
            }
        confidence_distribution = {
            ResearchConfidenceLevel.HIGH.value: 0,
            ResearchConfidenceLevel.MEDIUM.value: 0,
            ResearchConfidenceLevel.LOW.value: 0,
            ResearchConfidenceLevel.WEAK.value: 0,
        }
        tier_distribution = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
        for document in documents:
            confidence_distribution[document.confidence_level.value] += 1
            tier_distribution[document.tier] = tier_distribution.get(document.tier, 0) + 1
        trend_scores = [
            document.trend_score
            for document in documents
            if document.trend_available and document.trend_score is not None
        ]
        composite = avg_int([document.composite_score for document in documents])
        return {
            "document_count": len(documents),
            "tier_score_avg": avg_int([document.tier_score for document in documents]),
            "engagement_score_avg": avg_int(
                [document.engagement_score for document in documents]
            ),
            "freshness_score_avg": avg_int([document.freshness_score for document in documents]),
            "author_score_avg": avg_int([document.author_score for document in documents]),
            "composite_score": composite,
            "trend_score": avg_int(trend_scores) if trend_scores else None,
            "trend_available": bool(trend_scores),
            "confidence_level": self.confidence.level_for(composite).value,
            "confidence_distribution": confidence_distribution,
            "tier_distribution": tier_distribution,
            "explanation": (
                f"Average composite score {composite} from {len(documents)} "
                "linked research document(s)."
            ),
        }

    def _document_score_payload(
        self,
        document: ResearchDocument,
        source: ResearchSource,
    ) -> dict[str, object]:
        return {
            "document_id": document.id,
            "research_run_id": document.research_run_id,
            "source_id": document.source_id,
            "source_key": source.key,
            "source_name": source.name,
            "provider_type": document.provider_type,
            "title": document.title,
            "tier": document.tier,
            "tier_score": document.tier_score,
            "engagement_score": document.engagement_score,
            "freshness_score": document.freshness_score,
            "author_score": document.author_score,
            "composite_score": document.composite_score,
            "trend_score": document.trend_score,
            "trend_available": document.trend_available,
            "trend_source": document.trend_source,
            "trend_failure_reason": document.trend_failure_reason,
            "confidence_level": document.confidence_level,
            "score_explanation_json": document.score_explanation_json or {},
        }


def composite_score_for(
    *,
    tier_score: int,
    engagement_score: int,
    freshness_score: int,
    author_score: int,
) -> int:
    weighted = (
        clamp_score(tier_score) * 0.50
        + clamp_score(engagement_score) * 0.25
        + clamp_score(freshness_score) * 0.15
        + clamp_score(author_score) * 0.10
    )
    return clamp_score(weighted + 0.000001)


def clamp_score(value: object) -> int:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0
    return max(0, min(100, int(numeric + 0.5)))


def avg_int(values: list[int | None]) -> int:
    numeric = [int(value) for value in values if value is not None]
    if not numeric:
        return 0
    return clamp_score(sum(numeric) / len(numeric))


def number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def optional_str(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def metadata_for(document: ResearchDocument) -> dict[str, object]:
    raw = document.raw_metadata_json or {}
    metadata = raw.get("metadata") if isinstance(raw, dict) else {}
    return metadata if isinstance(metadata, dict) else {}


def provider_scores_for(document: ResearchDocument) -> dict[str, object]:
    raw = document.raw_metadata_json or {}
    scores = raw.get("scores") if isinstance(raw, dict) else {}
    return scores if isinstance(scores, dict) else {}


def domain_for(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    return host or None


def trusted_domain(domain: str | None) -> bool:
    if not domain:
        return False
    return any(domain == trusted or domain.endswith(f".{trusted}") for trusted in TRUSTED_DOMAINS)
