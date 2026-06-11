from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.types import (
    BufferAccountStatus,
    BufferPostStatus,
    EpisodeStatus,
    Platform,
    PublishingAuditStatus,
    ScheduleStatus,
    SeriesStatus,
)
from app.modules.captions.models import EpisodeVideoPlatformCaption
from app.modules.episodes.models import Episode
from app.modules.publishing_operations.schemas import PublishingBulkActionRequest
from app.modules.schedules.buffer_service import BufferPostResult, BufferPublishingService
from app.modules.schedules.models import (
    BufferAccount,
    BufferChannel,
    BufferChannelMapping,
    BufferWebhook,
    EpisodeVideoPlatformSchedule,
    PublishingAuditLog,
)
from app.modules.series.models import Series
from app.schemas.pagination import (
    OffsetParams,
    cursor_meta,
    decode_cursor,
    encode_cursor,
    offset_meta,
)


def _latest_schedule_ordering() -> tuple[object, object, object]:
    return (
        EpisodeVideoPlatformSchedule.scheduled_for.desc(),
        EpisodeVideoPlatformSchedule.created_at.desc(),
        EpisodeVideoPlatformSchedule.id.desc(),
    )


class PublishingOperationsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.buffer_service = BufferPublishingService(session)
        self._due_sync_ran = False

    async def workspace(self) -> dict[str, object]:
        await self._sync_due_schedules()
        rows = await self.queue_items(limit=100)
        failed = await self.queue_items(statuses=[ScheduleStatus.FAILED], limit=100)
        retry_center = await self.queue_items(
            statuses=[ScheduleStatus.FAILED, ScheduleStatus.CANCELLED],
            limit=100,
        )
        audit_logs = await self.audit_logs(limit=40)
        webhooks = await self.webhooks(limit=20)
        return {
            "analytics": await self.analytics(),
            "queue": rows,
            "failed": failed,
            "retry_center": retry_center,
            "channel_health": await self.channel_health(),
            "timeline": await self.timeline(limit=40),
            "activity_feed": await self.activity_feed(limit=40),
            "audit_logs": audit_logs,
            "webhooks": webhooks,
            "buffer_account": await self._active_account(),
        }

    async def analytics(self) -> dict[str, object]:
        await self._sync_due_schedules()
        schedules = await self._schedules()
        channels = await self._channels()
        account = await self._active_account()
        audit_logs = await self.audit_logs(limit=500)
        webhooks = await self.webhooks(limit=500)
        status_counts = Counter(schedule.status for schedule in schedules)
        unhealthy_channels = [
            channel for channel in channels if not channel.is_enabled or channel.is_queue_paused
        ]
        warnings = self._warnings(account, channels, unhealthy_channels, status_counts)
        return {
            "scheduled_count": status_counts[ScheduleStatus.SCHEDULED],
            "published_count": status_counts[ScheduleStatus.PUBLISHED],
            "failed_count": status_counts[ScheduleStatus.FAILED],
            "cancelled_count": status_counts[ScheduleStatus.CANCELLED],
            "retryable_count": status_counts[ScheduleStatus.FAILED]
            + status_counts[ScheduleStatus.CANCELLED],
            "active_channel_count": sum(channel.is_enabled for channel in channels),
            "unhealthy_channel_count": len(unhealthy_channels),
            "audit_event_count": len(audit_logs),
            "webhook_event_count": len(webhooks),
            "buffer_account_status": account.status if account else None,
            "warnings": warnings,
        }

    async def queue_items(
        self,
        *,
        statuses: list[ScheduleStatus] | None = None,
        platforms: list[Platform] | None = None,
        query: str | None = None,
        limit: int = 100,
        page: int = 1,
        page_size: int | None = None,
    ) -> dict[str, object]:
        await self._sync_due_schedules()
        effective_page_size = page_size or limit
        schedule_rows = await self._schedule_rows(
            statuses=statuses,
            platforms=platforms,
            query=query,
            limit=effective_page_size,
            page=page,
        )
        total_count = await self._schedule_count(
            statuses=statuses,
            platforms=platforms,
            query=query,
        )
        schedule_ids = [row["schedule"].id for row in schedule_rows]
        latest_audits = await self._latest_audits_by_schedule(schedule_ids)
        items = [
            self._queue_item(row, latest_audits.get(row["schedule"].id)) for row in schedule_rows
        ]
        return {
            "items": items,
            **offset_meta(total=total_count, page=page, page_size=effective_page_size),
            "total_count": total_count,
            "filters": {
                "statuses": [item.value for item in statuses] if statuses else [],
                "platforms": [item.value for item in platforms] if platforms else [],
                "query": query or "",
                "limit": effective_page_size,
            },
        }

    async def audit_logs(self, *, limit: int = 100) -> list[PublishingAuditLog]:
        result = await self.session.execute(
            select(PublishingAuditLog).order_by(PublishingAuditLog.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def audit_logs_page(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
    ) -> dict[str, object]:
        statement = select(PublishingAuditLog)
        if cursor:
            token = decode_cursor(cursor)
            statement = statement.where(
                or_(
                    PublishingAuditLog.created_at < token.created_at,
                    and_(
                        PublishingAuditLog.created_at == token.created_at,
                        PublishingAuditLog.id < token.id,
                    ),
                )
            )
        result = await self.session.execute(
            statement.order_by(
                PublishingAuditLog.created_at.desc(),
                PublishingAuditLog.id.desc(),
            ).limit(limit + 1)
        )
        audits = list(result.scalars().all())
        has_next = len(audits) > limit
        items = audits[:limit]
        next_cursor = (
            encode_cursor(items[-1].created_at, items[-1].id) if has_next and items else None
        )
        return {
            "items": items,
            **cursor_meta(page_size=limit, has_next=has_next, next_cursor=next_cursor),
        }

    async def webhooks(self, *, limit: int = 100) -> list[BufferWebhook]:
        result = await self.session.execute(
            select(BufferWebhook).order_by(BufferWebhook.received_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def channel_health(self) -> list[dict[str, object]]:
        channels = await self._channels()
        mappings = await self._mappings()
        schedules = await self._schedules()
        platforms_by_channel: dict[UUID, list[Platform]] = {}
        for mapping in mappings:
            platforms_by_channel.setdefault(mapping.buffer_channel_id, []).append(mapping.platform)
        status_counts: dict[UUID, Counter[ScheduleStatus]] = {}
        for schedule in schedules:
            if schedule.buffer_channel_id is None:
                continue
            status_counts.setdefault(schedule.buffer_channel_id, Counter())[schedule.status] += 1

        cards = []
        for channel in channels:
            counts = status_counts.get(channel.id, Counter())
            warnings = []
            if not channel.is_enabled:
                warnings.append("Channel is disabled.")
            if channel.is_queue_paused:
                warnings.append("Channel queue is paused.")
            if not platforms_by_channel.get(channel.id):
                warnings.append("Channel is not mapped to any platform.")
            health_status = "healthy" if not warnings else "degraded"
            if not channel.is_enabled:
                health_status = "broken"
            cards.append(
                {
                    "channel": channel,
                    "mapped_platforms": sorted(
                        platforms_by_channel.get(channel.id, []),
                        key=lambda item: item.value,
                    ),
                    "scheduled_count": counts[ScheduleStatus.SCHEDULED],
                    "published_count": counts[ScheduleStatus.PUBLISHED],
                    "failed_count": counts[ScheduleStatus.FAILED],
                    "health_status": health_status,
                    "warnings": warnings,
                }
            )
        return cards

    async def timeline(self, *, limit: int = 50) -> list[dict[str, object]]:
        audits = await self.audit_logs(limit=limit)
        schedule_map = await self._schedules_by_id(
            [audit.schedule_id for audit in audits if audit.schedule_id is not None]
        )
        events = []
        for audit in audits:
            schedule = schedule_map.get(audit.schedule_id) if audit.schedule_id else None
            events.append(
                {
                    "id": f"audit:{audit.id}",
                    "event_type": audit.action,
                    "title": audit.action.replace(".", " ").title(),
                    "status": audit.status.value,
                    "description": audit.error_message or "Publishing action recorded.",
                    "occurred_at": audit.created_at,
                    "schedule_id": audit.schedule_id,
                    "series_id": schedule.series_id if schedule else None,
                    "platform": schedule.platform if schedule else None,
                }
            )
        return events

    async def timeline_page(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, object]:
        audit_page = await self.audit_logs_page(limit=limit, cursor=cursor)
        audits = audit_page["items"]
        schedule_map = await self._schedules_by_id(
            [audit.schedule_id for audit in audits if audit.schedule_id is not None]
        )
        events = []
        for audit in audits:
            schedule = schedule_map.get(audit.schedule_id) if audit.schedule_id else None
            events.append(
                {
                    "id": f"audit:{audit.id}",
                    "event_type": audit.action,
                    "title": audit.action.replace(".", " ").title(),
                    "status": audit.status.value,
                    "description": audit.error_message or "Publishing action recorded.",
                    "occurred_at": audit.created_at,
                    "schedule_id": audit.schedule_id,
                    "series_id": schedule.series_id if schedule else None,
                    "platform": schedule.platform if schedule else None,
                }
            )
        return {**audit_page, "items": events}

    async def activity_feed(self, *, limit: int = 50) -> list[dict[str, object]]:
        audits = await self.audit_logs(limit=limit)
        webhooks = await self.webhooks(limit=limit)
        audit_schedule_ids = [audit.schedule_id for audit in audits]
        webhook_schedule_ids = [hook.schedule_id for hook in webhooks]
        schedule_ids = [
            item for item in [*audit_schedule_ids, *webhook_schedule_ids] if item is not None
        ]
        schedule_map = await self._schedules_by_id(schedule_ids)
        events = []
        for audit in audits:
            schedule = schedule_map.get(audit.schedule_id) if audit.schedule_id else None
            events.append(
                {
                    "id": f"audit:{audit.id}",
                    "event_type": audit.action,
                    "title": audit.action.replace(".", " ").title(),
                    "status": audit.status.value,
                    "description": audit.error_message or "Publishing action recorded.",
                    "occurred_at": audit.created_at,
                    "schedule_id": audit.schedule_id,
                    "series_id": schedule.series_id if schedule else None,
                    "platform": schedule.platform if schedule else None,
                    "source": "audit",
                }
            )
        for webhook in webhooks:
            schedule = schedule_map.get(webhook.schedule_id) if webhook.schedule_id else None
            events.append(
                {
                    "id": f"webhook:{webhook.id}",
                    "event_type": webhook.event_type,
                    "title": webhook.event_type.replace(".", " ").title(),
                    "status": webhook.status.value,
                    "description": f"Webhook event for {webhook.buffer_post_id or 'unknown post'}.",
                    "occurred_at": webhook.received_at,
                    "schedule_id": webhook.schedule_id,
                    "series_id": schedule.series_id if schedule else None,
                    "platform": schedule.platform if schedule else None,
                    "source": "webhook",
                }
            )
        return sorted(events, key=lambda item: item["occurred_at"], reverse=True)[:limit]

    async def retry_bulk(self, payload: PublishingBulkActionRequest) -> dict[str, object]:
        results = []
        now = datetime.now(UTC)
        for schedule_id in payload.schedule_ids:
            schedule = await self.session.get(EpisodeVideoPlatformSchedule, schedule_id)
            if schedule is None:
                results.append(self._bulk_result(schedule_id, False, "Schedule row not found."))
                continue
            if schedule.status not in {ScheduleStatus.FAILED, ScheduleStatus.CANCELLED}:
                results.append(
                    self._bulk_result(
                        schedule_id,
                        False,
                        "Only failed or cancelled posts can be retried.",
                        schedule.status,
                    )
                )
                continue
            caption = await self.session.get(EpisodeVideoPlatformCaption, schedule.caption_id)
            if caption is None or not caption.caption_text:
                results.append(
                    self._bulk_result(
                        schedule_id,
                        False,
                        "Caption text is missing; retry blocked.",
                        schedule.status,
                    )
                )
                continue

            scheduled_for = schedule.scheduled_for
            if scheduled_for <= now:
                scheduled_for = now + timedelta(minutes=5)
            text = schedule.scheduled_caption_text or caption.caption_text
            idempotency_key = self.buffer_service.idempotency_key(caption, scheduled_for, text)
            schedule.retry_count += 1
            schedule.scheduled_for = scheduled_for
            schedule.scheduled_caption_text = text
            schedule.idempotency_key = idempotency_key
            post_result, account, channel = await self.buffer_service.create_post(
                caption,
                scheduled_for,
                text,
                idempotency_key=idempotency_key,
            )
            schedule.buffer_account_id = account.id
            schedule.buffer_channel_id = channel.id
            self.buffer_service.apply_result(schedule, post_result, scheduled_for)
            self._audit_action(
                schedule,
                "publishing.bulk.retry",
                PublishingAuditStatus.SUCCEEDED
                if post_result.status != BufferPostStatus.FAILED
                else PublishingAuditStatus.FAILED,
                error_message=post_result.failure_reason,
            )
            results.append(
                self._bulk_result(
                    schedule_id,
                    schedule.status != ScheduleStatus.FAILED,
                    "Retry queued."
                    if schedule.status != ScheduleStatus.FAILED
                    else schedule.failure_reason,
                    schedule.status,
                )
            )

        await self.session.commit()
        return await self._bulk_response("retry", payload, results)

    async def sync_bulk(self, payload: PublishingBulkActionRequest) -> dict[str, object]:
        results = []
        now = datetime.now(UTC)
        for schedule_id in payload.schedule_ids:
            schedule = await self.session.get(EpisodeVideoPlatformSchedule, schedule_id)
            if schedule is None:
                results.append(self._bulk_result(schedule_id, False, "Schedule row not found."))
                continue
            if schedule.status in {ScheduleStatus.CANCELLED, ScheduleStatus.PUBLISHED}:
                results.append(
                    self._bulk_result(
                        schedule_id,
                        False,
                        "Cancelled or published rows do not need status sync.",
                        schedule.status,
                    )
                )
                continue
            post_result = await self.buffer_service.sync_post(schedule, now)
            self.buffer_service.apply_result(schedule, post_result, schedule.scheduled_for)
            self._audit_action(
                schedule,
                "publishing.bulk.sync",
                PublishingAuditStatus.SUCCEEDED
                if post_result.status != BufferPostStatus.FAILED
                else PublishingAuditStatus.FAILED,
                error_message=post_result.failure_reason,
            )
            results.append(self._bulk_result(schedule_id, True, "Status synced.", schedule.status))
        await self.session.commit()
        return await self._bulk_response("sync", payload, results)

    async def stop_bulk(self, payload: PublishingBulkActionRequest) -> dict[str, object]:
        results = []
        affected_series_ids: set[UUID] = set()
        for schedule_id in payload.schedule_ids:
            schedule = await self.session.get(EpisodeVideoPlatformSchedule, schedule_id)
            if schedule is None:
                results.append(self._bulk_result(schedule_id, False, "Schedule row not found."))
                continue
            if schedule.status == ScheduleStatus.PUBLISHED:
                results.append(
                    self._bulk_result(
                        schedule_id,
                        False,
                        "Published posts cannot be stopped from the Buffer queue.",
                        schedule.status,
                    )
                )
                continue

            if schedule.buffer_post_id:
                post_result = await self.buffer_service.cancel_post(schedule)
                if post_result.status == BufferPostStatus.FAILED:
                    self.buffer_service.apply_result(
                        schedule,
                        post_result,
                        schedule.scheduled_for,
                    )
                    self._audit_action(
                        schedule,
                        "publishing.bulk.stop",
                        PublishingAuditStatus.FAILED,
                        error_message=post_result.failure_reason,
                    )
                    results.append(
                        self._bulk_result(
                            schedule_id,
                            False,
                            post_result.failure_reason or "Buffer post could not be stopped.",
                            schedule.status,
                        )
                    )
                    continue

            affected_series_ids.add(schedule.series_id)
            schedule.status = ScheduleStatus.CANCELLED
            schedule.buffer_status = BufferPostStatus.CANCELLED
            schedule.failure_reason = None
            schedule.next_retry_at = None
            schedule.cancelled_at = datetime.now(UTC)
            self._audit_action(
                schedule,
                "publishing.bulk.stop",
                PublishingAuditStatus.SUCCEEDED,
            )
            await self.session.delete(schedule)
            results.append(
                self._bulk_result(
                    schedule_id,
                    True,
                    "Publishing stopped and Buffer queue item removed.",
                    None,
                )
            )

        await self.session.flush()
        for series_id in affected_series_ids:
            await self._refresh_series_publish_state(series_id)
        await self.session.commit()
        return await self._bulk_response("stop", payload, results)

    async def _sync_due_schedules(self) -> None:
        if self._due_sync_ran:
            return
        self._due_sync_ran = True
        now = datetime.now(UTC)
        schedules = await self._due_schedules(now)
        development_published_schedules = await self._development_published_schedules()
        if not schedules and not development_published_schedules:
            return

        affected_series_ids: set[UUID] = set()
        for schedule in schedules:
            result = await self.buffer_service.sync_post(schedule, now)
            self.buffer_service.apply_result(schedule, result, schedule.scheduled_for)
            affected_series_ids.add(schedule.series_id)
        for schedule in development_published_schedules:
            failure_reason = (
                "This post was marked as published by the development Buffer connector, but "
                "development mode does not publish to social channels. Configure Buffer OAuth, "
                "connect a real Buffer account, then reschedule this post."
            )
            result = BufferPostResult(
                post_id=schedule.buffer_post_id,
                status=BufferPostStatus.FAILED,
                failure_reason=failure_reason,
                raw_response={"development_published_reconciled": True},
            )
            self.buffer_service.apply_result(schedule, result, schedule.scheduled_for)
            self._audit_action(
                schedule,
                "publishing.development.reconcile",
                PublishingAuditStatus.FAILED,
                error_message=failure_reason,
            )
            affected_series_ids.add(schedule.series_id)

        await self.session.flush()
        for series_id in affected_series_ids:
            await self._refresh_series_publish_state(series_id)
        await self.session.commit()

    async def _due_schedules(self, now: datetime) -> list[EpisodeVideoPlatformSchedule]:
        result = await self.session.execute(
            select(EpisodeVideoPlatformSchedule)
            .where(
                EpisodeVideoPlatformSchedule.status == ScheduleStatus.SCHEDULED,
                EpisodeVideoPlatformSchedule.scheduled_for <= now,
                or_(
                    EpisodeVideoPlatformSchedule.last_synced_at.is_(None),
                    EpisodeVideoPlatformSchedule.last_synced_at
                    < EpisodeVideoPlatformSchedule.scheduled_for,
                    EpisodeVideoPlatformSchedule.last_synced_at
                    <= now - timedelta(seconds=45),
                ),
            )
            .order_by(EpisodeVideoPlatformSchedule.scheduled_for.asc())
            .limit(100)
        )
        return list(result.scalars().all())

    async def _development_published_schedules(self) -> list[EpisodeVideoPlatformSchedule]:
        result = await self.session.execute(
            select(EpisodeVideoPlatformSchedule)
            .join(
                BufferAccount,
                EpisodeVideoPlatformSchedule.buffer_account_id == BufferAccount.id,
            )
            .where(
                EpisodeVideoPlatformSchedule.status == ScheduleStatus.PUBLISHED,
                BufferAccount.access_token_secret.like("dev-buffer%"),
            )
            .order_by(EpisodeVideoPlatformSchedule.scheduled_for.asc())
            .limit(100)
        )
        return list(result.scalars().all())

    async def _bulk_response(
        self,
        action: str,
        payload: PublishingBulkActionRequest,
        results: list[dict[str, object]],
    ) -> dict[str, object]:
        return {
            "action": action,
            "requested_count": len(payload.schedule_ids),
            "succeeded_count": sum(bool(item["success"]) for item in results),
            "failed_count": sum(not bool(item["success"]) for item in results),
            "results": results,
            "workspace": await self.workspace(),
        }

    async def _schedule_rows(
        self,
        *,
        statuses: list[ScheduleStatus] | None = None,
        platforms: list[Platform] | None = None,
        query: str | None = None,
        limit: int = 100,
        page: int = 1,
    ) -> list[dict[str, object]]:
        pagination = OffsetParams(page=page, page_size=limit)
        statement = (
            select(EpisodeVideoPlatformSchedule, Series, Episode, BufferChannel)
            .join(Series, EpisodeVideoPlatformSchedule.series_id == Series.id)
            .join(Episode, EpisodeVideoPlatformSchedule.episode_id == Episode.id)
            .outerjoin(
                BufferChannel,
                EpisodeVideoPlatformSchedule.buffer_channel_id == BufferChannel.id,
            )
        )
        if statuses:
            statement = statement.where(EpisodeVideoPlatformSchedule.status.in_(statuses))
        if platforms:
            statement = statement.where(EpisodeVideoPlatformSchedule.platform.in_(platforms))
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(
                    Series.name.ilike(pattern),
                    Episode.title.ilike(pattern),
                    EpisodeVideoPlatformSchedule.scheduled_caption_text.ilike(pattern),
                    EpisodeVideoPlatformSchedule.buffer_post_id.ilike(pattern),
                )
            )
        statement = (
            statement.order_by(*_latest_schedule_ordering())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        result = await self.session.execute(statement)
        return [
            {
                "schedule": schedule,
                "series": series,
                "episode": episode,
                "channel": channel,
            }
            for schedule, series, episode, channel in result.all()
        ]

    async def _schedule_count(
        self,
        *,
        statuses: list[ScheduleStatus] | None = None,
        platforms: list[Platform] | None = None,
        query: str | None = None,
    ) -> int:
        statement = (
            select(func.count(EpisodeVideoPlatformSchedule.id))
            .join(Series, EpisodeVideoPlatformSchedule.series_id == Series.id)
            .join(Episode, EpisodeVideoPlatformSchedule.episode_id == Episode.id)
        )
        if statuses:
            statement = statement.where(EpisodeVideoPlatformSchedule.status.in_(statuses))
        if platforms:
            statement = statement.where(EpisodeVideoPlatformSchedule.platform.in_(platforms))
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(
                    Series.name.ilike(pattern),
                    Episode.title.ilike(pattern),
                    EpisodeVideoPlatformSchedule.scheduled_caption_text.ilike(pattern),
                    EpisodeVideoPlatformSchedule.buffer_post_id.ilike(pattern),
                )
            )
        return int((await self.session.execute(statement)).scalar_one() or 0)

    async def _latest_audits_by_schedule(
        self,
        schedule_ids: list[UUID],
    ) -> dict[UUID, PublishingAuditLog]:
        if not schedule_ids:
            return {}
        result = await self.session.execute(
            select(PublishingAuditLog)
            .where(PublishingAuditLog.schedule_id.in_(schedule_ids))
            .order_by(PublishingAuditLog.created_at.desc())
        )
        audits: dict[UUID, PublishingAuditLog] = {}
        for audit in result.scalars().all():
            if audit.schedule_id is not None and audit.schedule_id not in audits:
                audits[audit.schedule_id] = audit
        return audits

    async def _schedules(self) -> list[EpisodeVideoPlatformSchedule]:
        result = await self.session.execute(select(EpisodeVideoPlatformSchedule))
        return list(result.scalars().all())

    async def _schedules_by_id(
        self,
        schedule_ids: list[UUID | None],
    ) -> dict[UUID, EpisodeVideoPlatformSchedule]:
        ids = [schedule_id for schedule_id in schedule_ids if schedule_id is not None]
        if not ids:
            return {}
        result = await self.session.execute(
            select(EpisodeVideoPlatformSchedule).where(EpisodeVideoPlatformSchedule.id.in_(ids))
        )
        return {schedule.id: schedule for schedule in result.scalars().all()}

    async def _channels(self) -> list[BufferChannel]:
        result = await self.session.execute(
            select(BufferChannel).order_by(BufferChannel.service.asc())
        )
        return list(result.scalars().all())

    async def _mappings(self) -> list[BufferChannelMapping]:
        result = await self.session.execute(select(BufferChannelMapping))
        return list(result.scalars().all())

    async def _active_account(self) -> BufferAccount | None:
        result = await self.session.execute(
            select(BufferAccount)
            .where(BufferAccount.status == BufferAccountStatus.CONNECTED)
            .order_by(BufferAccount.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _refresh_series_publish_state(self, series_id: UUID) -> None:
        result = await self.session.execute(
            select(Episode)
            .where(Episode.series_id == series_id)
            .order_by(Episode.episode_number.asc())
        )
        episodes = list(result.scalars().all())
        schedules_result = await self.session.execute(
            select(EpisodeVideoPlatformSchedule).where(
                EpisodeVideoPlatformSchedule.series_id == series_id
            )
        )
        schedules = list(schedules_result.scalars().all())
        schedules_by_episode: dict[UUID, list[EpisodeVideoPlatformSchedule]] = {}
        for schedule in schedules:
            schedules_by_episode.setdefault(schedule.episode_id, []).append(schedule)

        for episode in episodes:
            episode_schedules = schedules_by_episode.get(episode.id, [])
            if any(schedule.status == ScheduleStatus.PUBLISHED for schedule in episode_schedules):
                if all(
                    schedule.status == ScheduleStatus.PUBLISHED for schedule in episode_schedules
                ):
                    episode.status = EpisodeStatus.PUBLISHED
                else:
                    episode.status = EpisodeStatus.PARTIALLY_PUBLISHED
            elif any(schedule.status == ScheduleStatus.SCHEDULED for schedule in episode_schedules):
                episode.status = EpisodeStatus.SCHEDULED
            elif episode.status in {
                EpisodeStatus.SCHEDULED,
                EpisodeStatus.PARTIALLY_PUBLISHED,
                EpisodeStatus.PUBLISHED,
            }:
                episode.status = EpisodeStatus.CAPTIONING

        series = await self.session.get(Series, series_id)
        if series is None:
            return
        if any(schedule.status == ScheduleStatus.PUBLISHED for schedule in schedules):
            series.status = SeriesStatus.PARTIALLY_PUBLISHED
        elif any(schedule.status == ScheduleStatus.SCHEDULED for schedule in schedules) or (
            series.status in {SeriesStatus.PARTIALLY_PUBLISHED, SeriesStatus.COMPLETE}
        ):
            series.status = SeriesStatus.IN_PRODUCTION

    def _queue_item(
        self,
        row: dict[str, object],
        latest_audit: PublishingAuditLog | None,
    ) -> dict[str, object]:
        schedule = row["schedule"]
        series = row["series"]
        episode = row["episode"]
        assert isinstance(schedule, EpisodeVideoPlatformSchedule)
        assert isinstance(series, Series)
        assert isinstance(episode, Episode)
        return {
            "id": schedule.id,
            "series_id": schedule.series_id,
            "series_name": series.name,
            "episode_id": schedule.episode_id,
            "episode_number": episode.episode_number,
            "episode_title": episode.title,
            "caption_id": schedule.caption_id,
            "video_kind": schedule.video_kind,
            "video_key": schedule.video_key,
            "platform": schedule.platform,
            "status": schedule.status,
            "buffer_status": schedule.buffer_status,
            "buffer_post_id": schedule.buffer_post_id,
            "scheduled_for": schedule.scheduled_for,
            "scheduled_caption_text": schedule.scheduled_caption_text,
            "failure_reason": schedule.failure_reason,
            "live_url": schedule.live_url,
            "retry_count": schedule.retry_count,
            "next_retry_at": schedule.next_retry_at,
            "last_synced_at": schedule.last_synced_at,
            "rate_limit_reset_at": schedule.rate_limit_reset_at,
            "channel": row["channel"],
            "latest_audit": latest_audit,
            "created_at": schedule.created_at,
            "updated_at": schedule.updated_at,
        }

    def _warnings(
        self,
        account: BufferAccount | None,
        channels: list[BufferChannel],
        unhealthy_channels: list[BufferChannel],
        status_counts: Counter[ScheduleStatus],
    ) -> list[str]:
        warnings = []
        if account is None:
            warnings.append("Buffer is required and is not connected.")
        elif self.buffer_service._is_development_account(account):
            warnings.append(
                "Buffer is connected in development mode. Queued posts are simulated and will "
                "not publish to social channels until real Buffer OAuth credentials are "
                "configured and connected."
            )
        if not channels:
            warnings.append("No Buffer channels have been synced.")
        if unhealthy_channels:
            warnings.append(f"{len(unhealthy_channels)} Buffer channel(s) need attention.")
        if status_counts[ScheduleStatus.FAILED]:
            warnings.append(f"{status_counts[ScheduleStatus.FAILED]} failed post(s) need recovery.")
        return warnings

    def _audit_action(
        self,
        schedule: EpisodeVideoPlatformSchedule,
        action: str,
        audit_status: PublishingAuditStatus,
        *,
        error_message: str | None = None,
    ) -> None:
        self.session.add(
            PublishingAuditLog(
                schedule_id=schedule.id,
                buffer_account_id=schedule.buffer_account_id,
                buffer_channel_id=schedule.buffer_channel_id,
                action=action,
                status=audit_status,
                idempotency_key=schedule.idempotency_key,
                request_payload={"schedule_id": str(schedule.id)},
                response_payload={
                    "schedule_status": schedule.status.value,
                    "buffer_status": schedule.buffer_status.value,
                },
                error_message=error_message,
            )
        )

    def _bulk_result(
        self,
        schedule_id: UUID,
        success: bool,
        message: str | None,
        schedule_status: ScheduleStatus | None = None,
    ) -> dict[str, object]:
        return {
            "schedule_id": schedule_id,
            "success": success,
            "message": message or "Publishing operation completed.",
            "status": schedule_status,
        }

    def _ensure_not_empty(self, payload: PublishingBulkActionRequest) -> None:
        if not payload.schedule_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Select at least one publishing row.",
            )
