from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.api.v1.endpoints.captions import get_caption_service
from app.db.types import (
    CaptionStatus,
    CaptionVideoKind,
    ClipSuggestionStatus,
    DiscoveryStatus,
    EpisodeStatus,
    Platform,
    SeriesStage,
    SeriesStatus,
    TranscriptStatus,
    VideoStatus,
)
from app.main import create_app
from app.modules.captions.service import CaptionService
from app.modules.recordings.models import EpisodeVideo, Transcript
from app.modules.recordings.schemas import EpisodeVideoResponse, TranscriptResponse
from app.modules.series.models import Series


def _series_payload(
    series_id: UUID,
    *,
    scheduling_unlocked: bool = False,
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
        "current_stage": (
            SeriesStage.SCHEDULE.value if scheduling_unlocked else SeriesStage.CAPTIONS.value
        ),
        "episode_plan_generated_at": now,
        "plan_locked_at": now,
        "briefs_approved_at": now,
        "captions_unlocked_at": now,
        "scheduling_unlocked_at": now if scheduling_unlocked else None,
        "created_at": now,
        "updated_at": now,
    }


def _video_payload(series_id: UUID, episode_id: UUID) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid4()),
        "series_id": str(series_id),
        "episode_id": str(episode_id),
        "status": VideoStatus.LOCKED.value,
        "file_path": f"series/{series_id}/episodes/{episode_id}/recordings/video/episode.mp4",
        "file_name": "episode.mp4",
        "content_type": "video/mp4",
        "file_size_bytes": 128,
        "uploaded_at": now,
        "locked_at": now,
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


def test_caption_media_payload_does_not_expose_sqlalchemy_metadata() -> None:
    now = datetime.now(UTC)
    series_id = uuid4()
    episode_id = uuid4()
    video = EpisodeVideo(
        id=uuid4(),
        series_id=series_id,
        episode_id=episode_id,
        status=VideoStatus.COMPLETE,
        file_path=f"series/{series_id}/episodes/{episode_id}/recordings/video/episode.mp4",
        file_name="episode.mp4",
        content_type="video/mp4",
        file_size_bytes=128,
        uploaded_at=now,
        created_at=now,
        updated_at=now,
    )
    transcript = Transcript(
        id=uuid4(),
        series_id=series_id,
        episode_id=episode_id,
        status=TranscriptStatus.PROCESSED,
        file_path=f"series/{series_id}/episodes/{episode_id}/recordings/transcript/show.vtt",
        file_name="show.vtt",
        content_type="text/vtt",
        file_size_bytes=96,
        uploaded_at=now,
        processed_at=now,
        created_at=now,
        updated_at=now,
    )
    service = CaptionService(session=None)  # type: ignore[arg-type]

    video_payload = service._media_record_payload(video)
    transcript_payload = service._media_record_payload(transcript)

    assert video_payload["metadata"] is None
    assert transcript_payload["metadata"] is None
    EpisodeVideoResponse.model_validate(video_payload)
    TranscriptResponse.model_validate(transcript_payload)


def test_caption_copy_fragment_removes_transcript_timecodes_and_labels() -> None:
    service = CaptionService(session=None)  # type: ignore[arg-type]

    assert service._caption_copy_fragment(
        "Clip 2: 00 05 00 11 Narrator In the earliest stage of opportunity discovery",
        fallback="fallback",
    ) == "In the earliest stage of opportunity discovery"
    assert service._caption_copy_fragment(
        "Transcript-backed moment with clear short-form potential: "
        "00:05 - 00:11 Narrator: Producers face the same challenge",
        fallback="fallback",
    ) == "Producers face the same challenge"
    assert service._caption_copy_fragment(
        "A public speaker explains why candid leadership signals matter.",
        fallback="fallback",
    ) == "A public speaker explains why candid leadership signals matter."


def test_caption_gate_allows_scheduling_ready_series_without_stale_caption_timestamp() -> None:
    now = datetime.now(UTC)
    service = CaptionService(session=None)  # type: ignore[arg-type]
    series = Series(
        id=uuid4(),
        name="Tkxel Talks",
        audience="Employees",
        description="A production-ready series.",
        status=SeriesStatus.IN_PRODUCTION,
        discovery_status=DiscoveryStatus.COMPLETE,
        current_stage=SeriesStage.SCHEDULE,
        captions_unlocked_at=None,
        scheduling_unlocked_at=now,
        created_at=now,
        updated_at=now,
    )

    service._assert_captions_unlocked(series)


def _clip_payload(series_id: UUID, episode_id: UUID) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid4()),
        "series_id": str(series_id),
        "episode_id": str(episode_id),
        "slot_number": 1,
        "title": "Executive hook",
        "rationale": "A concise moment for short-form packaging.",
        "start_timecode": "00:01:15",
        "end_timecode": "00:02:05",
        "status": ClipSuggestionStatus.SUGGESTED.value,
        "created_at": now,
        "updated_at": now,
    }


