from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.types import CaptionVideoKind, Platform, ScheduleStatus
from app.modules.captions.models import EpisodeVideoPlatformCaption
from app.modules.episodes.models import Episode
from app.modules.schedules.models import (
    BufferChannel,
    BufferWebhook,
    EpisodeVideoPlatformSchedule,
    PublishingAuditLog,
)
from app.modules.series.models import Series
from app.schemas.pagination import OffsetParams, offset_meta


@dataclass(frozen=True)
class AnalyticsFilters:
    date_from: datetime | None = None
    date_to: datetime | None = None
    platforms: list[Platform] | None = None
    video_kinds: list[CaptionVideoKind] | None = None


@dataclass(frozen=True)
class ScheduleAnalyticsRow:
    schedule: EpisodeVideoPlatformSchedule
    series: Series
    episode: Episode
    caption: EpisodeVideoPlatformCaption
    channel: BufferChannel | None


class PublishingAnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def workspace(self, filters: AnalyticsFilters) -> dict[str, object]:
        rows = await self._rows(filters)
        schedule_ids = [row.schedule.id for row in rows]
        audit_events = await self.audit_events(filters=filters, limit=80)
        webhook_count = await self._webhook_count(schedule_ids)
        return {
            "generated_at": datetime.now(UTC),
            "filters": self._filter_payload(filters),
            "success_metrics": self.success_metrics(
                rows,
                audit_event_count=len(audit_events),
                webhook_event_count=webhook_count,
            ),
            "channel_performance": self.channel_performance(rows),
            "content_performance": self.content_performance(rows),
            "failure_metrics": self.failure_metrics(rows),
            "best_times": self.best_times(rows),
            "caption_effectiveness": self.caption_effectiveness(rows),
            "trends": self.trends(rows),
            "executive_insights": self.executive_insights(rows),
            "audit_events": audit_events,
        }

    async def channels(self, filters: AnalyticsFilters) -> list[dict[str, object]]:
        return self.channel_performance(await self._rows(filters))

    async def content(self, filters: AnalyticsFilters) -> list[dict[str, object]]:
        return self.content_performance(await self._rows(filters))

    async def executive_report(self, filters: AnalyticsFilters) -> dict[str, object]:
        workspace = await self.workspace(filters)
        return {
            "generated_at": workspace["generated_at"],
            "filters": workspace["filters"],
            "success_metrics": workspace["success_metrics"],
            "top_channels": workspace["channel_performance"][:5],
            "top_content": workspace["content_performance"][:8],
            "best_times": workspace["best_times"][:5],
            "executive_insights": workspace["executive_insights"],
            "audit_events": workspace["audit_events"],
        }

    async def audit_events(
        self,
        *,
        filters: AnalyticsFilters,
        limit: int = 100,
    ) -> list[PublishingAuditLog]:
        page = await self.audit_events_page(filters=filters, page=1, page_size=limit)
        return page["items"]

    async def audit_events_page(
        self,
        *,
        filters: AnalyticsFilters,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, object]:
        schedule_ids = await self._filtered_schedule_ids(filters)
        if not schedule_ids and self._has_any_filter(filters):
            return {
                "items": [],
                **offset_meta(total=0, page=page, page_size=page_size),
            }

        pagination = OffsetParams(page=page, page_size=page_size)
        stmt = select(PublishingAuditLog).order_by(
            PublishingAuditLog.created_at.desc(), PublishingAuditLog.id.desc()
        )
        total_stmt = select(func.count(PublishingAuditLog.id))
        if schedule_ids:
            stmt = stmt.where(PublishingAuditLog.schedule_id.in_(schedule_ids))
            total_stmt = total_stmt.where(PublishingAuditLog.schedule_id.in_(schedule_ids))

        total = int((await self.session.execute(total_stmt)).scalar_one())
        items = list(
            (
                await self.session.execute(
                    stmt.offset(pagination.offset).limit(pagination.page_size)
                )
            )
            .scalars()
            .all()
        )
        return {
            "items": items,
            **offset_meta(total=total, page=page, page_size=page_size),
        }

    def success_metrics(
        self,
        rows: list[ScheduleAnalyticsRow],
        *,
        audit_event_count: int,
        webhook_event_count: int,
    ) -> dict[str, object]:
        counts = Counter(row.schedule.status for row in rows)
        outcome_count = (
            counts[ScheduleStatus.PUBLISHED]
            + counts[ScheduleStatus.FAILED]
            + counts[ScheduleStatus.CANCELLED]
        )
        retry_count = sum(row.schedule.retry_count for row in rows)
        return {
            "total_rows": len(rows),
            "scheduled_count": counts[ScheduleStatus.SCHEDULED],
            "published_count": counts[ScheduleStatus.PUBLISHED],
            "failed_count": counts[ScheduleStatus.FAILED],
            "cancelled_count": counts[ScheduleStatus.CANCELLED],
            "retry_count": retry_count,
            "success_rate": _rate(counts[ScheduleStatus.PUBLISHED], outcome_count),
            "failure_rate": _rate(counts[ScheduleStatus.FAILED], outcome_count),
            "average_retry_count": _average(retry_count, len(rows)),
            "audit_event_count": audit_event_count,
            "webhook_event_count": webhook_event_count,
        }

    def channel_performance(self, rows: list[ScheduleAnalyticsRow]) -> list[dict[str, object]]:
        groups: dict[tuple[UUID | None, Platform], list[ScheduleAnalyticsRow]] = defaultdict(list)
        for row in rows:
            groups[(row.channel.id if row.channel else None, row.schedule.platform)].append(row)

        items = []
        for (channel_id, platform), group in groups.items():
            counts = Counter(row.schedule.status for row in group)
            channel = group[0].channel
            outcome_count = (
                counts[ScheduleStatus.PUBLISHED]
                + counts[ScheduleStatus.FAILED]
                + counts[ScheduleStatus.CANCELLED]
            )
            failed = counts[ScheduleStatus.FAILED]
            health_status = "healthy"
            if failed:
                health_status = "degraded"
            if channel and (not channel.is_enabled or channel.is_queue_paused):
                health_status = "broken" if not channel.is_enabled else "degraded"
            items.append(
                {
                    "channel_id": channel_id,
                    "channel_name": (
                        channel.display_name if channel else f"Unmapped {platform.value}"
                    ),
                    "platform": platform,
                    "scheduled_count": counts[ScheduleStatus.SCHEDULED],
                    "published_count": counts[ScheduleStatus.PUBLISHED],
                    "failed_count": failed,
                    "cancelled_count": counts[ScheduleStatus.CANCELLED],
                    "success_rate": _rate(counts[ScheduleStatus.PUBLISHED], outcome_count),
                    "failure_rate": _rate(failed, outcome_count),
                    "retry_count": sum(row.schedule.retry_count for row in group),
                    "is_enabled": bool(channel.is_enabled) if channel else False,
                    "is_queue_paused": bool(channel.is_queue_paused) if channel else False,
                    "health_status": health_status,
                }
            )
        return sorted(
            items,
            key=lambda item: (
                -float(item["success_rate"]),
                -int(item["published_count"]),
                str(item["channel_name"]),
            ),
        )

    def content_performance(self, rows: list[ScheduleAnalyticsRow]) -> list[dict[str, object]]:
        groups: dict[tuple[UUID, CaptionVideoKind], list[ScheduleAnalyticsRow]] = defaultdict(list)
        for row in rows:
            groups[(row.episode.id, row.schedule.video_kind)].append(row)

        items = []
        for (_episode_id, video_kind), group in groups.items():
            counts = Counter(row.schedule.status for row in group)
            outcome_count = (
                counts[ScheduleStatus.PUBLISHED]
                + counts[ScheduleStatus.FAILED]
                + counts[ScheduleStatus.CANCELLED]
            )
            caption_lengths = [
                len(row.schedule.scheduled_caption_text or row.caption.caption_text or "")
                for row in group
            ]
            generation_counts = [row.caption.generation_count for row in group]
            success_rate = _rate(counts[ScheduleStatus.PUBLISHED], outcome_count)
            trend_score = round(
                success_rate
                + (counts[ScheduleStatus.PUBLISHED] * 8)
                - (counts[ScheduleStatus.FAILED] * 10)
                - (_average(sum(generation_counts), len(generation_counts)) * 2),
                2,
            )
            first = group[0]
            items.append(
                {
                    "series_id": first.series.id,
                    "series_name": first.series.name,
                    "episode_id": first.episode.id,
                    "episode_title": first.episode.title,
                    "episode_number": first.episode.episode_number,
                    "video_kind": video_kind,
                    "platforms": sorted(
                        {row.schedule.platform for row in group},
                        key=lambda platform: platform.value,
                    ),
                    "scheduled_count": counts[ScheduleStatus.SCHEDULED],
                    "published_count": counts[ScheduleStatus.PUBLISHED],
                    "failed_count": counts[ScheduleStatus.FAILED],
                    "success_rate": success_rate,
                    "average_caption_characters": int(
                        round(_average(sum(caption_lengths), len(caption_lengths)))
                    ),
                    "average_caption_generations": _average(
                        sum(generation_counts),
                        len(generation_counts),
                    ),
                    "trend_score": trend_score,
                }
            )
        return sorted(
            items,
            key=lambda item: (
                -float(item["trend_score"]),
                -int(item["published_count"]),
                int(item["episode_number"]),
            ),
        )

    def failure_metrics(self, rows: list[ScheduleAnalyticsRow]) -> list[dict[str, object]]:
        groups: dict[str, list[ScheduleAnalyticsRow]] = defaultdict(list)
        for row in rows:
            if row.schedule.status != ScheduleStatus.FAILED:
                continue
            reason = (row.schedule.failure_reason or "Unspecified publishing failure").strip()
            groups[reason].append(row)
        items = []
        for reason, group in groups.items():
            items.append(
                {
                    "reason": reason,
                    "count": len(group),
                    "platforms": sorted(
                        {row.schedule.platform for row in group},
                        key=lambda platform: platform.value,
                    ),
                    "latest_at": max(row.schedule.updated_at for row in group),
                }
            )
        return sorted(items, key=lambda item: (-int(item["count"]), str(item["reason"])))

    def best_times(self, rows: list[ScheduleAnalyticsRow]) -> list[dict[str, object]]:
        groups: dict[tuple[int, int], list[ScheduleAnalyticsRow]] = defaultdict(list)
        for row in rows:
            scheduled_for = row.schedule.scheduled_for
            groups[(scheduled_for.weekday(), scheduled_for.hour)].append(row)
        items = []
        for (weekday, hour), group in groups.items():
            counts = Counter(row.schedule.status for row in group)
            outcome_count = (
                counts[ScheduleStatus.PUBLISHED]
                + counts[ScheduleStatus.FAILED]
                + counts[ScheduleStatus.CANCELLED]
            )
            items.append(
                {
                    "day_of_week": _weekday_name(weekday),
                    "hour": hour,
                    "scheduled_count": len(group),
                    "published_count": counts[ScheduleStatus.PUBLISHED],
                    "failed_count": counts[ScheduleStatus.FAILED],
                    "success_rate": _rate(counts[ScheduleStatus.PUBLISHED], outcome_count),
                }
            )
        return sorted(
            items,
            key=lambda item: (
                -float(item["success_rate"]),
                -int(item["scheduled_count"]),
                int(item["hour"]),
            ),
        )[:12]

    def caption_effectiveness(self, rows: list[ScheduleAnalyticsRow]) -> list[dict[str, object]]:
        buckets = {
            "short": {"label": "Short captions", "rows": []},
            "standard": {"label": "Standard captions", "rows": []},
            "long": {"label": "Long captions", "rows": []},
        }
        for row in rows:
            text = row.schedule.scheduled_caption_text or row.caption.caption_text or ""
            length = len(text)
            if length < 140:
                bucket = "short"
            elif length <= 280:
                bucket = "standard"
            else:
                bucket = "long"
            buckets[bucket]["rows"].append(row)
        items = []
        for bucket, data in buckets.items():
            group = data["rows"]
            counts = Counter(row.schedule.status for row in group)
            outcome_count = (
                counts[ScheduleStatus.PUBLISHED]
                + counts[ScheduleStatus.FAILED]
                + counts[ScheduleStatus.CANCELLED]
            )
            generation_total = sum(row.caption.generation_count for row in group)
            items.append(
                {
                    "bucket": bucket,
                    "label": str(data["label"]),
                    "scheduled_count": len(group),
                    "published_count": counts[ScheduleStatus.PUBLISHED],
                    "failed_count": counts[ScheduleStatus.FAILED],
                    "success_rate": _rate(counts[ScheduleStatus.PUBLISHED], outcome_count),
                    "average_generation_count": _average(generation_total, len(group)),
                }
            )
        return items

    def trends(self, rows: list[ScheduleAnalyticsRow]) -> list[dict[str, object]]:
        groups: dict[str, list[ScheduleAnalyticsRow]] = defaultdict(list)
        for row in rows:
            scheduled_for = row.schedule.scheduled_for
            year, week, _ = scheduled_for.isocalendar()
            groups[f"{year}-W{week:02d}"].append(row)
        items = []
        for period, group in groups.items():
            counts = Counter(row.schedule.status for row in group)
            outcome_count = (
                counts[ScheduleStatus.PUBLISHED]
                + counts[ScheduleStatus.FAILED]
                + counts[ScheduleStatus.CANCELLED]
            )
            items.append(
                {
                    "period": period,
                    "scheduled_count": len(group),
                    "published_count": counts[ScheduleStatus.PUBLISHED],
                    "failed_count": counts[ScheduleStatus.FAILED],
                    "success_rate": _rate(counts[ScheduleStatus.PUBLISHED], outcome_count),
                }
            )
        return sorted(items, key=lambda item: str(item["period"]))

    def executive_insights(self, rows: list[ScheduleAnalyticsRow]) -> list[dict[str, str]]:
        metrics = self.success_metrics(rows, audit_event_count=0, webhook_event_count=0)
        failures = self.failure_metrics(rows)
        best_times = self.best_times(rows)
        channels = self.channel_performance(rows)
        insights = []
        total_rows = int(metrics["total_rows"])
        if total_rows == 0:
            return [
                {
                    "severity": "neutral",
                    "title": "No publishing data yet",
                    "summary": "Schedule and publish captioned rows to populate reporting.",
                }
            ]
        outcome_count = (
            int(metrics["published_count"])
            + int(metrics["failed_count"])
            + int(metrics["cancelled_count"])
        )
        if outcome_count == 0:
            return [
                {
                    "severity": "neutral",
                    "title": "Final outcomes pending",
                    "summary": (
                        f"{total_rows} publishing row(s) are scheduled, but none have final "
                        "published, failed, or cancelled outcomes yet."
                    ),
                }
            ]
        if float(metrics["failure_rate"]) >= 25:
            insights.append(
                {
                    "severity": "critical",
                    "title": "Publishing failure rate needs attention",
                    "summary": (
                        f"{metrics['failure_rate']}% of final publishing outcomes failed. "
                        "Review Buffer errors before expanding volume."
                    ),
                }
            )
        if failures:
            insights.append(
                {
                    "severity": "warning",
                    "title": "Top failure reason",
                    "summary": f"{failures[0]['reason']} affected {failures[0]['count']} row(s).",
                }
            )
        if best_times:
            best = best_times[0]
            insights.append(
                {
                    "severity": "positive",
                    "title": "Strongest publishing window",
                    "summary": (
                        f"{best['day_of_week']} at {best['hour']:02d}:00 has the best observed "
                        f"success rate at {best['success_rate']}%."
                    ),
                }
            )
        if channels:
            top_channel = channels[0]
            insights.append(
                {
                    "severity": "positive",
                    "title": "Top channel",
                    "summary": (
                        f"{top_channel['channel_name']} leads observed channel performance "
                        f"with {top_channel['success_rate']}% success."
                    ),
                }
            )
        return insights[:5]

    async def _rows(self, filters: AnalyticsFilters) -> list[ScheduleAnalyticsRow]:
        stmt = (
            select(
                EpisodeVideoPlatformSchedule,
                Series,
                Episode,
                EpisodeVideoPlatformCaption,
                BufferChannel,
            )
            .join(Series, EpisodeVideoPlatformSchedule.series_id == Series.id)
            .join(Episode, EpisodeVideoPlatformSchedule.episode_id == Episode.id)
            .join(
                EpisodeVideoPlatformCaption,
                EpisodeVideoPlatformSchedule.caption_id == EpisodeVideoPlatformCaption.id,
            )
            .outerjoin(
                BufferChannel,
                EpisodeVideoPlatformSchedule.buffer_channel_id == BufferChannel.id,
            )
            .order_by(EpisodeVideoPlatformSchedule.scheduled_for.desc())
        )
        stmt = self._apply_filters(stmt, filters)
        return [
            ScheduleAnalyticsRow(schedule, series, episode, caption, channel)
            for schedule, series, episode, caption, channel in (
                await self.session.execute(stmt)
            ).all()
        ]

    async def _filtered_schedule_ids(self, filters: AnalyticsFilters) -> list[UUID]:
        rows = await self.session.execute(
            self._filtered_schedule_statement(filters).with_only_columns(
                EpisodeVideoPlatformSchedule.id
            )
        )
        return list(rows.scalars().all())

    def _filtered_schedule_statement(self, filters: AnalyticsFilters) -> Select:
        stmt = select(EpisodeVideoPlatformSchedule)
        return self._apply_filters(stmt, filters)

    def _apply_filters(self, stmt: Select, filters: AnalyticsFilters) -> Select:
        if filters.date_from is not None:
            stmt = stmt.where(EpisodeVideoPlatformSchedule.scheduled_for >= filters.date_from)
        if filters.date_to is not None:
            stmt = stmt.where(EpisodeVideoPlatformSchedule.scheduled_for <= filters.date_to)
        if filters.platforms:
            stmt = stmt.where(EpisodeVideoPlatformSchedule.platform.in_(filters.platforms))
        if filters.video_kinds:
            stmt = stmt.where(EpisodeVideoPlatformSchedule.video_kind.in_(filters.video_kinds))
        return stmt

    async def _webhook_count(self, schedule_ids: list[UUID]) -> int:
        if not schedule_ids:
            return 0
        result = await self.session.execute(
            select(BufferWebhook).where(BufferWebhook.schedule_id.in_(schedule_ids))
        )
        return len(result.scalars().all())

    def _filter_payload(self, filters: AnalyticsFilters) -> dict[str, object]:
        return {
            "date_from": filters.date_from,
            "date_to": filters.date_to,
            "platforms": filters.platforms or [],
            "video_kinds": filters.video_kinds or [],
        }

    def _has_any_filter(self, filters: AnalyticsFilters) -> bool:
        return bool(
            filters.date_from or filters.date_to or filters.platforms or filters.video_kinds
        )


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _average(total: int | float, count: int) -> float:
    if count <= 0:
        return 0.0
    return round(total / count, 2)


def _weekday_name(index: int) -> str:
    return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][index]
