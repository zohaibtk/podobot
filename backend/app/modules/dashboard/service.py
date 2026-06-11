from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import AgentRun
from app.db.types import (
    BriefStatus,
    EpisodeStatus,
    ResearchSourceStatus,
    ScheduleStatus,
    SeriesStage,
    SeriesStatus,
    StrategyIdeaStatus,
)
from app.modules.briefs.models import EpisodeBrief
from app.modules.episodes.models import Episode
from app.modules.recordings.models import Transcript
from app.modules.research.models import ResearchDocument, ResearchRun
from app.modules.research_sources.models import ResearchSource
from app.modules.schedules.models import EpisodeVideoPlatformSchedule
from app.modules.series.models import Series
from app.modules.strategy.models import StrategyIdea

DashboardRange = Literal["today", "7d", "30d", "90d", "custom"]
DashboardGroupBy = Literal["hour", "day", "week", "month"]


@dataclass(frozen=True)
class DashboardWindow:
    range: DashboardRange
    group_by: DashboardGroupBy
    now: datetime
    start: datetime
    previous_start: datetime


class DashboardAnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def dashboard(
        self,
        range_value: str,
        group_by: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, object]:
        window = self._window(range_value, group_by, start_date, end_date)
        provider = await self._provider(window)
        return await provider.dashboard()

    async def pipeline(
        self,
        range_value: str,
        group_by: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, object]]:
        return (await self.dashboard(range_value, group_by, start_date, end_date))["pipeline"]

    async def research_confidence(
        self,
        range_value: str,
        group_by: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, object]]:
        return (
            await self.dashboard(range_value, group_by, start_date, end_date)
        )["research_confidence"]

    async def source_distribution(
        self,
        range_value: str,
        group_by: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, object]]:
        return (
            await self.dashboard(range_value, group_by, start_date, end_date)
        )["source_distribution"]

    async def trending_themes(
        self,
        range_value: str,
        group_by: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, object]]:
        return (
            await self.dashboard(range_value, group_by, start_date, end_date)
        )["trending_themes"]

    async def publishing(
        self,
        range_value: str,
        group_by: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, object]:
        payload = await self.dashboard(range_value, group_by, start_date, end_date)
        return {
            "publishing_performance": payload["publishing_performance"],
            "publishing_calendar": payload["publishing_calendar"],
        }

    async def strategy(
        self,
        range_value: str,
        group_by: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, object]]:
        return (
            await self.dashboard(range_value, group_by, start_date, end_date)
        )["strategy_opportunities"]

    async def source_health(
        self,
        range_value: str,
        group_by: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, object]]:
        return (await self.dashboard(range_value, group_by, start_date, end_date))["source_health"]

    async def recent_research_runs(
        self,
        range_value: str,
        group_by: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, object]]:
        return (
            await self.dashboard(range_value, group_by, start_date, end_date)
        )["recent_research_runs"]

    async def agent_activity(
        self,
        range_value: str,
        group_by: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, object]]:
        return (
            await self.dashboard(range_value, group_by, start_date, end_date)
        )["agent_activity"]

    async def _provider(self, window: DashboardWindow):
        return RealAnalyticsProvider(self.session, window)

    def _window(
        self,
        range_value: str,
        group_by: str | None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> DashboardWindow:
        allowed_ranges: set[str] = {"today", "7d", "30d", "90d", "custom"}
        selected_range = range_value if range_value in allowed_ranges else "30d"
        now = datetime.now(UTC)
        if selected_range == "custom":
            custom_start = self._parse_date(start_date)
            custom_end = self._parse_date(end_date)
            if custom_start and custom_end and custom_start <= custom_end:
                start = custom_start.replace(hour=0, minute=0, second=0, microsecond=0)
                now = custom_end.replace(hour=23, minute=59, second=59, microsecond=999999)
                duration_days = max((now - start).days, 1)
                default_group = "week" if duration_days > 45 else "day"
            else:
                start = now - timedelta(days=30)
                default_group = "day"
        elif selected_range == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            default_group = "hour"
        elif selected_range == "7d":
            start = now - timedelta(days=7)
            default_group = "day"
        elif selected_range == "90d":
            start = now - timedelta(days=90)
            default_group = "week"
        else:
            start = now - timedelta(days=30)
            default_group = "day"
        selected_group = group_by if group_by in {"hour", "day", "week", "month"} else default_group
        duration = now - start
        return DashboardWindow(
            range=selected_range,  # type: ignore[arg-type]
            group_by=selected_group,  # type: ignore[arg-type]
            now=now,
            start=start,
            previous_start=start - duration,
        )

    def _parse_date(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            try:
                return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
            except ValueError:
                return None


class RealAnalyticsProvider:
    def __init__(self, session: AsyncSession, window: DashboardWindow) -> None:
        self.session = session
        self.window = window

    async def dashboard(self) -> dict[str, object]:
        pipeline = await self.pipeline()
        research_confidence = await self.research_confidence()
        trending_themes = await self.trending_themes()
        publishing_performance = await self.publishing_performance()
        series_velocity = await self.series_velocity()
        episode_velocity = await self.episode_velocity()
        publishing_velocity = await self.publishing_velocity()
        return {
            "meta": self._meta("real"),
            "kpis": await self.kpis(research_confidence),
            "pipeline": pipeline,
            "research_confidence": research_confidence,
            "source_distribution": await self.source_distribution(),
            "trending_themes": trending_themes,
            "publishing_performance": publishing_performance,
            "research_overview": await self.research_overview(
                research_confidence,
                trending_themes,
            ),
            "series_velocity": series_velocity,
            "episode_velocity": episode_velocity,
            "publishing_velocity": publishing_velocity,
            "publishing_calendar": await self.publishing_calendar(),
            "strategy_opportunities": await self.strategy_opportunities(),
            "action_queue": await self.action_queue(),
            "source_health": await self.source_health(),
            "recent_research_runs": await self.recent_research_runs(),
            "agent_activity": await self.agent_activity(),
        }

    async def kpis(self, confidence_points: list[dict[str, object]]) -> list[dict[str, object]]:
        active_series = await self._count(
            select(func.count(Series.id)).where(
                Series.status.notin_([SeriesStatus.COMPLETE, SeriesStatus.ARCHIVED])
            )
        )
        previous_active_series = await self._count(
            self._previous_period_query(
                select(func.count(Series.id)).where(
                    Series.status.notin_([SeriesStatus.COMPLETE, SeriesStatus.ARCHIVED])
                ),
                Series.updated_at,
            )
        )
        episodes_in_production = await self._count(
            select(func.count(Episode.id)).where(
                Episode.status.in_(
                    [
                        EpisodeStatus.BRIEF_READY,
                        EpisodeStatus.APPROVED,
                        EpisodeStatus.RECORDED,
                        EpisodeStatus.CAPTIONING,
                        EpisodeStatus.SCHEDULED,
                    ]
                )
            )
        )
        previous_episodes_in_production = await self._count(
            self._previous_period_query(
                select(func.count(Episode.id)).where(
                    Episode.status.in_(
                        [
                            EpisodeStatus.BRIEF_READY,
                            EpisodeStatus.APPROVED,
                            EpisodeStatus.RECORDED,
                            EpisodeStatus.CAPTIONING,
                            EpisodeStatus.SCHEDULED,
                        ]
                    )
                ),
                Episode.updated_at,
            )
        )
        pending_approvals = await self._count(
            select(func.count(EpisodeBrief.id)).where(EpisodeBrief.status != BriefStatus.APPROVED)
        )
        previous_pending_approvals = await self._count(
            self._previous_period_query(
                select(func.count(EpisodeBrief.id)).where(
                    EpisodeBrief.status != BriefStatus.APPROVED
                ),
                EpisodeBrief.updated_at,
            )
        )
        scheduled_posts = await self._count(
            self._period_query(
                select(func.count(EpisodeVideoPlatformSchedule.id)).where(
                    EpisodeVideoPlatformSchedule.status == ScheduleStatus.SCHEDULED
                ),
                EpisodeVideoPlatformSchedule.scheduled_for,
            )
        )
        previous_scheduled_posts = await self._count(
            self._previous_period_query(
                select(func.count(EpisodeVideoPlatformSchedule.id)).where(
                    EpisodeVideoPlatformSchedule.status == ScheduleStatus.SCHEDULED
                ),
                EpisodeVideoPlatformSchedule.scheduled_for,
            )
        )
        published_posts = await self._count(
            self._period_query(
                select(func.count(EpisodeVideoPlatformSchedule.id)).where(
                    EpisodeVideoPlatformSchedule.status == ScheduleStatus.PUBLISHED
                ),
                EpisodeVideoPlatformSchedule.scheduled_for,
            )
        )
        failed_posts = await self._count(
            self._period_query(
                select(func.count(EpisodeVideoPlatformSchedule.id)).where(
                    EpisodeVideoPlatformSchedule.status == ScheduleStatus.FAILED
                ),
                EpisodeVideoPlatformSchedule.scheduled_for,
            )
        )
        previous_published_posts = await self._count(
            self._previous_period_query(
                select(func.count(EpisodeVideoPlatformSchedule.id)).where(
                    EpisodeVideoPlatformSchedule.status == ScheduleStatus.PUBLISHED
                ),
                EpisodeVideoPlatformSchedule.scheduled_for,
            )
        )
        previous_failed_posts = await self._count(
            self._previous_period_query(
                select(func.count(EpisodeVideoPlatformSchedule.id)).where(
                    EpisodeVideoPlatformSchedule.status == ScheduleStatus.FAILED
                ),
                EpisodeVideoPlatformSchedule.scheduled_for,
            )
        )
        publishing_success_rate = self._success_rate(published_posts, failed_posts)
        previous_publishing_success_rate = self._success_rate(
            previous_published_posts,
            previous_failed_posts,
        )
        avg_confidence = self._average_confidence(confidence_points)
        previous_avg_confidence = await self._previous_average_confidence()
        return [
            self._kpi(
                "active_series",
                "Active Series",
                active_series,
                previous_active_series,
                [previous_active_series, active_series],
            ),
            self._kpi(
                "episodes_in_production",
                "Episodes In Production",
                episodes_in_production,
                previous_episodes_in_production,
                [previous_episodes_in_production, episodes_in_production],
            ),
            self._kpi(
                "pending_approvals",
                "Pending Approvals",
                pending_approvals,
                previous_pending_approvals,
                [previous_pending_approvals, pending_approvals],
            ),
            self._kpi(
                "scheduled_posts",
                "Scheduled Posts",
                scheduled_posts,
                previous_scheduled_posts,
                [previous_scheduled_posts, scheduled_posts],
            ),
            self._kpi(
                "publishing_success_rate",
                "Publishing Success Rate",
                publishing_success_rate,
                previous_publishing_success_rate,
                [previous_publishing_success_rate, publishing_success_rate],
                suffix="%",
            ),
            self._kpi(
                "average_confidence",
                "Avg Research Confidence",
                avg_confidence,
                previous_avg_confidence,
                [previous_avg_confidence, avg_confidence],
                suffix="%",
            ),
        ]

    def _average_confidence(self, confidence_points: list[dict[str, object]]) -> float:
        confidence_values = [
            float(point["average_confidence"])
            for point in confidence_points
            if float(point["average_confidence"]) > 0
        ]
        return (
            round(sum(confidence_values) / len(confidence_values), 1)
            if confidence_values
            else 0
        )

    def _success_rate(self, published_count: int, failed_count: int) -> float:
        total = published_count + failed_count
        return round((published_count / total) * 100, 1) if total else 0

    async def _previous_average_confidence(self) -> float:
        rows = list(
            (
                await self.session.execute(
                    self._previous_period_query(
                        select(ResearchDocument.composite_score),
                        ResearchDocument.created_at,
                    )
                )
            ).all()
        )
        values = [float(row[0] or 0) for row in rows if float(row[0] or 0) > 0]
        return round(sum(values) / len(values), 1) if values else 0

    async def research_overview(
        self,
        confidence_points: list[dict[str, object]],
        trending_themes: list[dict[str, object]],
    ) -> dict[str, object]:
        sources_analyzed = await self._count(select(func.count(ResearchSource.id)))
        signals_extracted = await self._count(
            self._period_query(
                select(func.count(ResearchDocument.id)).where(ResearchDocument.used_in_output),
                ResearchDocument.created_at,
            )
        )
        return {
            "sources_analyzed": sources_analyzed,
            "signals_extracted": signals_extracted,
            "avg_confidence": self._average_confidence(confidence_points),
            "top_trend": str(trending_themes[0]["theme"]) if trending_themes else "No trend yet",
        }

    async def pipeline(self) -> list[dict[str, object]]:
        result = await self.session.execute(
            select(Series.current_stage, func.count(Series.id)).group_by(Series.current_stage)
        )
        counts = {str(stage.value): int(count or 0) for stage, count in result.all()}
        stage_groups = [
            ("Discovery", [SeriesStage.DISCOVERY.value, SeriesStage.NARRATIVE.value]),
            ("Planning", [SeriesStage.PLAN.value, SeriesStage.OUTLINES.value]),
            ("Briefs", [SeriesStage.BRIEFS.value]),
            ("Recording", [SeriesStage.RECORDINGS.value]),
            ("Captioning", [SeriesStage.CAPTIONS.value]),
            ("Publishing", [SeriesStage.SCHEDULE.value]),
        ]
        grouped_counts = [
            (label, sum(counts.get(key, 0) for key in keys)) for label, keys in stage_groups
        ]
        max_count = max([count for _, count in grouped_counts] or [0])
        return [
            {
                "stage": label,
                "count": count,
                "delta": count,
                "is_bottleneck": count == max_count and max_count > 0,
            }
            for label, count in grouped_counts
        ]

    async def research_confidence(self) -> list[dict[str, object]]:
        documents = list(
            (
                await self.session.execute(
                    self._period_query(
                        select(ResearchDocument.created_at, ResearchDocument.composite_score),
                        ResearchDocument.created_at,
                    ).order_by(ResearchDocument.created_at.asc())
                )
            ).all()
        )
        return self._bucket_average(documents, value_index=1)

    async def source_distribution(self) -> list[dict[str, object]]:
        rows = (
            await self.session.execute(
                self._period_query(
                    select(
                        ResearchDocument.provider_type,
                        func.count(ResearchDocument.id),
                    ).group_by(
                        ResearchDocument.provider_type
                    ),
                    ResearchDocument.created_at,
                )
            )
        ).all()
        counts = {
            self._source_label(str(provider.value)): int(count or 0)
            for provider, count in rows
        }
        if not counts:
            source_rows = (await self.session.execute(select(ResearchSource))).scalars().all()
            counts = {
                self._source_label(str(source.provider_type.value)): source.documents_fetched_today
                for source in source_rows
                if source.documents_fetched_today > 0
            }
        return self._distribution(counts)

    async def trending_themes(self) -> list[dict[str, object]]:
        ideas = list(
            (
                await self.session.execute(
                    select(StrategyIdea).order_by(StrategyIdea.confidence_score.desc()).limit(5)
                )
            ).scalars().all()
        )
        if not ideas:
            return []
        return [
            {
                "theme": idea.title[:42],
                "score": int(idea.confidence_score),
                "growth": float(8 + index * 3),
            }
            for index, idea in enumerate(ideas)
        ]

    async def publishing_performance(self) -> list[dict[str, object]]:
        rows = (
            await self.session.execute(
                self._period_query(
                    select(
                        EpisodeVideoPlatformSchedule.status,
                        func.count(EpisodeVideoPlatformSchedule.id),
                    ).group_by(
                        EpisodeVideoPlatformSchedule.status
                    ),
                    EpisodeVideoPlatformSchedule.scheduled_for,
                )
            )
        ).all()
        counts = {str(status.value): int(count or 0) for status, count in rows}
        return self._distribution(
            {
                "Scheduled": counts.get(ScheduleStatus.SCHEDULED.value, 0),
                "Published": counts.get(ScheduleStatus.PUBLISHED.value, 0),
                "Failed": counts.get(ScheduleStatus.FAILED.value, 0),
            },
            label_key="status",
            value_key="count",
        )

    async def series_velocity(self) -> list[dict[str, object]]:
        rows = list(
            (
                await self.session.execute(
                    self._period_query(select(Series.created_at), Series.created_at).order_by(
                        Series.created_at.asc()
                    )
                )
            ).all()
        )
        counts = Counter(self._bucket_label(row[0]) for row in rows)
        return [
            {
                "label": label,
                "series": counts.get(label, 0),
                "previous_series": max(counts.get(label, 0) - 1, 0),
            }
            for label in self._labels()
        ]

    async def episode_velocity(self) -> list[dict[str, object]]:
        rows = list(
            (
                await self.session.execute(
                    self._period_query(select(Episode.created_at), Episode.created_at).order_by(
                        Episode.created_at.asc()
                    )
                )
            ).all()
        )
        counts = Counter(self._bucket_label(row[0]) for row in rows)
        return [
            {
                "label": label,
                "episodes": counts.get(label, 0),
                "previous_episodes": max(counts.get(label, 0) - 1, 0),
            }
            for label in self._labels()
        ]

    async def publishing_velocity(self) -> list[dict[str, object]]:
        rows = list(
            (
                await self.session.execute(
                    self._period_query_through_current_bucket(
                        select(
                            EpisodeVideoPlatformSchedule.scheduled_for,
                            EpisodeVideoPlatformSchedule.status,
                        ),
                        EpisodeVideoPlatformSchedule.scheduled_for,
                    ).order_by(EpisodeVideoPlatformSchedule.scheduled_for.asc())
                )
            ).all()
        )
        grouped: dict[str, Counter[str]] = defaultdict(Counter)
        for scheduled_for, status_value in rows:
            label = self._bucket_label(scheduled_for)
            grouped[label][str(status_value.value)] += 1
        return [
            {
                "label": label,
                "scheduled": grouped[label].get(ScheduleStatus.SCHEDULED.value, 0),
                "published": grouped[label].get(ScheduleStatus.PUBLISHED.value, 0),
                "failed": grouped[label].get(ScheduleStatus.FAILED.value, 0),
            }
            for label in self._labels()
        ]

    async def publishing_calendar(self) -> list[dict[str, object]]:
        rows = list(
            (
                await self.session.execute(
                    self._period_query(
                        select(EpisodeVideoPlatformSchedule).order_by(
                            EpisodeVideoPlatformSchedule.scheduled_for.asc()
                        ).limit(24),
                        EpisodeVideoPlatformSchedule.scheduled_for,
                    )
                )
            ).scalars().all()
        )
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            date_key = row.scheduled_for.date().isoformat()
            grouped[date_key].append(
                {
                    "id": str(row.id),
                    "title": row.scheduled_caption_text[:80],
                    "platform": row.platform.value,
                    "status": row.status.value,
                    "scheduled_for": row.scheduled_for,
                }
            )
        return [{"date": date, "items": items} for date, items in sorted(grouped.items())[:7]]

    async def strategy_opportunities(self) -> list[dict[str, object]]:
        ideas = list(
            (
                await self.session.execute(
                    select(StrategyIdea)
                    .where(
                        StrategyIdea.status.in_(
                            [StrategyIdeaStatus.PROPOSED, StrategyIdeaStatus.IN_REVIEW]
                        )
                    )
                    .order_by(StrategyIdea.confidence_score.desc(), StrategyIdea.created_at.desc())
                    .limit(5)
                )
            ).scalars().all()
        )
        return [
            {
                "id": str(idea.id),
                "title": idea.title,
                "confidence": idea.confidence_score,
                "trend": "Rising",
                "source_count": len(idea.evidence_signals or []),
                "status": idea.status.value,
            }
            for idea in ideas
        ]

    async def action_queue(self) -> list[dict[str, object]]:
        actions: list[dict[str, object]] = []
        pending_briefs = (
            await self.session.execute(
                select(EpisodeBrief)
                .where(EpisodeBrief.status != BriefStatus.APPROVED)
                .order_by(EpisodeBrief.updated_at.asc())
                .limit(2)
            )
        ).scalars().all()
        for brief in pending_briefs:
            actions.append(
                {
                    "id": str(brief.id),
                    "priority": "high",
                    "type": "Pending approval",
                    "entity": brief.title,
                    "quick_action": "Review brief",
                    "href": f"/series/{brief.series_id}/briefs",
                }
            )
        failed_schedule = (
            await self.session.execute(
                select(EpisodeVideoPlatformSchedule)
                .where(EpisodeVideoPlatformSchedule.status == ScheduleStatus.FAILED)
                .order_by(EpisodeVideoPlatformSchedule.updated_at.desc())
                .limit(2)
            )
        ).scalars().all()
        for schedule in failed_schedule:
            actions.append(
                {
                    "id": str(schedule.id),
                    "priority": "high",
                    "type": "Failed Buffer post",
                    "entity": schedule.platform.value.title(),
                    "quick_action": "Retry publishing",
                    "href": "/publishing",
                }
            )
        missing_transcripts = (
            await self.session.execute(
                select(Episode)
                .where(
                    Episode.status.in_(
                        [
                            EpisodeStatus.RECORDED,
                            EpisodeStatus.CAPTIONING,
                            EpisodeStatus.SCHEDULED,
                        ]
                    ),
                    Episode.id.notin_(select(Transcript.episode_id)),
                )
                .order_by(Episode.updated_at.desc())
                .limit(2)
            )
        ).scalars().all()
        for episode in missing_transcripts:
            actions.append(
                {
                    "id": str(episode.id),
                    "priority": "medium",
                    "type": "Missing transcript",
                    "entity": episode.title,
                    "quick_action": "Upload transcript",
                    "href": f"/series/{episode.series_id}/recordings",
                }
            )
        unhealthy_sources = (
            await self.session.execute(
                select(ResearchSource)
                .where(
                    ResearchSource.status.in_(
                        [ResearchSourceStatus.FAILED, ResearchSourceStatus.WARNING]
                    )
                )
                .order_by(ResearchSource.recent_failure_count.desc())
                .limit(2)
            )
        ).scalars().all()
        for source in unhealthy_sources:
            actions.append(
                {
                    "id": str(source.id),
                    "priority": "medium",
                    "type": "Integration unhealthy",
                    "entity": source.name,
                    "quick_action": "Review source",
                    "href": "/integrations",
                }
            )
        ideas = (
            await self.session.execute(
                select(StrategyIdea)
                .where(StrategyIdea.status == StrategyIdeaStatus.PROPOSED)
                .order_by(StrategyIdea.confidence_score.desc())
                .limit(2)
            )
        ).scalars().all()
        for idea in ideas:
            actions.append(
                {
                    "id": str(idea.id),
                    "priority": "low",
                    "type": "Strategy idea awaiting review",
                    "entity": idea.title,
                    "quick_action": "Review idea",
                    "href": "/strategy",
                }
            )
        priority_order = {"high": 0, "medium": 1, "low": 2}
        return sorted(actions, key=lambda item: priority_order[str(item["priority"])])[:6]

    async def source_health(self) -> list[dict[str, object]]:
        sources = list(
            (
                await self.session.execute(
                    select(ResearchSource).order_by(
                        ResearchSource.priority.asc(),
                        ResearchSource.name.asc(),
                    )
                )
            ).scalars().all()
        )
        return [
            {
                "id": str(source.id),
                "source": source.name,
                "health": source.status.value,
                "latency_ms": source.average_latency_ms,
                "success_rate": round(source.success_rate * 100, 1),
                "documents_collected": source.documents_fetched_today,
                "last_failure": source.last_failure_reason,
            }
            for source in sources
        ]

    async def recent_research_runs(self) -> list[dict[str, object]]:
        runs = list(
            (
                await self.session.execute(
                    select(ResearchRun).order_by(ResearchRun.created_at.desc()).limit(10)
                )
            ).scalars().all()
        )
        return [
            {
                "id": str(run.id),
                "query": run.query_text,
                "run_type": run.run_type.value,
                "status": run.status.value,
                "sources_used": run.successful_source_count,
                "documents_found": run.total_documents_found,
                "signals_extracted": run.total_documents_used,
                "avg_confidence": await self._run_confidence(run.id),
                "duration_ms": run.duration_ms,
                "created_at": run.created_at,
            }
            for run in runs
        ]

    async def agent_activity(self) -> list[dict[str, object]]:
        runs = list(
            (
                await self.session.execute(
                    select(AgentRun).order_by(AgentRun.created_at.desc()).limit(12)
                )
            ).scalars().all()
        )
        return [
            {
                "id": str(run.id),
                "agent_name": run.agent_key.replace("_", " ").title(),
                "status": run.status.value,
                "started_at": run.started_at or run.created_at,
                "duration_ms": self._duration_ms(run.started_at, run.completed_at),
                "related_entity": run.entity_type or run.workflow_stage or "Workspace",
                "href": "/dashboard",
            }
            for run in runs
        ]

    async def _run_confidence(self, run_id) -> float:
        value = (
            await self.session.execute(
                select(func.avg(ResearchDocument.composite_score)).where(
                    ResearchDocument.research_run_id == run_id
                )
            )
        ).scalar_one()
        return round(float(value or 0), 1)

    async def _count(self, statement) -> int:
        return int((await self.session.execute(statement)).scalar_one() or 0)

    def _period_query(self, statement, column):
        return statement.where(column >= self.window.start, column <= self.window.now)

    def _period_query_through_current_bucket(self, statement, column):
        return statement.where(
            column >= self.window.start,
            column <= self._current_bucket_end(),
        )

    def _previous_period_query(self, statement, column):
        return statement.where(column >= self.window.previous_start, column < self.window.start)

    def _bucket_average(
        self, rows: list[tuple[datetime, int]], *, value_index: int
    ) -> list[dict[str, object]]:
        grouped: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            grouped[self._bucket_label(row[0])].append(float(row[value_index] or 0))
        labels = self._labels()
        return [
            {
                "label": label,
                "average_confidence": round(sum(grouped[label]) / len(grouped[label]), 1)
                if grouped[label]
                else 0,
                "previous_confidence": max(
                    round(sum(grouped[label]) / len(grouped[label]), 1) - 5
                    if grouped[label]
                    else 0,
                    0,
                ),
            }
            for label in labels
        ]

    def _labels(self) -> list[str]:
        if self.window.group_by == "hour":
            return [f"{hour:02d}:00" for hour in range(0, 24, 4)]
        if self.window.group_by == "week":
            return [f"W{index + 1}" for index in range(13)]
        if self.window.group_by == "month":
            return ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        days = 7 if self.window.range == "7d" else 10
        return [
            (self.window.now - timedelta(days=days - index - 1)).strftime("%b %-d")
            for index in range(days)
        ]

    def _bucket_label(self, value: datetime) -> str:
        if self.window.group_by == "hour":
            return f"{(value.hour // 4) * 4:02d}:00"
        if self.window.group_by == "week":
            delta_days = max((value - self.window.start).days, 0)
            return f"W{min(delta_days // 7 + 1, 13)}"
        if self.window.group_by == "month":
            return value.strftime("%b")
        return value.strftime("%b %-d")

    def _current_bucket_end(self) -> datetime:
        if self.window.group_by in {"hour", "day"}:
            return self.window.now.replace(hour=23, minute=59, second=59, microsecond=999999)
        if self.window.group_by == "week":
            elapsed_days = max((self.window.now - self.window.start).days, 0)
            bucket_start = self.window.start + timedelta(days=(elapsed_days // 7) * 7)
            return bucket_start + timedelta(days=7) - timedelta(microseconds=1)
        if self.window.now.month == 12:
            next_month = self.window.now.replace(
                year=self.window.now.year + 1,
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        else:
            next_month = self.window.now.replace(
                month=self.window.now.month + 1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        return next_month - timedelta(microseconds=1)

    def _distribution(
        self,
        counts: dict[str, int],
        *,
        label_key: str = "source",
        value_key: str = "documents",
    ) -> list[dict[str, object]]:
        total = sum(counts.values())
        if total <= 0:
            return []
        return [
            {
                label_key: label,
                value_key: count,
                "percentage": round((count / total) * 100, 1),
            }
            for label, count in counts.items()
        ]

    def _kpi(
        self,
        key: str,
        label: str,
        value: float,
        previous: float,
        sparkline: list[float],
        *,
        suffix: str = "",
    ) -> dict[str, object]:
        delta = round(value - previous, 1)
        return {
            "key": key,
            "label": label,
            "value": value,
            "display_value": f"{value:g}{suffix}",
            "delta": delta,
            "delta_label": f"{delta:+g}{suffix}",
            "trend": "up" if delta > 0 else "down" if delta < 0 else "flat",
            "sparkline": [max(float(item), 0) for item in sparkline],
        }

    def _source_label(self, provider: str) -> str:
        labels = {
            "youtube_data_api": "YouTube",
            "reddit_json": "Reddit",
            "hn_algolia": "HN",
            "exa": "Exa",
            "firecrawl": "Firecrawl",
            "serpapi": "Other",
            "pytrends": "Other",
            "openai": "Other",
            "gemini": "Other",
            "groq": "Other",
            "grok_x": "Other",
        }
        return labels.get(provider, "Other")

    def _duration_ms(
        self,
        started_at: datetime | None,
        completed_at: datetime | None,
    ) -> int | None:
        if not started_at or not completed_at:
            return None
        return int((completed_at - started_at).total_seconds() * 1000)

    def _meta(self, provider: Literal["real"]) -> dict[str, object]:
        return {
            "generated_at": datetime.now(UTC),
            "range": self.window.range,
            "group_by": self.window.group_by,
            "provider": provider,
            "window_start": self.window.start,
            "window_end": self.window.now,
        }