def _caption_payload(
    series_id: UUID,
    episode_id: UUID,
    episode_video_id: str,
    platform: Platform,
    *,
    video_kind: CaptionVideoKind = CaptionVideoKind.FULL_EPISODE,
    clip_suggestion_id: str | None = None,
    ready: bool = False,
    generation_count: int = 0,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    caption_text = f"Caption for {platform.value}" if ready else None
    return {
        "id": str(uuid4()),
        "series_id": str(series_id),
        "episode_id": str(episode_id),
        "episode_video_id": episode_video_id,
        "clip_suggestion_id": clip_suggestion_id,
        "video_kind": video_kind.value,
        "video_key": "full"
        if video_kind == CaptionVideoKind.FULL_EPISODE
        else f"clip:{clip_suggestion_id}",
        "platform": platform.value,
        "status": CaptionStatus.READY.value if ready else CaptionStatus.NOT_STARTED.value,
        "caption_text": caption_text,
        "generation_count": generation_count,
        "generated_at": now if ready else None,
        "created_at": now,
        "updated_at": now,
        "can_schedule": ready,
        "scheduling_locked_reason": None
        if ready
        else "Scheduling locked until this caption is generated or edited.",
    }


def _workspace(
    series_id: UUID,
    *,
    ready_count: int = 0,
    include_short_clip: bool = False,
) -> dict[str, object]:
    episode_id = uuid4()
    video = _video_payload(series_id, episode_id)
    transcript = _transcript_payload(series_id, episode_id)
    full_captions = [
        _caption_payload(
            series_id,
            episode_id,
            video["id"],
            platform,
            ready=index < ready_count,
            generation_count=1 if index < ready_count else 0,
        )
        for index, platform in enumerate([Platform.LINKEDIN, Platform.FACEBOOK, Platform.YOUTUBE])
    ]
    clip = _clip_payload(series_id, episode_id)
    short_caption = _caption_payload(
        series_id,
        episode_id,
        video["id"],
        Platform.INSTAGRAM,
        video_kind=CaptionVideoKind.SHORT_CLIP,
        clip_suggestion_id=clip["id"],
        ready=include_short_clip and ready_count > 0,
        generation_count=1 if include_short_clip and ready_count > 0 else 0,
    )
    short_clip_slots = [
        {
            "clip_suggestion": clip,
            "captions": [short_caption] if include_short_clip else [],
            "available_platforms": [
                platform.value
                for platform in [
                    Platform.INSTAGRAM,
                    Platform.YOUTUBE,
                    Platform.TIKTOK,
                    Platform.X,
                    Platform.FACEBOOK,
                    Platform.LINKEDIN,
                ]
                if not include_short_clip or platform != Platform.INSTAGRAM
            ],
            "complete_caption_count": 1 if include_short_clip and ready_count > 0 else 0,
        }
    ]
    ready_total = sum(caption["can_schedule"] for caption in full_captions)
    if include_short_clip and short_caption["can_schedule"]:
        ready_total += 1
    total_count = len(full_captions) + (1 if include_short_clip else 0)
    return {
        "series": _series_payload(series_id, scheduling_unlocked=ready_total > 0),
        "episodes": [
            {
                "episode_id": str(episode_id),
                "episode_number": 1,
                "episode_title": "Set the executive frame",
                "episode_premise": "Open the narrative with an operating model decision.",
                "episode_status": EpisodeStatus.CAPTIONING.value
                if ready_total
                else EpisodeStatus.RECORDED.value,
                "video_status": VideoStatus.LOCKED.value,
                "transcript_status": TranscriptStatus.PROCESSED.value,
                "transcript_ready": True,
                "caption_blockers": [],
                "video": video,
                "transcript": transcript,
                "full_episode_captions": full_captions,
                "full_available_platforms": [],
                "short_clip_slots": short_clip_slots,
                "ready_caption_count": ready_total,
                "total_caption_count": total_count,
            }
        ],
        "full_episode_platforms": [
            Platform.LINKEDIN.value,
            Platform.FACEBOOK.value,
            Platform.YOUTUBE.value,
        ],
        "short_clip_platforms": [
            Platform.INSTAGRAM.value,
            Platform.YOUTUBE.value,
            Platform.TIKTOK.value,
            Platform.X.value,
            Platform.FACEBOOK.value,
            Platform.LINKEDIN.value,
        ],
        "readiness": {
            "total_caption_count": total_count,
            "ready_caption_count": ready_total,
            "full_episode_ready_count": min(ready_total, len(full_captions)),
            "short_clip_ready_count": 1
            if include_short_clip and short_caption["can_schedule"]
            else 0,
            "scheduling_unlocked": ready_total > 0,
            "warnings": []
            if ready_total == total_count
            else ["Uncaptioned rows remain locked for scheduling."],
        },
    }


class FakeCaptionService:
    async def get_workspace(self, series_id: UUID):
        return _workspace(series_id)

    async def add_platform(self, series_id: UUID, episode_id: UUID, payload):
        return _workspace(series_id, include_short_clip=True)

    async def generate_caption(self, series_id: UUID, caption_id: UUID):
        return _workspace(series_id, ready_count=1)

    async def regenerate_caption(self, series_id: UUID, caption_id: UUID):
        return _workspace(series_id, ready_count=1)

    async def update_caption(self, series_id: UUID, caption_id: UUID, payload):
        return _workspace(series_id, ready_count=1)


class FakeLockedCaptionService(FakeCaptionService):
    async def get_workspace(self, series_id: UUID):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload a transcript before working on captions",
        )


