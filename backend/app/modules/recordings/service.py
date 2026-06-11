import re
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.clip_suggestions import (
    ClipSuggestionAgent,
    ClipSuggestionDraft,
    EvidenceSignal,
    evidence_signal_from_document,
)
from app.agents.llm.database import DatabaseGeminiLLMProvider
from app.core.config import settings
from app.db.types import (
    BriefStatus,
    ClipSuggestionStatus,
    EpisodeStatus,
    MediaAssetKind,
    MediaAssetStatus,
    MediaProcessingJobStatus,
    MediaProcessingJobType,
    NarrativeStatus,
    SeriesStage,
    SeriesStatus,
    ThumbnailStatus,
    TranscriptStatus,
    VideoStatus,
)
from app.files.signed_urls import SignedURLService
from app.files.storage import EmptyUploadError, StorageError, UploadTooLargeError, storage
from app.modules.briefs.models import EpisodeBrief
from app.modules.episodes.models import Episode
from app.modules.narratives.models import Narrative
from app.modules.recordings.media_services import (
    MediaMetadataExtractionService,
    TranscriptParserService,
    UploadValidationRule,
    UploadValidationService,
    upload_rule,
)
from app.modules.recordings.models import (
    ClipSuggestion,
    EpisodeVideo,
    MediaAsset,
    MediaAuditLog,
    MediaMetadata,
    MediaProcessingJob,
    Thumbnail,
    Transcript,
)
from app.modules.research.models import DiscoveryLedgerEntry, ResearchDocument
from app.modules.research_sources.models import ResearchSource
from app.modules.series.models import Series
from app.modules.series.service import SeriesService

VIDEO_CONTENT_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
TRANSCRIPT_CONTENT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/vtt",
    "application/x-subrip",
    "application/octet-stream",
}
TRANSCRIPT_EXTENSIONS = {".txt", ".md", ".vtt", ".srt"}
THUMBNAIL_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
THUMBNAIL_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_UPLOAD_RULE = upload_rule(
    "video",
    VIDEO_CONTENT_TYPES,
    VIDEO_EXTENSIONS,
    500 * 1024 * 1024,
)
TRANSCRIPT_UPLOAD_RULE = upload_rule(
    "transcript",
    TRANSCRIPT_CONTENT_TYPES,
    TRANSCRIPT_EXTENSIONS,
    10 * 1024 * 1024,
)
THUMBNAIL_UPLOAD_RULE = upload_rule(
    "thumbnail",
    THUMBNAIL_CONTENT_TYPES,
    THUMBNAIL_EXTENSIONS,
    10 * 1024 * 1024,
)


class RecordingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.series_service = SeriesService(session)
        self.validator = UploadValidationService()
        self.metadata_extractor = MediaMetadataExtractionService()
        self.transcript_parser = TranscriptParserService()
        self.signed_urls = SignedURLService()
        self.clip_suggestion_agent = ClipSuggestionAgent(DatabaseGeminiLLMProvider(session))

    async def get_workspace(self, series_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_recordings_unlocked(series)
        episodes = await self._episodes(series_id)
        await self._ensure_video_slots(series_id, episodes)
        await self._sync_caption_unlock_state(
            series,
            series_id,
            now=datetime.now(UTC),
        )
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def get_signed_media_url(self, asset_id: UUID) -> dict[str, object]:
        asset = await self.session.get(MediaAsset, asset_id)
        if asset is None or asset.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media asset not found",
            )
        signed_url = self.signed_urls.create(asset.storage_key)
        self._audit_media(
            asset,
            "media.signed_url_created",
            {"expires_at": signed_url.expires_at.isoformat()},
        )
        await self.session.commit()
        return {
            "asset_id": asset.id,
            "url": signed_url.url,
            "expires_at": signed_url.expires_at,
        }

    async def upload_video(
        self,
        series_id: UUID,
        episode_id: UUID,
        file: UploadFile,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_recordings_unlocked(series)
        episode = await self._get_episode(series_id, episode_id)
        await self._assert_episode_recordable(series_id, episode)
        slot = await self._ensure_video_slot(series_id, episode)
        self._assert_slot_open(slot)

        asset = await self._store_media_asset(
            file=file,
            series_id=series_id,
            episode_id=episode_id,
            media_kind=MediaAssetKind.VIDEO,
            rule=VIDEO_UPLOAD_RULE,
        )
        now = datetime.now(UTC)
        slot.file_path = asset.storage_key
        slot.file_name = asset.file_name
        slot.content_type = asset.content_type
        slot.file_size_bytes = asset.file_size_bytes
        slot.media_asset_id = asset.id
        slot.uploaded_at = now
        await self._run_metadata_extraction(asset)
        transcript = await self._transcript_for_episode(series_id, episode_id)
        await self._refresh_video_status(slot, transcript=transcript)
        await self._sync_caption_unlock_state(series, series_id, now=now)
        series.status = SeriesStatus.IN_PRODUCTION

        await self.session.commit()
        return await self._workspace_response(series_id)

    async def upload_transcript(
        self,
        series_id: UUID,
        episode_id: UUID,
        file: UploadFile,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_recordings_unlocked(series)
        episode = await self._get_episode(series_id, episode_id)
        await self._assert_episode_recordable(series_id, episode)
        slot = await self._ensure_video_slot(series_id, episode)
        self._assert_slot_open(slot)

        asset = await self._store_media_asset(
            file=file,
            series_id=series_id,
            episode_id=episode_id,
            media_kind=MediaAssetKind.TRANSCRIPT,
            rule=TRANSCRIPT_UPLOAD_RULE,
        )
        metadata = await self._run_transcript_parsing(asset)
        now = datetime.now(UTC)
        transcript = await self._transcript_for_episode(series_id, episode_id)
        if transcript is None:
            transcript = Transcript(
                series_id=series_id,
                episode_id=episode_id,
                file_path=asset.storage_key,
                file_name=asset.file_name,
                content_type=asset.content_type,
                file_size_bytes=asset.file_size_bytes,
                media_asset_id=asset.id,
                uploaded_at=now,
                processed_at=metadata.extracted_at,
                status=TranscriptStatus.PROCESSED,
            )
            self.session.add(transcript)
        else:
            transcript.file_path = asset.storage_key
            transcript.file_name = asset.file_name
            transcript.content_type = asset.content_type
            transcript.file_size_bytes = asset.file_size_bytes
            transcript.media_asset_id = asset.id
            transcript.uploaded_at = now
            transcript.processed_at = metadata.extracted_at
            transcript.status = TranscriptStatus.PROCESSED

        series.status = SeriesStatus.IN_PRODUCTION
        await self._refresh_video_status(slot, transcript=transcript)
        await self._sync_caption_unlock_state(series, series_id, now=now)

        await self.session.commit()
        return await self._workspace_response(series_id)

    async def upload_thumbnail(
        self,
        series_id: UUID,
        episode_id: UUID,
        file: UploadFile,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_recordings_unlocked(series)
        episode = await self._get_episode(series_id, episode_id)
        await self._assert_episode_recordable(series_id, episode)
        slot = await self._ensure_video_slot(series_id, episode)
        self._assert_slot_open(slot)

        asset = await self._store_media_asset(
            file=file,
            series_id=series_id,
            episode_id=episode_id,
            media_kind=MediaAssetKind.THUMBNAIL,
            rule=THUMBNAIL_UPLOAD_RULE,
        )
        await self._run_metadata_extraction(asset)
        await self.session.execute(
            update(Thumbnail)
            .where(
                Thumbnail.series_id == series_id,
                Thumbnail.episode_id == episode_id,
                Thumbnail.is_selected.is_(True),
            )
            .values(
                is_selected=False,
                status=ThumbnailStatus.UPLOADED,
            )
        )
        thumbnail = Thumbnail(
            series_id=series_id,
            episode_id=episode_id,
            status=ThumbnailStatus.SELECTED,
            is_selected=True,
            file_path=asset.storage_key,
            file_name=asset.file_name,
            content_type=asset.content_type,
            file_size_bytes=asset.file_size_bytes,
            media_asset_id=asset.id,
            uploaded_at=datetime.now(UTC),
        )
        self.session.add(thumbnail)

        await self.session.commit()
        return await self._workspace_response(series_id)

    async def upload_clip_suggestion_video(
        self,
        series_id: UUID,
        episode_id: UUID,
        clip_suggestion_id: UUID,
        file: UploadFile,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_recordings_unlocked(series)
        episode = await self._get_episode(series_id, episode_id)
        await self._assert_episode_recordable(series_id, episode)
        slot = await self._ensure_video_slot(series_id, episode)
        self._assert_slot_open(slot)
        clip_suggestion = await self._get_clip_suggestion(
            series_id,
            episode_id,
            clip_suggestion_id,
        )

        asset = await self._store_media_asset(
            file=file,
            series_id=series_id,
            episode_id=episode_id,
            media_kind=MediaAssetKind.VIDEO,
            rule=VIDEO_UPLOAD_RULE,
            storage_folder="short-clips",
        )
        await self._run_metadata_extraction(asset)
        now = datetime.now(UTC)
        clip_suggestion.clip_file_path = asset.storage_key
        clip_suggestion.clip_file_name = asset.file_name
        clip_suggestion.clip_content_type = asset.content_type
        clip_suggestion.clip_file_size_bytes = asset.file_size_bytes
        clip_suggestion.clip_media_asset_id = asset.id
        clip_suggestion.clip_uploaded_at = now
        self._audit_media(
            asset,
            "media.short_clip_uploaded",
            {
                "clip_suggestion_id": str(clip_suggestion.id),
                "slot_number": clip_suggestion.slot_number,
                "start_timecode": clip_suggestion.start_timecode,
                "end_timecode": clip_suggestion.end_timecode,
            },
        )

        await self.session.flush()
        await self._sync_caption_unlock_state(series, series_id, now=now)
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def select_thumbnail(
        self,
        series_id: UUID,
        episode_id: UUID,
        thumbnail_id: UUID,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_recordings_unlocked(series)
        episode = await self._get_episode(series_id, episode_id)
        await self._assert_episode_recordable(series_id, episode)
        slot = await self._ensure_video_slot(series_id, episode)
        self._assert_slot_open(slot)
        thumbnail = await self.session.get(Thumbnail, thumbnail_id)
        if (
            thumbnail is None
            or thumbnail.series_id != series_id
            or thumbnail.episode_id != episode_id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thumbnail not found",
            )

        await self.session.execute(
            update(Thumbnail)
            .where(Thumbnail.series_id == series_id, Thumbnail.episode_id == episode_id)
            .values(is_selected=False, status=ThumbnailStatus.UPLOADED)
        )
        thumbnail.is_selected = True
        thumbnail.status = ThumbnailStatus.SELECTED

        await self.session.commit()
        return await self._workspace_response(series_id)

    async def delete_thumbnail(
        self,
        series_id: UUID,
        episode_id: UUID,
        thumbnail_id: UUID,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_recordings_unlocked(series)
        episode = await self._get_episode(series_id, episode_id)
        await self._assert_episode_recordable(series_id, episode)
        slot = await self._ensure_video_slot(series_id, episode)
        self._assert_slot_open(slot)

        thumbnail = await self.session.get(Thumbnail, thumbnail_id)
        if (
            thumbnail is None
            or thumbnail.series_id != series_id
            or thumbnail.episode_id != episode_id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thumbnail not found",
            )

        was_selected = thumbnail.is_selected
        asset = (
            await self.session.get(MediaAsset, thumbnail.media_asset_id)
            if thumbnail.media_asset_id is not None
            else None
        )
        if asset is not None:
            storage.delete(asset.storage_key)
            asset.status = MediaAssetStatus.DELETED
            asset.deleted_at = datetime.now(UTC)
            self._audit_media(
                asset,
                "media.thumbnail_deleted",
                {
                    "thumbnail_id": str(thumbnail.id),
                    "file_name": thumbnail.file_name,
                    "storage_key": asset.storage_key,
                },
            )

        await self.session.delete(thumbnail)
        await self.session.flush()

        if was_selected:
            replacement = await self._first_available_thumbnail(
                series_id,
                episode_id,
            )
            if replacement is not None:
                replacement.is_selected = True
                replacement.status = ThumbnailStatus.SELECTED

        await self.session.commit()
        return await self._workspace_response(series_id)

    async def request_clip_suggestions(
        self,
        series_id: UUID,
        episode_id: UUID,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_recordings_unlocked(series)
        episode = await self._get_episode(series_id, episode_id)
        await self._assert_episode_recordable(series_id, episode)
        transcript = await self._transcript_for_episode(series_id, episode_id)
        if transcript is None or transcript.status == TranscriptStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Upload a transcript before requesting clip suggestions",
            )

        transcript_text = await self._transcript_text_for_suggestions(transcript)
        generation_source = "clip_suggestion_agent.gemini"
        try:
            suggestions = await self.clip_suggestion_agent.suggest(
                series=series,
                episode=episode,
                transcript_text=transcript_text,
                narrative=await self._selected_narrative(series_id),
                evidence_signals=await self._clip_evidence_signals(series_id),
            )
        except (RuntimeError, ValueError):
            generation_source = "transcript_fallback"
            suggestions = self._fallback_clip_suggestions(episode, transcript_text)

        existing_suggestions = {
            suggestion.slot_number: suggestion
            for suggestion in await self._clip_suggestions(series_id, episode_id)
        }
        for draft in suggestions:
            slot_number = draft.slot_number
            suggestion = existing_suggestions.get(slot_number)
            if suggestion is None:
                self.session.add(
                    ClipSuggestion(
                        series_id=series_id,
                        episode_id=episode_id,
                        slot_number=slot_number,
                        title=draft.title,
                        rationale=draft.rationale,
                        start_timecode=draft.start_timecode,
                        end_timecode=draft.end_timecode,
                        status=ClipSuggestionStatus.SUGGESTED,
                    )
                )
            else:
                suggestion.title = draft.title
                suggestion.rationale = draft.rationale
                suggestion.start_timecode = draft.start_timecode
                suggestion.end_timecode = draft.end_timecode
                suggestion.status = ClipSuggestionStatus.SUGGESTED

        if transcript.media_asset_id is not None:
            asset = await self.session.get(MediaAsset, transcript.media_asset_id)
            if asset is not None:
                self._audit_media(
                    asset,
                    "media.clip_suggestions_requested",
                    {
                        "episode_id": str(episode_id),
                        "generation_source": generation_source,
                        "suggestion_count": len(suggestions),
                    },
                )

        now = datetime.now(UTC)
        await self.session.flush()
        await self._sync_caption_unlock_state(series, series_id, now=now)
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def lock_recording(
        self,
        series_id: UUID,
        episode_id: UUID,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_recordings_unlocked(series)
        episode = await self._get_episode(series_id, episode_id)
        await self._assert_episode_recordable(series_id, episode)
        slot = await self._ensure_video_slot(series_id, episode)
        transcript = await self._transcript_for_episode(series_id, episode_id)
        if not slot.file_path or transcript is None or transcript.status == TranscriptStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Upload both video and transcript before locking the recording",
            )

        now = datetime.now(UTC)
        slot.status = VideoStatus.LOCKED
        slot.locked_at = slot.locked_at or now
        episode.status = EpisodeStatus.RECORDED
        series.status = SeriesStatus.IN_PRODUCTION
        await self._sync_caption_unlock_state(series, series_id, now=now)

        await self.session.commit()
        return await self._workspace_response(series_id)

    async def _workspace_response(self, series_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        await self.session.refresh(series)
        episodes = await self._episodes(series_id)
        videos = await self._videos_by_episode(series_id)
        transcripts = await self._transcripts_by_episode(series_id)
        thumbnails = await self._thumbnails_by_episode(series_id)
        suggestions = await self._clip_suggestions_by_episode(series_id)
        approved_episode_ids = await self._approved_episode_ids(series_id)
        media_context = await self._media_context(
            videos=videos.values(),
            transcripts=transcripts.values(),
            thumbnails=[
                thumbnail
                for thumbnail_group in thumbnails.values()
                for thumbnail in thumbnail_group
            ],
        )

        episode_payloads = [
            self._episode_payload(
                episode=episode,
                video=videos[episode.id],
                transcript=transcripts.get(episode.id),
                thumbnails=thumbnails.get(episode.id, []),
                clip_suggestions=suggestions.get(episode.id, []),
                brief_pair_approved=episode.id in approved_episode_ids,
                media_context=media_context,
            )
            for episode in episodes
        ]
        complete_count = sum(item["recording_complete"] for item in episode_payloads)
        transcript_ready_count = sum(item["captions_ready"] for item in episode_payloads)
        suggested_short_clip_count = sum(
            item["suggested_short_clip_count"] for item in episode_payloads
        )
        uploaded_short_clip_count = sum(
            item["uploaded_short_clip_count"] for item in episode_payloads
        )
        captions_unlocked = complete_count > 0

        return {
            "series": series,
            "episodes": episode_payloads,
            "readiness": {
                "total_episode_count": len(episode_payloads),
                "complete_episode_count": complete_count,
                "transcript_ready_episode_count": transcript_ready_count,
                "suggested_short_clip_count": suggested_short_clip_count,
                "uploaded_short_clip_count": uploaded_short_clip_count,
                "captions_unlocked": captions_unlocked,
                "warnings": self._readiness_warnings(
                    total_count=len(episode_payloads),
                    complete_count=complete_count,
                ),
            },
        }

    async def _ensure_video_slots(self, series_id: UUID, episodes: list[Episode]) -> None:
        videos = await self._videos_by_episode(series_id)
        for episode in episodes:
            if episode.id not in videos:
                self.session.add(EpisodeVideo(series_id=series_id, episode_id=episode.id))
        await self.session.flush()

    async def _ensure_video_slot(self, series_id: UUID, episode: Episode) -> EpisodeVideo:
        result = await self.session.execute(
            select(EpisodeVideo).where(EpisodeVideo.episode_id == episode.id)
        )
        slot = result.scalar_one_or_none()
        if slot is not None:
            return slot

        slot = EpisodeVideo(series_id=series_id, episode_id=episode.id)
        self.session.add(slot)
        await self.session.flush()
        return slot

    async def _sync_caption_unlock_state(
        self,
        series: Series,
        series_id: UUID,
        *,
        now: datetime,
    ) -> None:
        episodes = await self._episodes(series_id)
        videos = await self._videos_by_episode(series_id)
        transcripts = await self._transcripts_by_episode(series_id)
        has_caption_ready_episode = any(
            self._episode_caption_ready(
                videos.get(episode.id),
                transcripts.get(episode.id),
            )
            for episode in episodes
        )

        if has_caption_ready_episode:
            series.captions_unlocked_at = series.captions_unlocked_at or now
            if series.current_stage == SeriesStage.RECORDINGS:
                series.current_stage = SeriesStage.CAPTIONS
            return

        series.captions_unlocked_at = None
        if series.current_stage == SeriesStage.CAPTIONS:
            series.current_stage = SeriesStage.RECORDINGS

    async def _refresh_video_status(
        self,
        slot: EpisodeVideo,
        transcript: Transcript | None = None,
    ) -> None:
        if slot.locked_at is not None:
            slot.status = VideoStatus.LOCKED
            return
        if transcript is None:
            transcript = await self._transcript_for_episode(slot.series_id, slot.episode_id)
        if slot.file_path and transcript is not None:
            slot.status = VideoStatus.COMPLETE
        elif slot.file_path:
            slot.status = VideoStatus.UPLOADED
        else:
            slot.status = VideoStatus.MISSING

    async def _store_media_asset(
        self,
        file: UploadFile,
        series_id: UUID,
        episode_id: UUID,
        media_kind: MediaAssetKind,
        rule: UploadValidationRule,
        storage_folder: str | None = None,
    ) -> MediaAsset:
        validation = self.validator.validate(file, rule)

        folder = storage_folder or media_kind.value
        relative_path = (
            f"series/{series_id}/episodes/{episode_id}/recordings/"
            f"{folder}/{uuid4().hex}-{validation.file_name}"
        )
        try:
            stored_object = await storage.save_upload(
                relative_path,
                file,
                max_bytes=validation.max_bytes,
                chunk_size=settings.media_upload_chunk_bytes,
            )
        except UploadTooLargeError as exc:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"{media_kind.value.capitalize()} file exceeds size limit",
            ) from exc
        except EmptyUploadError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{media_kind.value.capitalize()} file cannot be empty",
            ) from exc
        except StorageError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not store {media_kind.value} upload",
            ) from exc

        now = datetime.now(UTC)
        asset = MediaAsset(
            series_id=series_id,
            episode_id=episode_id,
            kind=media_kind,
            status=MediaAssetStatus.UPLOADED,
            storage_provider="local",
            storage_key=stored_object.relative_path,
            file_name=validation.file_name,
            content_type=validation.content_type,
            file_size_bytes=stored_object.size_bytes,
            checksum_sha256=stored_object.checksum_sha256,
            uploaded_at=now,
        )
        self.session.add(asset)
        await self.session.flush()
        self._audit_media(
            asset,
            "media.uploaded",
            {
                "file_name": asset.file_name,
                "content_type": asset.content_type,
                "file_size_bytes": asset.file_size_bytes,
                "storage_provider": asset.storage_provider,
            },
        )
        return asset

    async def _run_metadata_extraction(self, asset: MediaAsset) -> MediaMetadata:
        job = self._start_processing_job(
            asset,
            MediaProcessingJobType.METADATA_EXTRACTION,
            {"storage_key": asset.storage_key},
        )
        try:
            payload = self.metadata_extractor.extract(
                file_name=asset.file_name,
                content_type=asset.content_type,
                file_size_bytes=asset.file_size_bytes,
                checksum_sha256=asset.checksum_sha256,
            )
            metadata = await self._upsert_metadata(asset, payload)
            self._complete_processing_job(job, asset, payload)
            asset.status = MediaAssetStatus.READY
            self._audit_media(asset, "media.metadata_extracted", payload["metadata"])
            return metadata
        except Exception as exc:
            self._fail_processing_job(job, asset, str(exc))
            raise

    async def _run_transcript_parsing(self, asset: MediaAsset) -> MediaMetadata:
        job = self._start_processing_job(
            asset,
            MediaProcessingJobType.TRANSCRIPT_PARSING,
            {"storage_key": asset.storage_key},
        )
        try:
            content = storage.resolve(asset.storage_key).read_bytes()
            payload = self.transcript_parser.parse(
                content,
                file_name=asset.file_name,
                content_type=asset.content_type,
            )
            metadata = await self._upsert_metadata(asset, payload)
            self._complete_processing_job(job, asset, payload)
            asset.status = MediaAssetStatus.READY
            self._audit_media(asset, "media.transcript_parsed", payload["metadata"])
            return metadata
        except Exception as exc:
            self._fail_processing_job(job, asset, str(exc))
            raise

    def _start_processing_job(
        self,
        asset: MediaAsset,
        job_type: MediaProcessingJobType,
        input_payload: dict[str, object],
    ) -> MediaProcessingJob:
        now = datetime.now(UTC)
        asset.status = MediaAssetStatus.PROCESSING
        job = MediaProcessingJob(
            media_asset_id=asset.id,
            series_id=asset.series_id,
            episode_id=asset.episode_id,
            job_type=job_type,
            status=MediaProcessingJobStatus.RUNNING,
            attempts=1,
            input_payload=input_payload,
            started_at=now,
        )
        self.session.add(job)
        self._audit_media(asset, "media.processing_started", {"job_type": job_type.value})
        return job

    def _complete_processing_job(
        self,
        job: MediaProcessingJob,
        asset: MediaAsset,
        output_payload: dict[str, object],
    ) -> None:
        now = datetime.now(UTC)
        job.status = MediaProcessingJobStatus.SUCCEEDED
        job.output_payload = output_payload
        job.completed_at = now
        if asset.status != MediaAssetStatus.FAILED:
            asset.status = MediaAssetStatus.READY
        self._audit_media(asset, "media.processing_completed", {"job_type": job.job_type.value})

    def _fail_processing_job(
        self,
        job: MediaProcessingJob,
        asset: MediaAsset,
        error_message: str,
    ) -> None:
        now = datetime.now(UTC)
        job.status = MediaProcessingJobStatus.FAILED
        job.error_message = error_message
        job.completed_at = now
        asset.status = MediaAssetStatus.FAILED
        asset.last_error = error_message
        self._audit_media(
            asset,
            "media.processing_failed",
            {"job_type": job.job_type.value, "error_message": error_message},
        )

    async def _upsert_metadata(
        self,
        asset: MediaAsset,
        payload: dict[str, object],
    ) -> MediaMetadata:
        metadata = await self._metadata_for_asset(asset.id)
        if metadata is None:
            metadata = MediaMetadata(
                media_asset_id=asset.id,
                series_id=asset.series_id,
                episode_id=asset.episode_id,
                extracted_at=datetime.now(UTC),
                metadata_payload={},
            )
            self.session.add(metadata)

        metadata.duration_seconds = payload.get("duration_seconds")  # type: ignore[assignment]
        metadata.width = payload.get("width")  # type: ignore[assignment]
        metadata.height = payload.get("height")  # type: ignore[assignment]
        metadata.frame_rate = payload.get("frame_rate")  # type: ignore[assignment]
        metadata.codec = payload.get("codec")  # type: ignore[assignment]
        metadata.transcript_cue_count = payload.get("transcript_cue_count")  # type: ignore[assignment]
        metadata.transcript_language = payload.get("transcript_language")  # type: ignore[assignment]
        metadata.metadata_payload = dict(payload.get("metadata") or {})
        metadata.extracted_at = datetime.now(UTC)
        await self.session.flush()
        return metadata

    def _audit_media(
        self,
        asset: MediaAsset,
        action: str,
        details: dict[str, object],
    ) -> None:
        self.session.add(
            MediaAuditLog(
                media_asset_id=asset.id,
                series_id=asset.series_id,
                episode_id=asset.episode_id,
                action=action,
                actor="system",
                details=details,
            )
        )

    async def _assert_episode_recordable(self, series_id: UUID, episode: Episode) -> None:
        approved_episode_ids = await self._approved_episode_ids(series_id)
        if episode.id not in approved_episode_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Approve the host and guest brief pair before uploading recordings",
            )

    def _assert_recordings_unlocked(self, series: Series) -> None:
        if series.briefs_approved_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Approve a brief pair before working on recordings",
            )

    def _assert_slot_open(self, slot: EpisodeVideo) -> None:
        if slot.locked_at is not None or slot.status == VideoStatus.LOCKED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Recording is locked and cannot be changed",
            )

    async def _episodes(self, series_id: UUID) -> list[Episode]:
        result = await self.session.execute(
            select(Episode)
            .where(Episode.series_id == series_id)
            .order_by(Episode.episode_number.asc())
        )
        return list(result.scalars().all())

    async def _get_episode(self, series_id: UUID, episode_id: UUID) -> Episode:
        episode = await self.session.get(Episode, episode_id)
        if episode is None or episode.series_id != series_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found")
        return episode

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

    async def _selected_thumbnail(
        self,
        series_id: UUID,
        episode_id: UUID,
    ) -> Thumbnail | None:
        result = await self.session.execute(
            select(Thumbnail).where(
                Thumbnail.series_id == series_id,
                Thumbnail.episode_id == episode_id,
                Thumbnail.is_selected.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def _first_available_thumbnail(
        self,
        series_id: UUID,
        episode_id: UUID,
    ) -> Thumbnail | None:
        result = await self.session.execute(
            select(Thumbnail)
            .where(
                Thumbnail.series_id == series_id,
                Thumbnail.episode_id == episode_id,
            )
            .order_by(Thumbnail.created_at.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _thumbnails_by_episode(self, series_id: UUID) -> dict[UUID, list[Thumbnail]]:
        result = await self.session.execute(
            select(Thumbnail)
            .where(Thumbnail.series_id == series_id)
            .order_by(Thumbnail.episode_id.asc(), Thumbnail.created_at.asc())
        )
        grouped: dict[UUID, list[Thumbnail]] = {}
        for thumbnail in result.scalars().all():
            grouped.setdefault(thumbnail.episode_id, []).append(thumbnail)
        return grouped

    async def _clip_suggestions(
        self,
        series_id: UUID,
        episode_id: UUID,
    ) -> list[ClipSuggestion]:
        result = await self.session.execute(
            select(ClipSuggestion)
            .where(
                ClipSuggestion.series_id == series_id,
                ClipSuggestion.episode_id == episode_id,
            )
            .order_by(ClipSuggestion.slot_number.asc())
        )
        return list(result.scalars().all())

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

    async def _transcript_text_for_suggestions(self, transcript: Transcript) -> str:
        text = ""
        if transcript.file_path:
            try:
                text = storage.resolve(transcript.file_path).read_text(
                    encoding="utf-8-sig",
                    errors="replace",
                )
            except (OSError, ValueError):
                text = ""

        if text.strip() or transcript.media_asset_id is None:
            return text

        metadata = await self._metadata_for_asset(transcript.media_asset_id)
        if metadata is None:
            return ""
        return str(metadata.metadata_payload.get("text_preview") or "")

    async def _selected_narrative(self, series_id: UUID) -> Narrative | None:
        result = await self.session.execute(
            select(Narrative).where(
                Narrative.series_id == series_id,
                Narrative.status == NarrativeStatus.SELECTED,
                Narrative.is_selected.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def _clip_evidence_signals(self, series_id: UUID) -> list[EvidenceSignal]:
        result = await self.session.execute(
            select(ResearchDocument, ResearchSource)
            .join(
                DiscoveryLedgerEntry,
                DiscoveryLedgerEntry.document_id == ResearchDocument.id,
            )
            .join(ResearchSource, ResearchSource.id == ResearchDocument.source_id)
            .where(
                DiscoveryLedgerEntry.series_id == series_id,
                ResearchSource.enabled.is_(True),
                ResearchDocument.archived.is_(False),
            )
            .order_by(
                func.coalesce(ResearchDocument.trend_score, 0).desc(),
                ResearchDocument.composite_score.desc(),
                ResearchDocument.created_at.desc(),
            )
            .limit(12)
        )
        signals = []
        seen_document_ids: set[UUID] = set()
        for document, source in result.all():
            if document.id in seen_document_ids:
                continue
            signals.append(evidence_signal_from_document(document, source))
            seen_document_ids.add(document.id)
            if len(signals) == 8:
                break
        return signals

    def _fallback_clip_suggestions(
        self,
        episode: Episode,
        transcript_text: str,
    ) -> list[ClipSuggestionDraft]:
        return [
            ClipSuggestionDraft(
                slot_number=int(payload["slot_number"]),
                title=str(payload["title"]),
                rationale=str(payload["rationale"]),
                start_timecode=str(payload["start_timecode"]),
                end_timecode=str(payload["end_timecode"]),
            )
            for payload in self._clip_suggestion_payloads(episode, transcript_text)
        ]

    def _clip_suggestion_payloads(
        self,
        episode: Episode,
        transcript_text: str,
    ) -> list[dict[str, object]]:
        cleaned_text = self._clean_transcript_text(transcript_text)
        moments = self._candidate_moments(cleaned_text, episode.premise)
        windows = self._timecode_windows(transcript_text, len(moments))
        payloads = []
        for index, moment in enumerate(moments, start=1):
            start_timecode, end_timecode = windows[index - 1]
            payloads.append(
                {
                    "slot_number": index,
                    "title": self._clip_title(moment, episode.title, index),
                    "rationale": self._clip_rationale(moment),
                    "start_timecode": start_timecode,
                    "end_timecode": end_timecode,
                }
            )
        return payloads

    def _clean_transcript_text(self, transcript_text: str) -> str:
        lines = []
        for raw_line in transcript_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.upper() == "WEBVTT" or line.isdigit() or "-->" in line:
                continue
            lines.append(line)
        return " ".join(lines)

    def _candidate_moments(self, transcript_text: str, fallback: str) -> list[str]:
        sentences = [
            sentence.strip(" -")
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", transcript_text)
            if len(sentence.strip(" -")) >= 24
        ]
        if not sentences and fallback:
            sentences = [fallback]
        if not sentences:
            sentences = ["A concise moment from the uploaded transcript."]

        while len(sentences) < 3:
            sentences.append(sentences[-1])
        return sentences[:3]

    def _timecode_windows(
        self,
        transcript_text: str,
        count: int,
    ) -> list[tuple[str, str]]:
        matches = re.findall(
            r"((?:\d{1,2}:)?\d{2}:\d{2}(?:[,.]\d{1,3})?)\s*-->\s*"
            r"((?:\d{1,2}:)?\d{2}:\d{2}(?:[,.]\d{1,3})?)",
            transcript_text,
        )
        windows = [
            (self._normalize_timecode(start), self._normalize_timecode(end))
            for start, end in matches[:count]
        ]
        while len(windows) < count:
            index = len(windows)
            start_seconds = 30 + index * 60
            windows.append(
                (
                    self._seconds_to_timecode(start_seconds),
                    self._seconds_to_timecode(start_seconds + 30),
                )
            )
        return windows

    def _normalize_timecode(self, value: str) -> str:
        time_without_millis = value.replace(",", ".").split(".", maxsplit=1)[0]
        parts = time_without_millis.split(":")
        if len(parts) == 2:
            return f"00:{parts[0]}:{parts[1]}"
        return time_without_millis

    def _seconds_to_timecode(self, total_seconds: int) -> str:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _clip_title(self, moment: str, episode_title: str, index: int) -> str:
        words = re.findall(r"[A-Za-z0-9']+", moment)
        if not words:
            return f"Clip {index}: {episode_title}"[:220]
        headline = " ".join(words[:8])
        if len(words) > 8:
            headline = f"{headline}..."
        return f"Clip {index}: {headline}"[:220]

    def _clip_rationale(self, moment: str) -> str:
        trimmed = moment.strip()
        if len(trimmed) > 180:
            trimmed = f"{trimmed[:177].rstrip()}..."
        return f"Transcript-backed moment with clear short-form potential: {trimmed}"

    async def _metadata_for_asset(self, asset_id: UUID) -> MediaMetadata | None:
        result = await self.session.execute(
            select(MediaMetadata).where(MediaMetadata.media_asset_id == asset_id)
        )
        return result.scalar_one_or_none()

    async def _media_context(
        self,
        *,
        videos,
        transcripts,
        thumbnails,
    ) -> dict[str, dict[UUID, object]]:
        asset_ids = {
            media_asset_id
            for media_asset_id in [
                *(video.media_asset_id for video in videos),
                *(transcript.media_asset_id for transcript in transcripts),
                *(thumbnail.media_asset_id for thumbnail in thumbnails),
            ]
            if media_asset_id is not None
        }
        if not asset_ids:
            return {"assets": {}, "metadata": {}, "jobs": {}}

        asset_result = await self.session.execute(
            select(MediaAsset).where(MediaAsset.id.in_(asset_ids))
        )
        metadata_result = await self.session.execute(
            select(MediaMetadata).where(MediaMetadata.media_asset_id.in_(asset_ids))
        )
        job_result = await self.session.execute(
            select(MediaProcessingJob)
            .where(MediaProcessingJob.media_asset_id.in_(asset_ids))
            .order_by(MediaProcessingJob.created_at.desc())
        )

        jobs_by_asset: dict[UUID, list[MediaProcessingJob]] = {}
        for job in job_result.scalars().all():
            jobs_by_asset.setdefault(job.media_asset_id, []).append(job)

        return {
            "assets": {asset.id: asset for asset in asset_result.scalars().all()},
            "metadata": {
                metadata.media_asset_id: metadata for metadata in metadata_result.scalars().all()
            },
            "jobs": jobs_by_asset,
        }

    async def _approved_episode_ids(self, series_id: UUID) -> set[UUID]:
        result = await self.session.execute(
            select(EpisodeBrief.episode_id)
            .where(
                EpisodeBrief.series_id == series_id,
                EpisodeBrief.status == BriefStatus.APPROVED,
            )
            .group_by(EpisodeBrief.episode_id)
            .having(func.count(EpisodeBrief.id) == 2)
        )
        return set(result.scalars().all())

    def _episode_payload(
        self,
        episode: Episode,
        video: EpisodeVideo,
        transcript: Transcript | None,
        thumbnails: list[Thumbnail],
        clip_suggestions: list[ClipSuggestion],
        brief_pair_approved: bool,
        media_context: dict[str, dict[UUID, object]],
    ) -> dict[str, object]:
        selected_thumbnail = next(
            (
                thumbnail
                for thumbnail in thumbnails
                if thumbnail.is_selected and not self._is_generated_thumbnail(thumbnail)
            ),
            None,
        )
        video_file_uploaded = video.file_path is not None
        transcript_uploaded = (
            transcript is not None and transcript.status != TranscriptStatus.FAILED
        )
        suggested_short_clip_count, uploaded_short_clip_count = self._clip_media_progress(
            clip_suggestions
        )
        recording_complete = self._episode_caption_ready(video, transcript)
        recording_locked = video.locked_at is not None or video.status == VideoStatus.LOCKED
        upload_blockers = self._upload_blockers(
            brief_pair_approved=brief_pair_approved,
            recording_locked=recording_locked,
        )
        return {
            "episode_id": episode.id,
            "episode_number": episode.episode_number,
            "episode_title": episode.title,
            "episode_premise": episode.premise,
            "episode_status": episode.status,
            "brief_pair_approved": brief_pair_approved,
            "can_upload": not upload_blockers,
            "upload_blockers": upload_blockers,
            "video": self._asset_backed_payload(video, media_context),
            "transcript": self._asset_backed_payload(transcript, media_context)
            if transcript is not None
            else None,
            "thumbnails": [
                self._asset_backed_payload(thumbnail, media_context) for thumbnail in thumbnails
            ],
            "selected_thumbnail": self._asset_backed_payload(
                selected_thumbnail,
                media_context,
            )
            if selected_thumbnail is not None
            else None,
            "clip_suggestions": clip_suggestions,
            "video_file_uploaded": video_file_uploaded,
            "transcript_uploaded": transcript_uploaded,
            "suggested_short_clip_count": suggested_short_clip_count,
            "uploaded_short_clip_count": uploaded_short_clip_count,
            "recording_complete": recording_complete,
            "captions_ready": transcript_uploaded,
            "recording_locked": recording_locked,
            "locked_at": video.locked_at,
        }

    @staticmethod
    def _is_generated_thumbnail(thumbnail: Thumbnail) -> bool:
        return "/recordings/generated-thumbnails/" in (thumbnail.file_path or "")

    def _clip_media_progress(self, clip_suggestions: list[ClipSuggestion]) -> tuple[int, int]:
        suggested = [
            suggestion
            for suggestion in clip_suggestions
            if suggestion.status != ClipSuggestionStatus.REJECTED
        ]
        uploaded = sum(suggestion.clip_media_uploaded for suggestion in suggested)
        return len(suggested), uploaded

    def _asset_backed_payload(
        self,
        record: EpisodeVideo | Transcript | Thumbnail,
        media_context: dict[str, dict[UUID, object]],
    ) -> dict[str, object]:
        payload = {column.name: getattr(record, column.key) for column in record.__table__.columns}
        asset_id = payload.get("media_asset_id")
        if isinstance(asset_id, UUID):
            payload["media_asset"] = self._media_asset_payload(
                media_context["assets"].get(asset_id)
            )
            payload["metadata"] = self._metadata_payload(media_context["metadata"].get(asset_id))
            payload["processing_jobs"] = media_context["jobs"].get(asset_id, [])
        else:
            payload["media_asset"] = None
            payload["metadata"] = None
            payload["processing_jobs"] = []
        return payload

    def _media_asset_payload(self, asset: object | None) -> dict[str, object] | None:
        if not isinstance(asset, MediaAsset):
            return None
        payload = {column.name: getattr(asset, column.key) for column in asset.__table__.columns}
        signed_url = self.signed_urls.create(asset.storage_key)
        payload["signed_url"] = signed_url.url
        payload["signed_url_expires_at"] = signed_url.expires_at
        return payload

    def _metadata_payload(self, metadata: object | None) -> dict[str, object] | None:
        if not isinstance(metadata, MediaMetadata):
            return None
        payload = {
            column.name: getattr(metadata, column.key) for column in metadata.__table__.columns
        }
        payload["metadata"] = metadata.metadata_payload
        return payload

    def _upload_blockers(
        self,
        brief_pair_approved: bool,
        recording_locked: bool,
    ) -> list[str]:
        blockers = []
        if not brief_pair_approved:
            blockers.append("brief pair approval")
        if recording_locked:
            blockers.append("recording locked")
        return blockers

    def _readiness_warnings(
        self,
        total_count: int,
        complete_count: int,
    ) -> list[str]:
        warnings = []
        if total_count and complete_count < total_count:
            warnings.append(
                f"{total_count - complete_count} episode(s) still have required "
                "recording fields missing."
            )
        if total_count and complete_count == 0:
            warnings.append(
                "Complete at least one episode with video and transcript before "
                "Captions can unlock."
            )
        return warnings

    @staticmethod
    def _episode_caption_ready(
        video: EpisodeVideo | None,
        transcript: Transcript | None,
    ) -> bool:
        return (
            video is not None
            and video.file_path is not None
            and transcript is not None
            and transcript.status != TranscriptStatus.FAILED
        )
