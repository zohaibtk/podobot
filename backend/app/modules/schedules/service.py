from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.types import (
    CaptionStatus,
    BufferPostStatus,
    CaptionVideoKind,
    EpisodeStatus,
    ScheduleStatus,
    SeriesStatus,
)
from app.modules.captions.models import EpisodeVideoPlatformCaption
from app.modules.episodes.models import Episode
from app.modules.recordings.models import ClipSuggestion, EpisodeVideo
from app.modules.schedules.buffer_service import BufferPostResult, BufferPublishingService
from app.modules.schedules.models import EpisodeVideoPlatformSchedule
from app.modules.schedules.schemas import (
    BulkScheduleRequest,
    ScheduleCreateRequest,
    ScheduleRescheduleRequest,
    ScheduleUpdateRequest,
)
from app.modules.series.models import Series
from app.modules.series.service import SeriesService


class ScheduleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.series_service = SeriesService(session)
        self.buffer_service = BufferPublishingService(session)

    async def get_workspace(self, series_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_scheduling_unlocked(series)
        await self._sync_due_schedules(series_id)
        return await self._workspace_response(series_id)

    async def create_schedule(
        self,
        series_id: UUID,
        payload: ScheduleCreateRequest,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_scheduling_unlocked(series)
        caption = await self._get_caption(series_id, payload.caption_id)
        await self._assert_schedule_ready(caption)
        scheduled_for = self._ensure_aware(payload.scheduled_for)
        existing = await self._schedule_for_caption(caption.id)
        if existing is not None and existing.status not in {
            ScheduleStatus.FAILED,
            ScheduleStatus.CANCELLED,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This platform row is already scheduled or published",
            )

        await self._upsert_schedule(caption, scheduled_for, existing)
        await self._refresh_episode_and_series_status(series_id)
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def bulk_schedule(
        self,
        series_id: UUID,
        payload: BulkScheduleRequest,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_scheduling_unlocked(series)
        captions = await self._candidate_captions(series_id, payload.caption_ids)
        scheduled_count = 0
        failed_count = 0
        skipped_count = 0
        requested_count = len(captions)
        scheduled_for = self._ensure_aware(payload.scheduled_for)

        for index, caption in enumerate(captions):
            if not await self._schedule_ready(caption):
                skipped_count += 1
                continue
            existing = await self._schedule_for_caption(caption.id)
            if existing is not None and existing.status not in {
                ScheduleStatus.FAILED,
                ScheduleStatus.CANCELLED,
            }:
                skipped_count += 1
                continue
            schedule = await self._upsert_schedule(
                caption,
                scheduled_for + timedelta(minutes=index * payload.spacing_minutes),
                existing,
            )
            if schedule.status == ScheduleStatus.FAILED:
                failed_count += 1
            else:
                scheduled_count += 1

        await self._refresh_episode_and_series_status(series_id)
        await self.session.commit()
        return await self._workspace_response(
            series_id,
            bulk_result={
                "requested_count": requested_count,
                "scheduled_count": scheduled_count,
                "failed_count": failed_count,
                "skipped_count": skipped_count,
            },
        )

    async def update_schedule(
        self,
        series_id: UUID,
        schedule_id: UUID,
        payload: ScheduleUpdateRequest,
    ) -> dict[str, object]:
        schedule = await self._get_schedule(series_id, schedule_id)
        if schedule.status != ScheduleStatus.SCHEDULED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only scheduled Buffer posts can be edited",
            )

        if payload.scheduled_for is not None:
            schedule.scheduled_for = self._ensure_aware(payload.scheduled_for)
        if payload.scheduled_caption_text is not None:
            schedule.scheduled_caption_text = payload.scheduled_caption_text

        result = await self._update_buffer_post(schedule, schedule.scheduled_caption_text)
        self.buffer_service.apply_result(schedule, result, scheduled_for=schedule.scheduled_for)
        await self._refresh_episode_and_series_status(series_id)
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def reschedule(
        self,
        series_id: UUID,
        schedule_id: UUID,
        payload: ScheduleRescheduleRequest,
    ) -> dict[str, object]:
        schedule = await self._get_schedule(series_id, schedule_id)
        if schedule.status == ScheduleStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Published Buffer posts cannot be rescheduled",
        )
        caption = await self._get_caption(series_id, schedule.caption_id)
        await self._assert_schedule_ready(caption)
        schedule.retry_count += 1
        schedule.scheduled_for = self._ensure_aware(payload.scheduled_for)
        schedule.scheduled_caption_text = (
            payload.scheduled_caption_text or caption.caption_text or ""
        )
        schedule.idempotency_key = self.buffer_service.idempotency_key(
            caption,
            schedule.scheduled_for,
            schedule.scheduled_caption_text,
        )
        result, account, channel = await self.buffer_service.create_post(
            caption,
            schedule.scheduled_for,
            schedule.scheduled_caption_text,
            idempotency_key=schedule.idempotency_key,
        )
        schedule.buffer_account_id = account.id
        schedule.buffer_channel_id = channel.id
        self.buffer_service.apply_result(schedule, result, scheduled_for=schedule.scheduled_for)
        await self._refresh_episode_and_series_status(series_id)
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def cancel_schedule(self, series_id: UUID, schedule_id: UUID) -> dict[str, object]:
        schedule = await self._get_schedule(series_id, schedule_id)
        if schedule.status == ScheduleStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Published Buffer posts cannot be cancelled",
            )
        result = await self._cancel_buffer_post(schedule)
        if result.status == BufferPostStatus.FAILED:
            self.buffer_service.apply_result(schedule, result, scheduled_for=schedule.scheduled_for)
        else:
            schedule.status = ScheduleStatus.CANCELLED
            await self.session.delete(schedule)
        await self._refresh_episode_and_series_status(series_id)
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def sync_statuses(self, series_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_scheduling_unlocked(series)
        schedules = await self._schedules(series_id)
        now = datetime.now(UTC)
        for schedule in schedules:
            if schedule.status in {ScheduleStatus.CANCELLED, ScheduleStatus.PUBLISHED}:
                schedule.last_synced_at = now
                continue
            result = await self._sync_buffer_post(schedule, now)
            self.buffer_service.apply_result(schedule, result, scheduled_for=schedule.scheduled_for)
        await self._refresh_episode_and_series_status(series_id)
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def _upsert_schedule(
        self,
        caption: EpisodeVideoPlatformCaption,
        scheduled_for: datetime,
        existing: EpisodeVideoPlatformSchedule | None = None,
    ) -> EpisodeVideoPlatformSchedule:
        text = caption.caption_text or ""
        media_asset_id = await self._caption_media_asset_id(caption)
        idempotency_key = self.buffer_service.idempotency_key(caption, scheduled_for, text)
        result, account, channel = await self.buffer_service.create_post(
            caption,
            scheduled_for,
            text,
            idempotency_key=idempotency_key,
        )
        schedule = existing or EpisodeVideoPlatformSchedule(
            series_id=caption.series_id,
            episode_id=caption.episode_id,
            episode_video_id=caption.episode_video_id,
            media_asset_id=media_asset_id,
            caption_id=caption.id,
            clip_suggestion_id=caption.clip_suggestion_id,
            video_kind=caption.video_kind,
            video_key=caption.video_key,
            platform=caption.platform,
            scheduled_for=scheduled_for,
            scheduled_caption_text=text,
        )
        schedule.scheduled_for = scheduled_for
        schedule.scheduled_caption_text = text
        schedule.media_asset_id = media_asset_id
        schedule.clip_suggestion_id = caption.clip_suggestion_id
        schedule.video_kind = caption.video_kind
        schedule.video_key = caption.video_key
        schedule.platform = caption.platform
        schedule.buffer_account_id = account.id
        schedule.buffer_channel_id = channel.id
        schedule.idempotency_key = idempotency_key
        self.buffer_service.apply_result(schedule, result, scheduled_for=scheduled_for)
        if existing is None:
            self.session.add(schedule)
        await self.session.flush()
        return schedule

    async def _update_buffer_post(
        self,
        schedule: EpisodeVideoPlatformSchedule,
        text: str,
    ) -> BufferPostResult:
        return await self.buffer_service.update_post(schedule, text)

    async def _cancel_buffer_post(
        self,
        schedule: EpisodeVideoPlatformSchedule,
    ) -> BufferPostResult:
        return await self.buffer_service.cancel_post(schedule)

    async def _sync_buffer_post(
        self,
        schedule: EpisodeVideoPlatformSchedule,
        now: datetime,
    ) -> BufferPostResult:
        return await self.buffer_service.sync_post(schedule, now)

    async def _sync_due_schedules(self, series_id: UUID) -> None:
        schedules = await self._schedules(series_id)
        now = datetime.now(UTC)
        synced_any = False
        for schedule in schedules:
            if schedule.status != ScheduleStatus.SCHEDULED:
                continue
            if schedule.scheduled_for > now:
                continue
            if (
                schedule.last_synced_at is not None
                and schedule.last_synced_at >= schedule.scheduled_for
                and now - schedule.last_synced_at < timedelta(seconds=45)
            ):
                continue
            result = await self._sync_buffer_post(schedule, now)
            self.buffer_service.apply_result(schedule, result, scheduled_for=schedule.scheduled_for)
            synced_any = True

        if synced_any:
            await self._refresh_episode_and_series_status(series_id)
            await self.session.commit()

    async def _workspace_response(
        self,
        series_id: UUID,
        bulk_result: dict[str, int] | None = None,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        episodes = await self._episodes(series_id)
        captions = await self._captions_by_episode(series_id)
        schedule_list = await self._schedules(series_id)
        schedule_context = await self.buffer_service.schedule_context(schedule_list)
        schedules = {schedule.caption_id: schedule for schedule in schedule_list}
        clips = await self._clip_suggestions_by_episode(series_id)
        clip_lookup = {
            clip.id: clip
            for episode_clips in clips.values()
            for clip in episode_clips
        }

        episode_payloads = []
        all_rows = []
        for episode in episodes:
            episode_captions = captions.get(episode.id, [])
            rows = [
                self._row_payload(
                    caption,
                    schedules.get(caption.id),
                    schedule_context,
                    clip_lookup,
                )
                for caption in episode_captions
            ]
            all_rows.extend(rows)
            full_rows = [row for row in rows if row["video_kind"].value == "full_episode"]
            short_slots = []
            for clip in clips.get(episode.id, []):
                clip_rows = [row for row in rows if row["clip_suggestion_id"] == clip.id]
                if not clip_rows:
                    continue
                short_slots.append(
                    {
                        "clip_suggestion": clip,
                        "rows": clip_rows,
                        "scheduled_count": self._row_count(clip_rows, ScheduleStatus.SCHEDULED),
                        "published_count": self._row_count(clip_rows, ScheduleStatus.PUBLISHED),
                        "failed_count": self._row_count(clip_rows, ScheduleStatus.FAILED),
                    }
                )
            episode_payloads.append(
                {
                    "episode_id": episode.id,
                    "episode_number": episode.episode_number,
                    "episode_title": episode.title,
                    "episode_premise": episode.premise,
                    "episode_status": episode.status,
                    "full_episode_rows": full_rows,
                    "short_clip_slots": short_slots,
                    "eligible_count": sum(row["schedule_ready"] for row in rows),
                    "scheduled_count": self._row_count(rows, ScheduleStatus.SCHEDULED),
                    "published_count": self._row_count(rows, ScheduleStatus.PUBLISHED),
                    "failed_count": self._row_count(rows, ScheduleStatus.FAILED),
                    "locked_count": sum(not row["schedule_ready"] for row in rows),
                }
            )

        return {
            "series": series,
            "episodes": episode_payloads,
            "readiness": {
                "total_row_count": len(all_rows),
                "eligible_row_count": sum(row["schedule_ready"] for row in all_rows),
                "scheduled_row_count": self._row_count(all_rows, ScheduleStatus.SCHEDULED),
                "published_row_count": self._row_count(all_rows, ScheduleStatus.PUBLISHED),
                "failed_row_count": self._row_count(all_rows, ScheduleStatus.FAILED),
                "locked_row_count": sum(not row["schedule_ready"] for row in all_rows),
                "bulk_schedulable_count": sum(self._bulk_schedulable(row) for row in all_rows),
                "warnings": self._readiness_warnings(all_rows),
            },
            "buffer": await self.buffer_service.workspace(),
            "bulk_result": bulk_result,
        }

    def _row_payload(
        self,
        caption: EpisodeVideoPlatformCaption,
        schedule: EpisodeVideoPlatformSchedule | None,
        schedule_context: dict[str, dict[UUID, object]],
        clip_lookup: dict[UUID, ClipSuggestion],
    ) -> dict[str, object]:
        is_captioned = self._caption_ready(caption)
        media_ready, media_file_name = self._media_readiness(caption, clip_lookup)
        schedule_ready = is_captioned and media_ready
        has_terminal_schedule = schedule is not None and schedule.status in {
            ScheduleStatus.SCHEDULED,
            ScheduleStatus.PUBLISHED,
        }
        can_create_schedule = schedule_ready and not has_terminal_schedule and schedule is None
        can_reschedule = (
            schedule_ready
            and schedule is not None
            and schedule.status
            in {
                ScheduleStatus.SCHEDULED,
                ScheduleStatus.FAILED,
                ScheduleStatus.CANCELLED,
            }
        )
        return {
            "caption_id": caption.id,
            "series_id": caption.series_id,
            "episode_id": caption.episode_id,
            "episode_video_id": caption.episode_video_id,
            "clip_suggestion_id": caption.clip_suggestion_id,
            "video_kind": caption.video_kind,
            "video_key": caption.video_key,
            "platform": caption.platform,
            "caption_status": caption.status,
            "caption_text": caption.caption_text,
            "schedule": self.buffer_service.schedule_payload(schedule, schedule_context)
            if schedule is not None
            else None,
            "is_captioned": is_captioned,
            "media_ready": media_ready,
            "schedule_ready": schedule_ready,
            "media_file_name": media_file_name,
            "can_create_schedule": can_create_schedule,
            "can_reschedule": can_reschedule,
            "schedule_locked_reason": self._locked_reason(
                caption,
                schedule,
                is_captioned,
                media_ready,
            ),
        }

    def _locked_reason(
        self,
        caption: EpisodeVideoPlatformCaption,
        schedule: EpisodeVideoPlatformSchedule | None,
        is_captioned: bool,
        media_ready: bool,
    ) -> str | None:
        if not is_captioned:
            return "Only captioned rows can be scheduled."
        if not media_ready:
            return "Upload the suggested clip video in Recordings before scheduling."
        if schedule is None:
            return None
        if schedule.status == ScheduleStatus.PUBLISHED:
            return "Published rows are locked."
        if schedule.status == ScheduleStatus.SCHEDULED:
            return "Already scheduled in Buffer."
        if schedule.status == ScheduleStatus.FAILED:
            return schedule.failure_reason or "Buffer publishing failed; reschedule to recover."
        if schedule.status == ScheduleStatus.CANCELLED:
            return "Cancelled rows can be rescheduled."
        return None

    def _assert_scheduling_unlocked(self, series: Series) -> None:
        if series.scheduling_unlocked_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Generate at least one caption before scheduling",
            )

    async def _assert_schedule_ready(self, caption: EpisodeVideoPlatformCaption) -> None:
        if not self._caption_ready(caption):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only captioned rows can be scheduled",
            )
        if not await self._caption_media_ready(caption):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Upload the suggested clip video in Recordings before scheduling",
            )

    def _caption_ready(self, caption: EpisodeVideoPlatformCaption) -> bool:
        return caption.status == CaptionStatus.READY and bool(caption.caption_text)

    async def _schedule_ready(self, caption: EpisodeVideoPlatformCaption) -> bool:
        return self._caption_ready(caption) and await self._caption_media_ready(caption)

    async def _caption_media_ready(self, caption: EpisodeVideoPlatformCaption) -> bool:
        if caption.video_kind != CaptionVideoKind.SHORT_CLIP:
            return True
        if caption.clip_suggestion_id is None:
            return False
        clip = await self.session.get(ClipSuggestion, caption.clip_suggestion_id)
        return bool(clip and clip.clip_media_uploaded)

    async def _caption_media_asset_id(
        self,
        caption: EpisodeVideoPlatformCaption,
    ) -> UUID | None:
        if caption.video_kind == CaptionVideoKind.SHORT_CLIP:
            if caption.clip_suggestion_id is None:
                return None
            clip = await self.session.get(ClipSuggestion, caption.clip_suggestion_id)
            return clip.clip_media_asset_id if clip is not None else None

        video = await self.session.get(EpisodeVideo, caption.episode_video_id)
        return video.media_asset_id if video is not None else None

    def _media_readiness(
        self,
        caption: EpisodeVideoPlatformCaption,
        clip_lookup: dict[UUID, ClipSuggestion],
    ) -> tuple[bool, str | None]:
        if caption.video_kind != CaptionVideoKind.SHORT_CLIP:
            return True, None
        if caption.clip_suggestion_id is None:
            return False, None
        clip = clip_lookup.get(caption.clip_suggestion_id)
        if clip is None:
            return False, None
        return clip.clip_media_uploaded, clip.clip_file_name

    async def _get_caption(
        self,
        series_id: UUID,
        caption_id: UUID,
    ) -> EpisodeVideoPlatformCaption:
        caption = await self.session.get(EpisodeVideoPlatformCaption, caption_id)
        if caption is None or caption.series_id != series_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caption not found")
        return caption

    async def _get_schedule(
        self,
        series_id: UUID,
        schedule_id: UUID,
    ) -> EpisodeVideoPlatformSchedule:
        schedule = await self.session.get(EpisodeVideoPlatformSchedule, schedule_id)
        if schedule is None or schedule.series_id != series_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
        return schedule

    async def _schedule_for_caption(
        self,
        caption_id: UUID,
    ) -> EpisodeVideoPlatformSchedule | None:
        result = await self.session.execute(
            select(EpisodeVideoPlatformSchedule).where(
                EpisodeVideoPlatformSchedule.caption_id == caption_id
            )
        )
        return result.scalar_one_or_none()

    async def _episodes(self, series_id: UUID) -> list[Episode]:
        result = await self.session.execute(
            select(Episode)
            .where(Episode.series_id == series_id)
            .order_by(Episode.episode_number.asc())
        )
        return list(result.scalars().all())

    async def _captions_by_episode(
        self,
        series_id: UUID,
    ) -> dict[UUID, list[EpisodeVideoPlatformCaption]]:
        result = await self.session.execute(
            select(EpisodeVideoPlatformCaption)
            .where(EpisodeVideoPlatformCaption.series_id == series_id)
            .order_by(
                EpisodeVideoPlatformCaption.episode_id.asc(),
                EpisodeVideoPlatformCaption.video_kind.asc(),
                EpisodeVideoPlatformCaption.video_key.asc(),
                EpisodeVideoPlatformCaption.platform.asc(),
            )
        )
        grouped: dict[UUID, list[EpisodeVideoPlatformCaption]] = {}
        for caption in result.scalars().all():
            grouped.setdefault(caption.episode_id, []).append(caption)
        return grouped

    async def _candidate_captions(
        self,
        series_id: UUID,
        caption_ids: list[UUID] | None,
    ) -> list[EpisodeVideoPlatformCaption]:
        result = await self.session.execute(
            select(EpisodeVideoPlatformCaption)
            .where(EpisodeVideoPlatformCaption.series_id == series_id)
            .order_by(
                EpisodeVideoPlatformCaption.episode_id.asc(),
                EpisodeVideoPlatformCaption.video_kind.asc(),
                EpisodeVideoPlatformCaption.video_key.asc(),
                EpisodeVideoPlatformCaption.platform.asc(),
            )
        )
        captions = list(result.scalars().all())
        if caption_ids is None:
            return captions
        requested = set(caption_ids)
        return [caption for caption in captions if caption.id in requested]

    async def _schedules(self, series_id: UUID) -> list[EpisodeVideoPlatformSchedule]:
        result = await self.session.execute(
            select(EpisodeVideoPlatformSchedule)
            .where(EpisodeVideoPlatformSchedule.series_id == series_id)
            .order_by(EpisodeVideoPlatformSchedule.scheduled_for.asc())
        )
        return list(result.scalars().all())

    async def _clip_suggestions_by_episode(
        self,
        series_id: UUID,
    ) -> dict[UUID, list[ClipSuggestion]]:
        result = await self.session.execute(
            select(ClipSuggestion)
            .where(ClipSuggestion.series_id == series_id)
            .order_by(ClipSuggestion.episode_id.asc(), ClipSuggestion.slot_number.asc())
        )
        grouped: dict[UUID, list[ClipSuggestion]] = {}
        for suggestion in result.scalars().all():
            grouped.setdefault(suggestion.episode_id, []).append(suggestion)
        return grouped

    async def _refresh_episode_and_series_status(self, series_id: UUID) -> None:
        await self.session.flush()
        schedules = await self._schedules(series_id)
        schedules_by_episode: dict[UUID, list[EpisodeVideoPlatformSchedule]] = {}
        for schedule in schedules:
            schedules_by_episode.setdefault(schedule.episode_id, []).append(schedule)
        episodes = await self._episodes(series_id)
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

        series = await self.series_service.get_series(series_id)
        if any(schedule.status == ScheduleStatus.PUBLISHED for schedule in schedules):
            series.status = SeriesStatus.PARTIALLY_PUBLISHED
        elif any(schedule.status == ScheduleStatus.SCHEDULED for schedule in schedules):
            series.status = SeriesStatus.IN_PRODUCTION
        elif series.status in {SeriesStatus.PARTIALLY_PUBLISHED, SeriesStatus.COMPLETE}:
            series.status = SeriesStatus.IN_PRODUCTION

    def _row_count(self, rows: list[dict[str, object]], status: ScheduleStatus) -> int:
        return sum(self._row_schedule_status(row) == status for row in rows)

    def _readiness_warnings(self, rows: list[dict[str, object]]) -> list[str]:
        warnings = []
        if not rows:
            warnings.append("No caption platform rows are available for scheduling.")
        locked_count = sum(not row["is_captioned"] for row in rows)
        media_missing_count = sum(row["is_captioned"] and not row["media_ready"] for row in rows)
        failed_count = self._row_count(rows, ScheduleStatus.FAILED)
        unscheduled_count = sum(row["can_create_schedule"] for row in rows)
        if locked_count:
            warnings.append(f"{locked_count} uncaptioned row(s) remain locked.")
        if media_missing_count:
            warnings.append(
                f"{media_missing_count} short clip row(s) need uploaded clip media."
            )
        if unscheduled_count:
            warnings.append(f"{unscheduled_count} row(s) are ready to schedule.")
        if failed_count:
            warnings.append(f"{failed_count} failed Buffer post(s) can be rescheduled.")
        return warnings

    def _bulk_schedulable(self, row: dict[str, object]) -> bool:
        return bool(
            row["schedule_ready"]
            and (
                row["can_create_schedule"]
                or self._row_schedule_status(row)
                in {ScheduleStatus.FAILED, ScheduleStatus.CANCELLED}
            )
        )

    def _row_schedule_status(self, row: dict[str, object]) -> ScheduleStatus | None:
        schedule = row["schedule"]
        if schedule is None:
            return None
        if isinstance(schedule, dict):
            raw_status = schedule.get("status")
        else:
            raw_status = getattr(schedule, "status", None)
        if raw_status is None:
            return None
        if isinstance(raw_status, ScheduleStatus):
            return raw_status
        return ScheduleStatus(str(raw_status))

    def _ensure_aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