class FakeInvalidPlatformCaptionService(FakeCaptionService):
    async def add_platform(self, series_id: UUID, episode_id: UUID, payload):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="instagram is not available for full_episode",
        )


class FakeDuplicatePlatformCaptionService(FakeCaptionService):
    async def add_platform(self, series_id: UUID, episode_id: UUID, payload):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That platform is already configured for this video row",
        )


class FakeTranscriptMissingCaptionService(FakeCaptionService):
    async def generate_caption(self, series_id: UUID, caption_id: UUID):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Caption generation blocked: transcript missing",
        )


def _client(service: object | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_caption_service] = lambda: service or FakeCaptionService()
    return TestClient(app)


def test_captions_workspace_requires_transcript_gate() -> None:
    response = _client(FakeLockedCaptionService()).get(f"/api/v1/series/{uuid4()}/captions")

    assert response.status_code == 409
    assert "transcript" in response.text


def test_captions_workspace_shows_full_episode_platform_grid() -> None:
    response = _client().get(f"/api/v1/series/{uuid4()}/captions")

    assert response.status_code == 200
    body = response.json()
    episode = body["episodes"][0]
    assert body["full_episode_platforms"] == ["linkedin", "facebook", "youtube"]
    assert len(episode["full_episode_captions"]) == 3
    assert episode["transcript_ready"] is True


def test_add_platform_rejects_invalid_video_kind_platform_pair() -> None:
    response = _client(FakeInvalidPlatformCaptionService()).post(
        f"/api/v1/series/{uuid4()}/captions/episodes/{uuid4()}/platforms",
        json={"video_kind": "full_episode", "platform": "instagram"},
    )

    assert response.status_code == 400
    assert "not available" in response.text


def test_add_platform_rejects_already_configured_platform() -> None:
    response = _client(FakeDuplicatePlatformCaptionService()).post(
        f"/api/v1/series/{uuid4()}/captions/episodes/{uuid4()}/platforms",
        json={"video_kind": "full_episode", "platform": "linkedin"},
    )

    assert response.status_code == 409
    assert "already configured" in response.text


def test_add_platform_supports_short_clip_platform_rows() -> None:
    response = _client().post(
        f"/api/v1/series/{uuid4()}/captions/episodes/{uuid4()}/platforms",
        json={
            "video_kind": "short_clip",
            "platform": "instagram",
            "clip_suggestion_id": str(uuid4()),
        },
    )

    assert response.status_code == 200
    slot = response.json()["episodes"][0]["short_clip_slots"][0]
    assert slot["captions"][0]["platform"] == "instagram"
    assert "instagram" not in slot["available_platforms"]


def test_generate_caption_unlocks_row_level_scheduling() -> None:
    response = _client().post(f"/api/v1/series/{uuid4()}/captions/{uuid4()}/generate")

    assert response.status_code == 200
    body = response.json()
    caption = body["episodes"][0]["full_episode_captions"][0]
    assert caption["status"] == "ready"
    assert caption["can_schedule"] is True
    assert body["readiness"]["scheduling_unlocked"] is True
    assert body["series"]["scheduling_unlocked_at"] is not None


def test_regenerate_caption_preserves_readiness() -> None:
    response = _client().post(f"/api/v1/series/{uuid4()}/captions/{uuid4()}/regenerate")

    assert response.status_code == 200
    caption = response.json()["episodes"][0]["full_episode_captions"][0]
    assert caption["status"] == "ready"
    assert caption["generation_count"] == 1


def test_manual_caption_edit_marks_caption_ready() -> None:
    response = _client().patch(
        f"/api/v1/series/{uuid4()}/captions/{uuid4()}",
        json={"caption_text": "Edited LinkedIn caption"},
    )

    assert response.status_code == 200
    caption = response.json()["episodes"][0]["full_episode_captions"][0]
    assert caption["caption_text"]
    assert caption["can_schedule"] is True


def test_partial_caption_completion_keeps_uncaptioned_rows_locked() -> None:
    response = _client().post(f"/api/v1/series/{uuid4()}/captions/{uuid4()}/generate")

    assert response.status_code == 200
    captions = response.json()["episodes"][0]["full_episode_captions"]
    assert captions[0]["can_schedule"] is True
    assert captions[1]["can_schedule"] is False
    assert "locked" in captions[1]["scheduling_locked_reason"]


def test_caption_generation_blocks_missing_transcript() -> None:
    response = _client(FakeTranscriptMissingCaptionService()).post(
        f"/api/v1/series/{uuid4()}/captions/{uuid4()}/generate"
    )

    assert response.status_code == 409
    assert "transcript missing" in response.text
