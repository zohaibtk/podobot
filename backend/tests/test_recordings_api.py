from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.api.v1.endpoints.recordings import get_recording_service
from app.db.types import (
    ClipSuggestionStatus,
    DiscoveryStatus,
    EpisodeStatus,
    SeriesStage,
    SeriesStatus,
    ThumbnailStatus,
    TranscriptStatus,
    VideoStatus,
)
from app.main import create_app
from app.modules.recordings.models import EpisodeVideo, Transcript
from app.modules.recordings.service import RecordingService


def _series_payload(
    series_id: UUID,
    *,
    captions_unlocked: bool = False,
    current_stage: SeriesStage = SeriesStage.RECORDINGS,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(series_id),
        "name": "Executive AI Briefings",
        "audience": "Enterprise technology leaders",
        "description": "A series about operational AI adoption.",
        "guest_name": "Provided Guest",
        "status": SeriesStatus.IN_PRODUCTION.value,
        "discovery_status": DiscoveryStatus.COMPLETE.value,
        "current_stage": current_stage.value,
        "episode_plan_generated_at": now,
        "plan_locked_at": now,
        "briefs_approved_at": now,
        "captions_unlocked_at": now if captions_unlocked else None,
        "created_at": now,
        "updated_at": now,
    }


def _video_payload(
    series_id: UUID,
    episode_id: UUID,
    *,
    uploaded: bool = False,
    complete: bool = False,
    locked: bool = False,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    status_value = VideoStatus.MISSING
    if locked:
        status_value = VideoStatus.LOCKED
    elif complete:
        status_value = VideoStatus.COMPLETE
    elif uploaded:
        status_value = VideoStatus.UPLOADED
    return {
        "id": str(uuid4()),
        "series_id": str(series_id),
        "episode_id": str(episode_id),
        "status": status_value.value,
        "file_path": f"series/{series_id}/episodes/{episode_id}/recordings/video/episode.mp4"
        if uploaded
        else None,
        "file_name": "episode.mp4" if uploaded else None,
        "content_type": "video/mp4" if uploaded else None,
        "file_size_bytes": 128 if uploaded else None,
        "uploaded_at": now if uploaded else None,
        "locked_at": now if locked else None,
        "created_at": now,
        "updated_at": now,
    }


def _transcript_payload(series_id: UUID, episode_id: UUID) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid4()),
        "series_id": str(series_id),
        "episode_id": str(episode_id),
        "status": TranscriptStatus.PROCESSED.value,
        "file_path": f"series/{series_id}/episodes/{episode_id}/recordings/transcript/show.vtt",
        "file_name": "show.vtt",
        "content_type": "text/vtt",
        "file_size_bytes": 96,
        "uploaded_at": now,
        "processed_at": now,
        "created_at": now,
        "updated_at": now,
    }


def _thumbnail_payload(
    series_id: UUID,
    episode_id: UUID,
    *,
    selected: bool = True,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid4()),
        "series_id": str(series_id),
        "episode_id": str(episode_id),
        "status": ThumbnailStatus.SELECTED.value if selected else ThumbnailStatus.UPLOADED.value,
        "is_selected": selected,
        "file_path": f"series/{series_id}/episodes/{episode_id}/recordings/thumbnails/hero.png",
        "file_name": "hero.png",
        "content_type": "image/png",
        "file_size_bytes": 64,
        "uploaded_at": now,
        "created_at": now,
        "updated_at": now,
    }


def test_caption_unlock_rule_requires_one_complete_episode_not_all() -> None:
    series_id = uuid4()
    ready_episode_id = uuid4()
    missing_episode_id = uuid4()
    ready_video = EpisodeVideo(
        series_id=series_id,
        episode_id=ready_episode_id,
        status=VideoStatus.COMPLETE,
        file_path="recordings/episode-1.mp4",
    )
    ready_transcript = Transcript(
        series_id=series_id,
        episode_id=ready_episode_id,
        status=TranscriptStatus.PROCESSED,
    )
    missing_video = EpisodeVideo(
        series_id=series_id,
        episode_id=missing_episode_id,
        status=VideoStatus.MISSING,
    )
    service = RecordingService(session=None)  # type: ignore[arg-type]
    episode_readiness = [
        service._episode_caption_ready(ready_video, ready_transcript),
        service._episode_caption_ready(missing_video, None),
    ]

    assert any(episode_readiness) is True
    assert all(episode_readiness) is False


