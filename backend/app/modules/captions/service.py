import re
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.workflow import record_workflow_agent_run
from app.db.types import (
    CaptionStatus,
    CaptionVideoKind,
    EpisodeStatus,
    Platform,
    SeriesStage,
    SeriesStatus,
    TranscriptStatus,
    VideoStatus,
)
from app.modules.captions.models import EpisodeVideoPlatformCaption
from app.modules.captions.schemas import CaptionPlatformCreateRequest, CaptionUpdateRequest
from app.modules.episodes.models import Episode
from app.modules.recordings.models import ClipSuggestion, EpisodeVideo, Transcript
from app.modules.series.models import Series
from app.modules.series.service import SeriesService

FULL_EPISODE_PLATFORMS = (
    Platform.LINKEDIN,
    Platform.FACEBOOK,
    Platform.YOUTUBE,
)
SHORT_CLIP_PLATFORMS = (
    Platform.INSTAGRAM,
    Platform.YOUTUBE,
    Platform.TIKTOK,
    Platform.X,
    Platform.FACEBOOK,
    Platform.LINKEDIN,
)
CAPTION_TIMECODE_RANGE_RE = re.compile(
    r"\b(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d+)?\s*"
    r"(?:-->|[-–—]|to)\s*"
    r"(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d+)?\b",
    re.IGNORECASE,
)
CAPTION_SPACED_TIMECODE_RANGE_RE = re.compile(
    r"\b\d{1,2}\s+\d{2}(?:\s+\d{2})?\s+"
    r"\d{1,2}\s+\d{2}(?:\s+\d{2})?\b"
)
CAPTION_SINGLE_TIMECODE_RE = re.compile(
    r"\b(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d+)?\b"
)
CAPTION_CLIP_PREFIX_RE = re.compile(r"^\s*clip\s+\d+\s*[:\-]\s*", re.IGNORECASE)
CAPTION_META_PREFIX_RE = re.compile(
    r"^\s*transcript-backed moment(?:\s+with\s+clear\s+short-form\s+potential)?\s*[:\-]\s*",
    re.IGNORECASE,
)
CAPTION_SPEAKER_LABEL_RE = re.compile(r"^\s*(?:narrator|speaker\s*\d*)\s*[:\-]?\s*", re.IGNORECASE)


class CaptionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.series_service = SeriesService(session)

    async def get_workspace(self, series_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_captions_unlocked(series)
        episodes = await self._episodes(series_id)
        await self._ensure_full_episode_rows(series_id, episodes)
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def add_platform(
        self,
        series_id: UUID,
        episode_id: UUID,
        payload: CaptionPlatformCreateRequest,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_captions_unlocked(series)
        episode = await self._get_episode(series_id, episode_id)
        video = await self._video_for_episode(series_id, episode_id)
        await self._assert_episode_captionable(series_id, episode_id, video)
        self._assert_platform_allowed(payload.video_kind, payload.platform)

        clip_suggestion = None
        video_key = "full"
        if payload.video_kind == CaptionVideoKind.SHORT_CLIP:
            if payload.clip_suggestion_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="clip_suggestion_id is required for short clip captions",
                )
            clip_suggestion = await self._get_clip_suggestion(
                series_id,
                episode_id,
                payload.clip_suggestion_id,
            )
            video_key = self._clip_video_key(clip_suggestion.id)
        elif payload.clip_suggestion_id is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="clip_suggestion_id is only valid for short clip captions",
            )

        existing = await self._caption_for_key(
            episode_video_id=video.id,
            video_kind=payload.video_kind,
            video_key=video_key,
            platform=payload.platform,
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That platform is already configured for this video row",
            )

        self.session.add(
            EpisodeVideoPlatformCaption(
                series_id=series.id,
                episode_id=episode.id,
                episode_video_id=video.id,
                clip_suggestion_id=clip_suggestion.id if clip_suggestion else None,
                video_kind=payload.video_kind,
                video_key=video_key,
                platform=payload.platform,
            )
        )
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def generate_caption(self, series_id: UUID, caption_id: UUID) -> dict[str, object]:
        caption = await self._get_caption(series_id, caption_id)
        await self._assert_episode_captionable(
            caption.series_id,
            caption.episode_id,
            await self._video_by_id(caption.episode_video_id),
        )
        caption.caption_text = await self._generated_caption(caption, regenerated=False)
        caption.status = CaptionStatus.READY
        caption.generation_count += 1
        caption.generated_at = datetime.now(UTC)
        await self._mark_episode_captioning(caption.episode_id)
        await self._unlock_scheduling_if_ready(series_id)
        await record_workflow_agent_run(
            self.session,
            agent_key="caption",
            entity_type="series",
            entity_id=series_id,
            workflow_stage=SeriesStage.CAPTIONS.value,
            trigger="generation",
            input_payload={"caption_id": str(caption.id), "platform": caption.platform.value},
            output_payload={
                "summary": f"Generated {caption.platform.value} caption.",
                "needs_approval": True,
            },
        )
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def regenerate_caption(self, series_id: UUID, caption_id: UUID) -> dict[str, object]:
        caption = await self._get_caption(series_id, caption_id)
        await self._assert_episode_captionable(
            caption.series_id,
            caption.episode_id,
            await self._video_by_id(caption.episode_video_id),
        )
        caption.caption_text = await self._generated_caption(caption, regenerated=True)
        caption.status = CaptionStatus.READY
        caption.generation_count += 1
        caption.generated_at = datetime.now(UTC)
        await self._mark_episode_captioning(caption.episode_id)
        await self._unlock_scheduling_if_ready(series_id)
        await record_workflow_agent_run(
            self.session,
            agent_key="caption",
            entity_type="series",
            entity_id=series_id,
            workflow_stage=SeriesStage.CAPTIONS.value,
            trigger="regeneration",
            input_payload={"caption_id": str(caption.id), "platform": caption.platform.value},
            output_payload={
                "summary": f"Regenerated {caption.platform.value} caption.",
                "needs_approval": True,
            },
        )
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def update_caption(
        self,
        series_id: UUID,
        caption_id: UUID,
        payload: CaptionUpdateRequest,
    ) -> dict[str, object]:
        caption = await self._get_caption(series_id, caption_id)
        await self._assert_episode_captionable(
            caption.series_id,
            caption.episode_id,
            await self._video_by_id(caption.episode_video_id),
        )
        caption.caption_text = payload.caption_text
        caption.status = CaptionStatus.READY
        await self._mark_episode_captioning(caption.episode_id)
        await self._unlock_scheduling_if_ready(series_id)
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def _workspace_response(self, series_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        await self.session.refresh(series)
        episodes = await self._episodes(series_id)
        videos = await self._videos_by_episode(series_id)
        transcripts = await self._transcripts_by_episode(series_id)
        captions = await self._captions_by_episode(series_id)
        clip_suggestions = await self._clip_suggestions_by_episode(series_id)

        episode_payloads = []
        for episode in episodes:
            video = videos.get(episode.id)
            if video is None:
                continue
            episode_captions = captions.get(episode.id, [])
            transcript = transcripts.get(episode.id)
            clip_slots = [
                self._clip_slot_payload(
                    clip_suggestion=clip,
                    captions=[
                        caption
                        for caption in episode_captions
                        if caption.clip_suggestion_id == clip.id
                    ],
                )
                for clip in clip_suggestions.get(episode.id, [])
            ]
            full_captions = [
                caption
                for caption in episode_captions
                if caption.video_kind == CaptionVideoKind.FULL_EPISODE
            ]
            ready_count = self._ready_count(episode_captions)
            episode_payloads.append(
                {
                    "episode_id": episode.id,
                    "episode_number": episode.episode_number,
                    "episode_title": episode.title,
                    "episode_premise": episode.premise,
                    "episode_status": episode.status,
                    "video_status": video.status,
                    "transcript_status": transcript.status if transcript else None,
                    "transcript_ready": self._transcript_ready(transcript),
                    "caption_blockers": self._caption_blockers(video, transcript),
                    "video": self._media_record_payload(video),
                    "transcript": self._media_record_payload(transcript)
                    if transcript is not None
                    else None,
                    "full_episode_captions": [
                        self._caption_payload(caption) for caption in full_captions
                    ],
                    "full_available_platforms": self._available_platforms(
                        CaptionVideoKind.FULL_EPISODE,
                        full_captions,
                    ),
                    "short_clip_slots": clip_slots,
                    "ready_caption_count": ready_count,
                    "total_caption_count": len(episode_captions),
                }
            )

        all_captions = [caption for items in captions.values() for caption in items]
        full_ready_count = self._ready_count(
            [
                caption
                for caption in all_captions
                if caption.video_kind == CaptionVideoKind.FULL_EPISODE
            ]
        )
        short_ready_count = self._ready_count(
            [
                caption
                for caption in all_captions
                if caption.video_kind == CaptionVideoKind.SHORT_CLIP
            ]
        )
        ready_count = self._ready_count(all_captions)

        return {
            "series": series,
            "episodes": episode_payloads,
            "full_episode_platforms": list(FULL_EPISODE_PLATFORMS),
            "short_clip_platforms": list(SHORT_CLIP_PLATFORMS),
            "readiness": {
                "total_caption_count": len(all_captions),
                "ready_caption_count": ready_count,
                "full_episode_ready_count": full_ready_count,
                "short_clip_ready_count": short_ready_count,
                "scheduling_unlocked": series.scheduling_unlocked_at is not None,
                "warnings": self._readiness_warnings(all_captions, episode_payloads),
            },
        }

    async def _ensure_full_episode_rows(
        self,
        series_id: UUID,
        episodes: list[Episode],
    ) -> None:
        videos = await self._videos_by_episode(series_id)
        transcripts = await self._transcripts_by_episode(series_id)
        existing = await self._captions_by_episode(series_id)
        for episode in episodes:
            video = videos.get(episode.id)
            transcript = transcripts.get(episode.id)
            if video is None or not self._transcript_ready(transcript):
                continue
            existing_platforms = {
                caption.platform
                for caption in existing.get(episode.id, [])
                if caption.video_kind == CaptionVideoKind.FULL_EPISODE
            }
            for platform in FULL_EPISODE_PLATFORMS:
                if platform in existing_platforms:
                    continue
                self.session.add(
                    EpisodeVideoPlatformCaption(
                        series_id=series_id,
                        episode_id=episode.id,
                        episode_video_id=video.id,
                        video_kind=CaptionVideoKind.FULL_EPISODE,
                        video_key="full",
                        platform=platform,
                    )
                )
        await self.session.flush()

    async def _assert_episode_captionable(
        self,
        series_id: UUID,
        episode_id: UUID,
        video: EpisodeVideo,
    ) -> None:
        transcript = await self._transcript_for_episode(series_id, episode_id)
        blockers = self._caption_blockers(video, transcript)
        if blockers:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Caption generation blocked: {', '.join(blockers)}",
            )

    def _assert_captions_unlocked(self, series: Series) -> None:
        if (
            series.captions_unlocked_at is not None
            or series.scheduling_unlocked_at is not None
            or series.current_stage in {SeriesStage.CAPTIONS, SeriesStage.SCHEDULE}
        ):
            return
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload a transcript before working on captions",
        )

    def _assert_platform_allowed(
        self,
        video_kind: CaptionVideoKind,
        platform: Platform,
    ) -> None:
        if platform not in self._valid_platforms(video_kind):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{platform.value} is not available for {video_kind.value}",
            )

    async def _get_episode(self, series_id: UUID, episode_id: UUID) -> Episode:
        episode = await self.session.get(Episode, episode_id)
        if episode is None or episode.series_id != series_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found")
        return episode

    async def _get_caption(
        self,
        series_id: UUID,
        caption_id: UUID,
    ) -> EpisodeVideoPlatformCaption:
        caption = await self.session.get(EpisodeVideoPlatformCaption, caption_id)
        if caption is None or caption.series_id != series_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caption not found")
        return caption

    async def _video_by_id(self, video_id: UUID) -> EpisodeVideo:
        video = await self.session.get(EpisodeVideo, video_id)
        if video is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
        return video

    async def _video_for_episode(self, series_id: UUID, episode_id: UUID) -> EpisodeVideo:
        result = await self.session.execute(
            select(EpisodeVideo).where(
                EpisodeVideo.series_id == series_id,
                EpisodeVideo.episode_id == episode_id,
            )
        )
        video = result.scalar_one_or_none()
        if video is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Upload the full episode video before configuring captions",
            )
        return video

    async def _get_clip_suggestion(
        self,
        series_id: UUID,
        episode_id: UUID,
        clip_suggestion_id: UUID,
    ) -> ClipSuggestion:
        clip_suggestion = await self.session.get(ClipSuggestion, clip_suggestion_id)
        if (
            clip_suggestion is None
            or clip_suggestion.series_id != series_id
            or clip_suggestion.episode_id != episode_id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clip suggestion not found",
            )
        return clip_suggestion

    async def _caption_for_key(
        self,
        episode_video_id: UUID,
        video_kind: CaptionVideoKind,
        video_key: str,
        platform: Platform,
    ) -> EpisodeVideoPlatformCaption | None:
        result = await self.session.execute(
            select(EpisodeVideoPlatformCaption).where(
                EpisodeVideoPlatformCaption.episode_video_id == episode_video_id,
                EpisodeVideoPlatformCaption.video_kind == video_kind,
                EpisodeVideoPlatformCaption.video_key == video_key,
                EpisodeVideoPlatformCaption.platform == platform,
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

    async def _videos_by_episode(self, series_id: UUID) -> dict[UUID, EpisodeVideo]:
        result = await self.session.execute(
            select(EpisodeVideo).where(EpisodeVideo.series_id == series_id)
        )
        return {video.episode_id: video for video in result.scalars().all()}

    async def _transcript_for_episode(
        self,
        series_id: UUID,
        episode_id: UUID,
    ) -> Transcript | None:
        result = await self.session.execute(
            select(Transcript).where(
                Transcript.series_id == series_id,
                Transcript.episode_id == episode_id,
            )
        )
        return result.scalar_one_or_none()

    async def _transcripts_by_episode(self, series_id: UUID) -> dict[UUID, Transcript]:
        result = await self.session.execute(
            select(Transcript).where(Transcript.series_id == series_id)
        )
        return {transcript.episode_id: transcript for transcript in result.scalars().all()}

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

    async def _mark_episode_captioning(self, episode_id: UUID) -> None:
        episode = await self.session.get(Episode, episode_id)
        if episode and episode.status in {
            EpisodeStatus.APPROVED,
            EpisodeStatus.RECORDED,
        }:
            episode.status = EpisodeStatus.CAPTIONING

    async def _unlock_scheduling_if_ready(self, series_id: UUID) -> None:
        await self.session.flush()
        result = await self.session.execute(
            select(func.count(EpisodeVideoPlatformCaption.id)).where(
                EpisodeVideoPlatformCaption.series_id == series_id,
                EpisodeVideoPlatformCaption.status == CaptionStatus.READY,
            )
        )
        ready_count = result.scalar_one()
        if ready_count == 0:
            return

        series = await self.series_service.get_series(series_id)
        now = datetime.now(UTC)
        series.scheduling_unlocked_at = series.scheduling_unlocked_at or now
        series.current_stage = SeriesStage.SCHEDULE
        series.status = SeriesStatus.IN_PRODUCTION

    async def _generated_caption(
        self,
        caption: EpisodeVideoPlatformCaption,
        regenerated: bool,
    ) -> str:
        episode = await self._get_episode(caption.series_id, caption.episode_id)
        transcript = await self._transcript_for_episode(caption.series_id, caption.episode_id)
        label = self._platform_label(caption.platform)
        prefix = "Regenerated" if regenerated else "Generated"
        if caption.video_kind == CaptionVideoKind.SHORT_CLIP and caption.clip_suggestion_id:
            clip = await self._get_clip_suggestion(
                caption.series_id,
                caption.episode_id,
                caption.clip_suggestion_id,
            )
            clip_title = self._caption_copy_fragment(
                clip.title,
                fallback=f"Episode {episode.episode_number} short highlight",
            )
            clip_rationale = self._caption_copy_fragment(
                clip.rationale,
                fallback="A focused short-form moment from this episode.",
            )
            return (
                f"{prefix} {label} short clip caption: {clip_title}\n\n"
                f"{clip_rationale}\n\n"
                f"Watch the short highlight from Episode {episode.episode_number}, "
                f"{episode.title}. "
                "#Streamly #ExecutiveAI"
            )

        transcript_name = transcript.file_name if transcript else "the transcript"
        return (
            f"{prefix} {label} caption for Episode {episode.episode_number}: {episode.title}\n\n"
            f"{episode.premise}\n\n"
            f"Built from {transcript_name}. Share this with teams turning AI strategy into "
            "an operating rhythm. #Streamly #AILeadership"
        )

    def _clip_slot_payload(
        self,
        clip_suggestion: ClipSuggestion,
        captions: list[EpisodeVideoPlatformCaption],
    ) -> dict[str, object]:
        return {
            "clip_suggestion": clip_suggestion,
            "captions": [self._caption_payload(caption) for caption in captions],
            "available_platforms": self._available_platforms(
                CaptionVideoKind.SHORT_CLIP,
                captions,
            ),
            "complete_caption_count": self._ready_count(captions),
        }

    def _caption_payload(self, caption: EpisodeVideoPlatformCaption) -> dict[str, object]:
        can_schedule = caption.status == CaptionStatus.READY and bool(caption.caption_text)
        return {
            "id": caption.id,
            "series_id": caption.series_id,
            "episode_id": caption.episode_id,
            "episode_video_id": caption.episode_video_id,
            "clip_suggestion_id": caption.clip_suggestion_id,
            "video_kind": caption.video_kind,
            "video_key": caption.video_key,
            "platform": caption.platform,
            "status": caption.status,
            "caption_text": caption.caption_text,
            "generation_count": caption.generation_count,
            "generated_at": caption.generated_at,
            "created_at": caption.created_at,
            "updated_at": caption.updated_at,
            "can_schedule": can_schedule,
            "scheduling_locked_reason": None
            if can_schedule
            else "Scheduling locked until this caption is generated or edited.",
        }

    def _media_record_payload(self, record: EpisodeVideo | Transcript) -> dict[str, object]:
        payload = {column.name: getattr(record, column.key) for column in record.__table__.columns}
        payload["media_asset"] = None
        payload["metadata"] = None
        payload["processing_jobs"] = []
        return payload

    def _caption_blockers(
        self,
        video: EpisodeVideo,
        transcript: Transcript | None,
    ) -> list[str]:
        blockers = []
        if video.status == VideoStatus.MISSING or not video.file_path:
            blockers.append("video missing")
        if not self._transcript_ready(transcript):
            blockers.append("transcript missing")
        return blockers

    def _readiness_warnings(
        self,
        captions: list[EpisodeVideoPlatformCaption],
        episode_payloads: list[dict[str, object]],
    ) -> list[str]:
        warnings = []
        if not captions:
            warnings.append("No caption platform rows are ready yet.")
        ready_count = self._ready_count(captions)
        if captions and ready_count == 0:
            warnings.append("Generate at least one caption to unlock Scheduling.")
        if captions and ready_count < len(captions):
            warnings.append(
                f"{len(captions) - ready_count} caption row(s) remain locked for scheduling."
            )
        blocked_episode_count = sum(
            bool(episode["caption_blockers"]) for episode in episode_payloads
        )
        if blocked_episode_count:
            warnings.append(
                f"{blocked_episode_count} episode(s) still need transcript-ready media."
            )
        return warnings

    def _available_platforms(
        self,
        video_kind: CaptionVideoKind,
        captions: list[EpisodeVideoPlatformCaption],
    ) -> list[Platform]:
        existing_platforms = {caption.platform for caption in captions}
        return [
            platform
            for platform in self._valid_platforms(video_kind)
            if platform not in existing_platforms
        ]

    def _valid_platforms(self, video_kind: CaptionVideoKind) -> tuple[Platform, ...]:
        if video_kind == CaptionVideoKind.FULL_EPISODE:
            return FULL_EPISODE_PLATFORMS
        return SHORT_CLIP_PLATFORMS

    def _ready_count(self, captions: list[EpisodeVideoPlatformCaption]) -> int:
        return sum(
            caption.status == CaptionStatus.READY and bool(caption.caption_text)
            for caption in captions
        )

    def _transcript_ready(self, transcript: Transcript | None) -> bool:
        return transcript is not None and transcript.status != TranscriptStatus.FAILED

    def _clip_video_key(self, clip_suggestion_id: UUID) -> str:
        return f"clip:{clip_suggestion_id}"

    def _caption_copy_fragment(self, value: str, fallback: str) -> str:
        text = CAPTION_TIMECODE_RANGE_RE.sub(" ", value)
        text = CAPTION_SPACED_TIMECODE_RANGE_RE.sub(" ", text)
        text = CAPTION_SINGLE_TIMECODE_RE.sub(" ", text)
        text = CAPTION_CLIP_PREFIX_RE.sub("", text)
        text = CAPTION_META_PREFIX_RE.sub("", text)
        text = CAPTION_SPEAKER_LABEL_RE.sub("", text)
        text = re.sub(r"\s+", " ", text).strip(" -–—:·")
        return text or fallback

    def _platform_label(self, platform: Platform) -> str:
        if platform == Platform.X:
            return "X"
        return platform.value.title()
