from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.workflow import record_workflow_agent_run
from app.db.types import (
    AgentRunStatus,
    DiscoveryStatus,
    EpisodeStatus,
    NarrativeStatus,
    SeriesStage,
    SeriesStatus,
    StrategyIdeaStatus,
)
from app.modules.episodes.models import Episode
from app.modules.narratives.models import Narrative
from app.modules.series.models import Series
from app.modules.strategy.models import StrategyIdea, StrategyRun
from app.modules.strategy.opportunity import StrategyOpportunityEngine
from app.schemas.pagination import cursor_meta, decode_cursor, encode_cursor


class StrategyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_workspace(self) -> dict[str, object]:
        return await self._workspace_response()

    async def get_summary(self, *, range_value: str = "30d") -> dict[str, object]:
        start_at = self._range_start(range_value)
        run_count_statement = select(func.count(StrategyRun.id))
        idea_statement = select(StrategyIdea.status, func.count(StrategyIdea.id)).group_by(
            StrategyIdea.status
        )
        if start_at is not None:
            run_count_statement = run_count_statement.where(StrategyRun.created_at >= start_at)
            idea_statement = idea_statement.where(StrategyIdea.created_at >= start_at)
        run_count = int((await self.session.execute(run_count_statement)).scalar_one() or 0)
        rows = await self.session.execute(idea_statement)
        status_counts = Counter({status_value: 0 for status_value in StrategyIdeaStatus})
        for idea_status, count in rows.all():
            status_counts[idea_status] = int(count or 0)
        avg_statement = select(func.avg(StrategyIdea.opportunity_score))
        high_confidence_statement = select(func.count(StrategyIdea.id)).where(
            StrategyIdea.opportunity_score >= 80
        )
        hot_trends_statement = select(func.count(StrategyIdea.id)).where(
            StrategyIdea.lifecycle_stage == "hot"
        )
        if start_at is not None:
            avg_statement = avg_statement.where(StrategyIdea.created_at >= start_at)
            high_confidence_statement = high_confidence_statement.where(
                StrategyIdea.created_at >= start_at
            )
            hot_trends_statement = hot_trends_statement.where(
                StrategyIdea.created_at >= start_at
            )
        avg_score = (await self.session.execute(avg_statement)).scalar_one()
        high_confidence_count = int(
            (await self.session.execute(high_confidence_statement)).scalar_one() or 0
        )
        hot_trends_count = int(
            (await self.session.execute(hot_trends_statement)).scalar_one() or 0
        )
        now = datetime.now(UTC)
        month_start = datetime(now.year, now.month, 1, tzinfo=UTC)
        converted_this_month_count = int(
            (
                await self.session.execute(
                    select(func.count(StrategyIdea.id))
                    .where(StrategyIdea.status == StrategyIdeaStatus.CONVERTED)
                    .where(StrategyIdea.converted_at >= month_start)
                )
            ).scalar_one()
            or 0
        )
        return {
            "run_count": run_count,
            "proposed_count": status_counts[StrategyIdeaStatus.PROPOSED],
            "in_review_count": status_counts[StrategyIdeaStatus.IN_REVIEW],
            "dismissed_count": status_counts[StrategyIdeaStatus.DISMISSED],
            "converted_count": status_counts[StrategyIdeaStatus.CONVERTED],
            "new_opportunities_count": (
                status_counts[StrategyIdeaStatus.PROPOSED]
                + status_counts[StrategyIdeaStatus.IN_REVIEW]
            ),
            "high_confidence_count": high_confidence_count,
            "hot_trends_count": hot_trends_count,
            "converted_this_month_count": converted_this_month_count,
            "average_opportunity_score": round(float(avg_score or 0)),
        }

    async def list_runs_page(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, object]:
        statement = select(StrategyRun)
        if cursor:
            token = decode_cursor(cursor)
            statement = statement.where(
                or_(
                    StrategyRun.created_at < token.created_at,
                    and_(StrategyRun.created_at == token.created_at, StrategyRun.id < token.id),
                )
            )
        result = await self.session.execute(
            statement.order_by(
                StrategyRun.created_at.desc(),
                StrategyRun.id.desc(),
            ).limit(limit + 1)
        )
        runs = list(result.scalars().all())
        has_next = len(runs) > limit
        items = runs[:limit]
        next_cursor = (
            encode_cursor(items[-1].created_at, items[-1].id) if has_next and items else None
        )
        run_ids = [run.id for run in items]
        idea_counts: dict[UUID, int] = {}
        if run_ids:
            counts = await self.session.execute(
                select(StrategyIdea.run_id, func.count(StrategyIdea.id))
                .where(StrategyIdea.run_id.in_(run_ids))
                .group_by(StrategyIdea.run_id)
            )
            idea_counts = {row[0]: int(row[1]) for row in counts.all()}
        return {
            "items": [self._run_payload(run, idea_counts.get(run.id, 0)) for run in items],
            **cursor_meta(page_size=limit, has_next=has_next, next_cursor=next_cursor),
        }

    async def list_ideas_page(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status_filter: StrategyIdeaStatus | None = None,
        run_id: UUID | None = None,
        query: str | None = None,
    ) -> dict[str, object]:
        statement = select(StrategyIdea, StrategyRun).join(
            StrategyRun,
            StrategyRun.id == StrategyIdea.run_id,
        )
        if status_filter is not None:
            statement = statement.where(StrategyIdea.status == status_filter)
        if run_id is not None:
            statement = statement.where(StrategyIdea.run_id == run_id)
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(
                    StrategyIdea.title.ilike(pattern),
                    StrategyIdea.audience.ilike(pattern),
                    StrategyIdea.description.ilike(pattern),
                    StrategyIdea.thesis.ilike(pattern),
                    StrategyIdea.rationale.ilike(pattern),
                )
            )
        if cursor:
            token = decode_cursor(cursor)
            statement = statement.where(
                or_(
                    StrategyIdea.created_at < token.created_at,
                    and_(
                        StrategyIdea.created_at == token.created_at,
                        StrategyIdea.id < token.id,
                    ),
                )
            )
        result = await self.session.execute(
            statement.order_by(
                StrategyRun.run_date.desc(),
                StrategyIdea.opportunity_score.desc(),
                StrategyIdea.created_at.desc(),
                StrategyIdea.id.desc(),
            ).limit(limit + 1)
        )
        rows = result.all()
        has_next = len(rows) > limit
        items = rows[:limit]
        next_cursor = (
            encode_cursor(items[-1][0].created_at, items[-1][0].id)
            if has_next and items
            else None
        )
        return {
            "items": [self._idea_payload(idea, run) for idea, run in items],
            **cursor_meta(page_size=limit, has_next=has_next, next_cursor=next_cursor),
        }

    async def create_research_run(self) -> dict[str, object]:
        now = datetime.now(UTC)
        run_date = date.today()
        run = StrategyRun(
            run_date=run_date,
            topic="Content opportunity intelligence scan",
            status=AgentRunStatus.RUNNING,
            started_at=now,
        )
        self.session.add(run)
        await self.session.flush()
        try:
            opportunities, generation_metadata = await StrategyOpportunityEngine(
                self.session
            ).generate(run)
        except Exception as exc:
            run.status = AgentRunStatus.FAILED
            run.completed_at = datetime.now(UTC)
            await record_workflow_agent_run(
                self.session,
                agent_key="research",
                entity_type="strategy_run",
                entity_id=run.id,
                workflow_stage="strategy",
                trigger="generation",
                input_payload={"topic": run.topic, "run_date": run.run_date.isoformat()},
                output_payload={
                    "summary": "Strategy opportunity scan failed.",
                    "failure_reason": str(exc)[:240],
                    "needs_approval": False,
                    "idea_count": 0,
                },
            )
            await self.session.commit()
            return await self._workspace_response()

        for opportunity in opportunities:
            self.session.add(
                StrategyIdea(
                    run_id=run.id,
                    title=opportunity.title,
                    audience=opportunity.audience,
                    description=opportunity.description,
                    proposed_guest_name=opportunity.proposed_guest_name,
                    thesis=opportunity.thesis,
                    rationale=opportunity.rationale,
                    evidence_signals=opportunity.evidence_signals,
                    source_proposal=opportunity.source_proposal,
                    confidence_score=opportunity.confidence_score,
                    opportunity_score=opportunity.opportunity_score,
                    opportunity_score_breakdown=opportunity.opportunity_score_breakdown,
                    opportunity_score_explanation=opportunity.opportunity_score_explanation,
                    audience_intelligence=opportunity.audience_intelligence,
                    lifecycle_stage=opportunity.lifecycle_stage,
                    season_potential=opportunity.season_potential,
                    trend_intelligence=opportunity.trend_intelligence,
                    source_count=opportunity.source_count,
                    potential_episode_count=opportunity.potential_episode_count,
                    theme_count=opportunity.theme_count,
                    generated_at=opportunity.generated_at,
                )
            )
        run.status = AgentRunStatus.SUCCEEDED
        run.completed_at = datetime.now(UTC)
        await record_workflow_agent_run(
            self.session,
            agent_key="research",
            entity_type="strategy_run",
            entity_id=run.id,
            workflow_stage="strategy",
            trigger="generation",
            input_payload={"topic": run.topic, "run_date": run.run_date.isoformat()},
            output_payload={
                "summary": "Content opportunity intelligence scan completed.",
                "needs_approval": True,
                "idea_count": len(opportunities),
                "generation_metadata": generation_metadata,
            },
        )
        await self.session.commit()
        return await self._workspace_response()

    async def review_idea(self, idea_id: UUID) -> dict[str, object]:
        idea = await self._get_idea(idea_id)
        if idea.status == StrategyIdeaStatus.CONVERTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Converted ideas cannot be moved back into review",
            )
        if idea.status == StrategyIdeaStatus.DISMISSED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Restore dismissed ideas before review",
            )
        idea.status = StrategyIdeaStatus.IN_REVIEW
        idea.reviewed_at = idea.reviewed_at or datetime.now(UTC)
        await self.session.commit()
        return await self._action_response(idea.id)

    async def dismiss_idea(self, idea_id: UUID) -> dict[str, object]:
        idea = await self._get_idea(idea_id)
        if idea.status == StrategyIdeaStatus.CONVERTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Converted ideas cannot be dismissed",
            )
        idea.status = StrategyIdeaStatus.DISMISSED
        idea.dismissed_at = datetime.now(UTC)
        await self.session.commit()
        return await self._action_response(idea.id)

    async def restore_idea(self, idea_id: UUID) -> dict[str, object]:
        idea = await self._get_idea(idea_id)
        if idea.status == StrategyIdeaStatus.CONVERTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Converted ideas cannot be restored",
            )
        if idea.status != StrategyIdeaStatus.DISMISSED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only dismissed ideas can be restored",
            )
        idea.status = StrategyIdeaStatus.IN_REVIEW
        idea.dismissed_at = None
        idea.reviewed_at = idea.reviewed_at or datetime.now(UTC)
        await self.session.commit()
        return await self._action_response(idea.id)

    async def convert_idea(self, idea_id: UUID) -> dict[str, object]:
        idea = await self._get_idea(idea_id)
        if idea.status == StrategyIdeaStatus.CONVERTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Converted ideas cannot be converted again",
            )
        if idea.status == StrategyIdeaStatus.DISMISSED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Restore dismissed ideas before conversion",
            )

        now = datetime.now(UTC)
        series = Series(
            name=idea.title,
            audience=idea.audience,
            description=idea.description,
            guest_name=idea.proposed_guest_name,
            status=SeriesStatus.PLANNING,
            discovery_status=DiscoveryStatus.COMPLETE,
            current_stage=SeriesStage.PLAN,
            episode_plan_generated_at=now,
        )
        self.session.add(series)
        await self.session.flush()

        self.session.add(
            Narrative(
                series_id=series.id,
                title=idea.title,
                thesis=idea.thesis,
                summary=idea.rationale,
                confidence_score=idea.confidence_score,
                supporting_signals=idea.evidence_signals,
                generation=1,
                status=NarrativeStatus.SELECTED,
                is_selected=True,
                selected_at=now,
            )
        )
        for index, episode in enumerate(self._episode_plan(idea), start=1):
            self.session.add(
                Episode(
                    series_id=series.id,
                    episode_number=index,
                    title=episode["title"],
                    premise=episode["premise"],
                    status=EpisodeStatus.PLANNED,
                )
            )

        idea.status = StrategyIdeaStatus.CONVERTED
        idea.reviewed_at = idea.reviewed_at or now
        idea.converted_at = now
        idea.converted_series_id = series.id
        await self.session.commit()
        return await self._action_response(idea.id, converted_series=series)

    async def _workspace_response(self) -> dict[str, object]:
        runs = await self._runs()
        ideas = await self._ideas()
        ideas_by_run_id: dict[UUID, list[StrategyIdea]] = defaultdict(list)
        for idea in ideas:
            ideas_by_run_id[idea.run_id].append(idea)

        run_payloads = []
        groups = []
        status_counts = Counter({status_value: 0 for status_value in StrategyIdeaStatus})
        run_by_id = {run.id: run for run in runs}
        for idea in ideas:
            status_counts[idea.status] += 1

        for run in runs:
            run_payloads.append(self._run_payload(run, len(ideas_by_run_id[run.id])))

        grouped_ideas: dict[tuple[UUID, StrategyIdeaStatus], list[StrategyIdea]] = defaultdict(list)
        for idea in ideas:
            grouped_ideas[(idea.run_id, idea.status)].append(idea)

        for run in runs:
            for idea_status in StrategyIdeaStatus:
                items = grouped_ideas.get((run.id, idea_status), [])
                if not items:
                    continue
                groups.append(
                    {
                        "run_id": run.id,
                        "run_date": run.run_date,
                        "run_topic": run.topic,
                        "status": idea_status,
                        "ideas": [
                            self._idea_payload(idea, run_by_id[idea.run_id]) for idea in items
                        ],
                    }
                )

        return {
            "runs": run_payloads,
            "groups": groups,
            "summary": {
                "run_count": len(runs),
                "proposed_count": status_counts[StrategyIdeaStatus.PROPOSED],
                "in_review_count": status_counts[StrategyIdeaStatus.IN_REVIEW],
                "dismissed_count": status_counts[StrategyIdeaStatus.DISMISSED],
                "converted_count": status_counts[StrategyIdeaStatus.CONVERTED],
                "new_opportunities_count": (
                    status_counts[StrategyIdeaStatus.PROPOSED]
                    + status_counts[StrategyIdeaStatus.IN_REVIEW]
                ),
                "high_confidence_count": len(
                    [idea for idea in ideas if idea.opportunity_score >= 80]
                ),
                "hot_trends_count": len(
                    [idea for idea in ideas if idea.lifecycle_stage == "hot"]
                ),
                "converted_this_month_count": len(
                    [
                        idea
                        for idea in ideas
                        if idea.converted_at is not None
                        and idea.converted_at
                        >= datetime(
                            datetime.now(UTC).year,
                            datetime.now(UTC).month,
                            1,
                            tzinfo=UTC,
                        )
                    ]
                ),
                "average_opportunity_score": round(
                    sum(idea.opportunity_score for idea in ideas) / len(ideas)
                )
                if ideas
                else 0,
            },
        }

    def _run_payload(self, run: StrategyRun, idea_count: int) -> dict[str, object]:
        return {
            "id": run.id,
            "run_date": run.run_date,
            "topic": run.topic,
            "status": run.status,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "idea_count": idea_count,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
        }

    async def _action_response(
        self,
        idea_id: UUID,
        converted_series: Series | None = None,
    ) -> dict[str, object]:
        idea = await self._get_idea(idea_id)
        run = await self.session.get(StrategyRun, idea.run_id)
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy run not found",
            )
        if converted_series is not None:
            await self.session.refresh(converted_series)
        return {
            "workspace": await self._workspace_response(),
            "idea": self._idea_payload(idea, run),
            "converted_series": converted_series,
        }

    async def _get_idea(self, idea_id: UUID) -> StrategyIdea:
        idea = await self.session.get(StrategyIdea, idea_id)
        if idea is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy idea not found",
            )
        return idea

    async def _runs(self) -> list[StrategyRun]:
        result = await self.session.execute(
            select(StrategyRun).order_by(StrategyRun.run_date.desc(), StrategyRun.created_at.desc())
        )
        return list(result.scalars().all())

    async def _ideas(self) -> list[StrategyIdea]:
        result = await self.session.execute(
            select(StrategyIdea, StrategyRun)
            .join(StrategyRun, StrategyRun.id == StrategyIdea.run_id)
            .order_by(
                StrategyRun.run_date.desc(),
                StrategyIdea.status.asc(),
                StrategyIdea.opportunity_score.desc(),
                StrategyIdea.created_at.asc(),
            )
        )
        return [row[0] for row in result.all()]

    def _idea_payload(self, idea: StrategyIdea, run: StrategyRun) -> dict[str, object]:
        opportunity = self._opportunity_defaults(idea)
        return {
            "id": idea.id,
            "run_id": idea.run_id,
            "title": idea.title,
            "audience": idea.audience,
            "description": idea.description,
            "proposed_guest_name": idea.proposed_guest_name,
            "thesis": idea.thesis,
            "rationale": idea.rationale,
            "evidence_signals": idea.evidence_signals,
            "source_proposal": idea.source_proposal,
            "confidence_score": idea.confidence_score,
            "opportunity_score": opportunity["opportunity_score"],
            "opportunity_score_breakdown": opportunity["opportunity_score_breakdown"],
            "opportunity_score_explanation": opportunity["opportunity_score_explanation"],
            "audience_intelligence": opportunity["audience_intelligence"],
            "lifecycle_stage": opportunity["lifecycle_stage"],
            "season_potential": opportunity["season_potential"],
            "trend_intelligence": opportunity["trend_intelligence"],
            "source_count": opportunity["source_count"],
            "potential_episode_count": opportunity["potential_episode_count"],
            "theme_count": opportunity["theme_count"],
            "generated_at": opportunity["generated_at"],
            "status": idea.status,
            "reviewed_at": idea.reviewed_at,
            "dismissed_at": idea.dismissed_at,
            "converted_at": idea.converted_at,
            "converted_series_id": idea.converted_series_id,
            "run_date": run.run_date,
            "run_topic": run.topic,
            "created_at": idea.created_at,
            "updated_at": idea.updated_at,
        }

    def _episode_plan(self, idea: StrategyIdea) -> list[dict[str, str]]:
        raw_plan = idea.source_proposal.get("episode_plan", [])
        episodes = [
            {
                "title": str(item.get("title", "")).strip(),
                "premise": str(item.get("premise", "")).strip(),
            }
            for item in raw_plan
            if isinstance(item, dict)
        ]
        valid_episodes = [
            episode for episode in episodes if episode["title"] and episode["premise"]
        ]
        if valid_episodes:
            return valid_episodes
        return [
            {
                "title": f"Editorial review for {idea.title}",
                "premise": "Producer reviews the converted strategy proposal and curates the plan.",
            }
        ]

    def _opportunity_defaults(self, idea: StrategyIdea) -> dict[str, object]:
        episode_plan = idea.source_proposal.get("episode_plan", [])
        episode_count = len(episode_plan) if isinstance(episode_plan, list) else 0
        evidence_count = len(idea.evidence_signals or [])
        score = int(getattr(idea, "opportunity_score", 0) or idea.confidence_score or 0)
        breakdown = getattr(idea, "opportunity_score_breakdown", {}) or {
            "research_confidence": idea.confidence_score,
            "source_coverage": min(100, evidence_count * 20),
            "trend_strength": 0,
            "audience_fit": 50,
            "content_depth": min(100, episode_count * 20),
            "competition_signal": 50,
            "formula": (
                "research_confidence * 0.25 + source_coverage * 0.20 + "
                "trend_strength * 0.20 + audience_fit * 0.15 + "
                "content_depth * 0.10 + competition_signal * 0.10"
            ),
        }
        audience_intelligence = getattr(idea, "audience_intelligence", {}) or {
            "audience": idea.audience,
            "source_mix": [],
            "reason": "Audience intelligence has not been calculated for this legacy idea.",
            "fit_score": breakdown.get("audience_fit", 50),
        }
        season_potential = getattr(idea, "season_potential", {}) or {
            "potential_episodes": episode_count,
            "reason": "Season potential is based on the saved proposal episode plan.",
            "research_coverage": {
                "source_count": evidence_count,
                "document_count": evidence_count,
                "signals_extracted": evidence_count,
            },
            "theme_count": episode_count,
            "themes": [],
        }
        trend_intelligence = getattr(idea, "trend_intelligence", {}) or {
            "trend_available": False,
            "trend_source": None,
            "current_trend": 0,
            "previous_trend": 0,
            "trend_velocity": 0,
            "velocity_label": "Trend not available",
        }
        return {
            "opportunity_score": score,
            "opportunity_score_breakdown": breakdown,
            "opportunity_score_explanation": (
                getattr(idea, "opportunity_score_explanation", None)
                or "Opportunity score has not been calculated yet."
            ),
            "audience_intelligence": audience_intelligence,
            "lifecycle_stage": getattr(idea, "lifecycle_stage", None) or "emerging",
            "season_potential": season_potential,
            "trend_intelligence": trend_intelligence,
            "source_count": int(getattr(idea, "source_count", 0) or evidence_count),
            "potential_episode_count": int(
                getattr(idea, "potential_episode_count", 0) or episode_count
            ),
            "theme_count": int(getattr(idea, "theme_count", 0) or episode_count),
            "generated_at": getattr(idea, "generated_at", None) or idea.created_at,
        }

    def _range_start(self, range_value: str) -> datetime | None:
        now = datetime.now(UTC)
        normalized = range_value.lower()
        if normalized in {"today", "1d"}:
            return datetime(now.year, now.month, now.day, tzinfo=UTC)
        if normalized in {"7d", "7_days"}:
            return now - timedelta(days=7)
        if normalized in {"30d", "30_days"}:
            return now - timedelta(days=30)
        if normalized in {"90d", "90_days"}:
            return now - timedelta(days=90)
        return None