def _clip_payload(
    series_id: UUID,
    episode_id: UUID,
    slot_number: int,
    *,
    uploaded: bool = False,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid4()),
        "series_id": str(series_id),
        "episode_id": str(episode_id),
        "slot_number": slot_number,
        "title": "Executive hook",
        "rationale": "A strong signal for short-form packaging.",
        "start_timecode": "00:01:15",
        "end_timecode": "00:02:05",
        "clip_file_path": f"series/{series_id}/episodes/{episode_id}/short-clips/clip-{slot_number}.mp4"
        if uploaded
        else None,
        "clip_file_name": f"clip-{slot_number}.mp4" if uploaded else None,
        "clip_content_type": "video/mp4" if uploaded else None,
        "clip_file_size_bytes": 256 if uploaded else None,
        "clip_media_asset_id": str(uuid4()) if uploaded else None,
        "clip_uploaded_at": now if uploaded else None,
        "clip_media_uploaded": uploaded,
        "status": ClipSuggestionStatus.SUGGESTED.value,
        "created_at": now,
        "updated_at": now,
    }


def _workspace(
    series_id: UUID,
    *,
    uploaded_video: bool = False,
    uploaded_transcript: bool = False,
    thumbnail: bool = False,
    clips: bool = False,
    uploaded_clips: bool = False,
    locked: bool = False,
    brief_pair_approved: bool = True,
) -> dict[str, object]:
    episode_id = uuid4()
    transcript = _transcript_payload(series_id, episode_id) if uploaded_transcript else None
    complete = uploaded_video and uploaded_transcript
    video = _video_payload(
        series_id,
        episode_id,
        uploaded=uploaded_video,
        complete=uploaded_video and uploaded_transcript,
        locked=locked,
    )
    thumbnails = [_thumbnail_payload(series_id, episode_id)] if thumbnail else []
    suggestions = (
        [
            _clip_payload(series_id, episode_id, index, uploaded=uploaded_clips)
            for index in range(1, 4)
        ]
        if clips
        else []
    )
    suggested_short_clip_count = len(suggestions)
    uploaded_short_clip_count = sum(
        bool(suggestion["clip_media_uploaded"]) for suggestion in suggestions
    )
    warnings = []
    if not complete:
        warnings.append("1 episode(s) still have required recording fields missing.")
    upload_blockers = []
    if not brief_pair_approved:
        upload_blockers.append("brief pair approval")
    if locked:
        upload_blockers.append("recording locked")
    current_stage = SeriesStage.CAPTIONS if locked else SeriesStage.RECORDINGS
    return {
        "series": _series_payload(
            series_id,
            captions_unlocked=complete or locked,
            current_stage=current_stage,
        ),
        "episodes": [
            {
                "episode_id": str(episode_id),
                "episode_number": 1,
                "episode_title": "Set the executive frame",
                "episode_premise": "Open the narrative with an operating model decision.",
                "episode_status": EpisodeStatus.RECORDED.value
                if locked
                else EpisodeStatus.APPROVED.value,
                "brief_pair_approved": brief_pair_approved,
                "can_upload": not upload_blockers,
                "upload_blockers": upload_blockers,
                "video": video,
                "transcript": transcript,
                "thumbnails": thumbnails,
                "selected_thumbnail": thumbnails[0] if thumbnails else None,
                "clip_suggestions": suggestions,
                "video_file_uploaded": uploaded_video,
                "transcript_uploaded": uploaded_transcript,
                "suggested_short_clip_count": suggested_short_clip_count,
                "uploaded_short_clip_count": uploaded_short_clip_count,
                "recording_complete": complete,
                "captions_ready": uploaded_transcript,
                "recording_locked": locked,
                "locked_at": video["locked_at"],
            }
        ],
        "readiness": {
            "total_episode_count": 1,
            "complete_episode_count": 1 if complete else 0,
            "transcript_ready_episode_count": 1 if uploaded_transcript else 0,
            "suggested_short_clip_count": suggested_short_clip_count,
            "uploaded_short_clip_count": uploaded_short_clip_count,
            "captions_unlocked": complete or locked,
            "warnings": warnings,
        },
    }


class FakeRecordingService:
    async def get_workspace(self, series_id: UUID):
        return _workspace(series_id)

    async def upload_video(self, series_id: UUID, episode_id: UUID, file):
        return _workspace(series_id, uploaded_video=True)

    async def upload_transcript(self, series_id: UUID, episode_id: UUID, file):
        return _workspace(series_id, uploaded_transcript=True)

    async def upload_thumbnail(self, series_id: UUID, episode_id: UUID, file):
        return _workspace(series_id, thumbnail=True)

    async def select_thumbnail(self, series_id: UUID, episode_id: UUID, thumbnail_id: UUID):
        return _workspace(series_id, thumbnail=True)

    async def delete_thumbnail(self, series_id: UUID, episode_id: UUID, thumbnail_id: UUID):
        return _workspace(series_id)

    async def request_clip_suggestions(self, series_id: UUID, episode_id: UUID):
        return _workspace(series_id, uploaded_transcript=True, clips=True)

    async def upload_clip_suggestion_video(
        self,
        series_id: UUID,
        episode_id: UUID,
        clip_suggestion_id: UUID,
        file,
    ):
        workspace = _workspace(series_id, uploaded_video=True, uploaded_transcript=True, clips=True)
        clip = workspace["episodes"][0]["clip_suggestions"][0]
        clip["clip_file_path"] = "series/example/short-clips/clip.mp4"
        clip["clip_file_name"] = "clip.mp4"
        clip["clip_content_type"] = "video/mp4"
        clip["clip_file_size_bytes"] = 256
        clip["clip_media_asset_id"] = str(uuid4())
        clip["clip_uploaded_at"] = datetime.now(UTC).isoformat()
        clip["clip_media_uploaded"] = True
        workspace["episodes"][0]["uploaded_short_clip_count"] = 1
        workspace["readiness"]["uploaded_short_clip_count"] = 1
        return workspace

    async def lock_recording(self, series_id: UUID, episode_id: UUID):
        return _workspace(series_id, uploaded_video=True, uploaded_transcript=True, locked=True)


class FakeLockedRecordingService(FakeRecordingService):
    async def get_workspace(self, series_id: UUID):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approve a brief pair before working on recordings",
        )


class FakeInvalidUploadRecordingService(FakeRecordingService):
    async def upload_video(self, series_id: UUID, episode_id: UUID, file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported video file type",
        )


class FakeClipBlockedRecordingService(FakeRecordingService):
    async def request_clip_suggestions(self, series_id: UUID, episode_id: UUID):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload a transcript before requesting clip suggestions",
        )


def _client(service: object | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_recording_service] = lambda: service or FakeRecordingService()
    return TestClient(app)


def test_recordings_workspace_requires_brief_approval() -> None:
    response = _client(FakeLockedRecordingService()).get(f"/api/v1/series/{uuid4()}/recordings")

    assert response.status_code == 409


def test_workspace_includes_full_episode_slot_before_uploads() -> None:
    response = _client().get(f"/api/v1/series/{uuid4()}/recordings")

    assert response.status_code == 200
    episode = response.json()["episodes"][0]
    assert episode["video"]["status"] == "missing"
    assert episode["video_file_uploaded"] is False
    assert episode["recording_complete"] is False


def test_video_upload_alone_is_not_complete() -> None:
    response = _client().post(
        f"/api/v1/series/{uuid4()}/recordings/episodes/{uuid4()}/video",
        files={"file": ("episode.mp4", b"video-bytes", "video/mp4")},
    )

    assert response.status_code == 200
    episode = response.json()["episodes"][0]
    assert episode["video_file_uploaded"] is True
    assert episode["transcript_uploaded"] is False
    assert episode["recording_complete"] is False


def test_transcript_upload_alone_does_not_complete_recording() -> None:
    response = _client().post(
        f"/api/v1/series/{uuid4()}/recordings/episodes/{uuid4()}/transcript",
        files={"file": ("show.vtt", b"WEBVTT", "text/vtt")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["episodes"][0]["captions_ready"] is True
    assert body["episodes"][0]["recording_complete"] is False
    assert body["readiness"]["complete_episode_count"] == 0
    assert body["readiness"]["captions_unlocked"] is False
    assert body["series"]["captions_unlocked_at"] is None


def test_upload_failure_returns_visible_reason() -> None:
    response = _client(FakeInvalidUploadRecordingService()).post(
        f"/api/v1/series/{uuid4()}/recordings/episodes/{uuid4()}/video",
        files={"file": ("episode.exe", b"bad", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "Unsupported video file type" in response.text


def test_thumbnail_upload_creates_selectable_thumbnail() -> None:
    response = _client().post(
        f"/api/v1/series/{uuid4()}/recordings/episodes/{uuid4()}/thumbnails",
        files={"file": ("hero.png", b"png", "image/png")},
    )

    assert response.status_code == 200
    episode = response.json()["episodes"][0]
    assert episode["selected_thumbnail"]["is_selected"] is True


def test_thumbnail_delete_removes_thumbnail_option() -> None:
    response = _client().delete(
        f"/api/v1/series/{uuid4()}/recordings/episodes/{uuid4()}/thumbnails/{uuid4()}"
    )

    assert response.status_code == 200
    episode = response.json()["episodes"][0]
    assert episode["thumbnails"] == []
    assert episode["selected_thumbnail"] is None


def test_clip_suggestions_require_transcript() -> None:
    response = _client(FakeClipBlockedRecordingService()).post(
        f"/api/v1/series/{uuid4()}/recordings/episodes/{uuid4()}/clip-suggestions"
    )

    assert response.status_code == 409
    assert "transcript" in response.text


def test_clip_suggestions_are_metadata_only() -> None:
    response = _client().post(
        f"/api/v1/series/{uuid4()}/recordings/episodes/{uuid4()}/clip-suggestions"
    )

    assert response.status_code == 200
    suggestions = response.json()["episodes"][0]["clip_suggestions"]
    assert len(suggestions) == 3
    assert "file_path" not in suggestions[0]


class FakeCompleteWithSuggestedClipsService(FakeRecordingService):
    async def get_workspace(self, series_id: UUID):
        return _workspace(
            series_id,
            uploaded_video=True,
            uploaded_transcript=True,
            clips=True,
            uploaded_clips=False,
        )


def test_clip_suggestions_do_not_block_captions_unlock() -> None:
    response = _client(FakeCompleteWithSuggestedClipsService()).get(
        f"/api/v1/series/{uuid4()}/recordings"
    )

    assert response.status_code == 200
    readiness = response.json()["readiness"]
    assert readiness["suggested_short_clip_count"] == 3
    assert readiness["uploaded_short_clip_count"] == 0
    assert readiness["captions_unlocked"] is True
    assert not readiness["warnings"]


def test_clip_suggestion_video_upload_attaches_media_to_slot() -> None:
    response = _client().post(
        f"/api/v1/series/{uuid4()}/recordings/episodes/{uuid4()}/clip-suggestions/{uuid4()}/video",
        files={"file": ("clip.mp4", b"video-bytes", "video/mp4")},
    )

    assert response.status_code == 200
    clip = response.json()["episodes"][0]["clip_suggestions"][0]
    assert clip["clip_media_uploaded"] is True
    assert clip["clip_file_name"] == "clip.mp4"


def test_recording_lock_freezes_episode_and_moves_to_captions() -> None:
    response = _client().post(f"/api/v1/series/{uuid4()}/recordings/episodes/{uuid4()}/lock")

    assert response.status_code == 200
    body = response.json()
    episode = body["episodes"][0]
    assert episode["video_file_uploaded"] is True
    assert episode["recording_complete"] is True
    assert episode["recording_locked"] is True
    assert episode["episode_status"] == "recorded"
    assert episode["can_upload"] is False
    assert body["series"]["current_stage"] == "captions"
