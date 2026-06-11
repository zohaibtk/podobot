from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.api.v1.endpoints.schedules import get_schedule_service
from app.db.types import (
    BufferAccountStatus,
    BufferPostStatus,
    CaptionStatus,
    CaptionVideoKind,
    DiscoveryStatus,
    EpisodeStatus,
    Platform,
    ScheduleStatus,
    SeriesStage,
    SeriesStatus,
)
from app.main import create_app
from app.modules.captions.models import EpisodeVideoPlatformCaption
from app.modules.recordings.models import ClipSuggestion
from app.modules.schedules.buffer_service import BufferPostResult, BufferPublishingService
from app.modules.schedules.models import BufferAccount, EpisodeVideoPlatformSchedule
from app.modules.schedules.service import ScheduleService


def _series_payload(series_id: UUID, *, scheduling_unlocked: bool = True) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(series_id),
        "name": "Executive AI Briefings",
        "audience": "Enterprise technology leaders",
        "description": "A series about operational AI adoption.",
        "guest_name": "Provided Guest",
        "status": SeriesStatus.IN_PRODUCTION.value,
        "discovery_status": DiscoveryStatus.COMPLETE.value,
        "current_stage": SeriesStage.SCHEDULE.value,
        "episode_plan_generated_at": now,
        "plan_locked_at": now,
        "briefs_approved_at": now,
        "captions_unlocked_at": now,
        "scheduling_unlocked_at": now if scheduling_unlocked else None,
        "created_at": now,
        "updated_at": now,
    }


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
        "status": "suggested",
        "created_at": now,
        "updated_at": now,
    }


def _schedule_payload(
    series_id: UUID,
    episode_id: UUID,
    caption_id: UUID,
    platform: Platform,
    *,
    schedule_status: ScheduleStatus = ScheduleStatus.SCHEDULED,
    failure_reason: str | None = None,
    live_url: str | None = None,
    retry_count: int = 0,
) -> dict[str, object]:
    now = datetime.now(UTC)
    buffer_status = {
        ScheduleStatus.SCHEDULED: BufferPostStatus.QUEUED,
        ScheduleStatus.PUBLISHED: BufferPostStatus.PUBLISHED,
        ScheduleStatus.FAILED: BufferPostStatus.FAILED,
        ScheduleStatus.CANCELLED: BufferPostStatus.CANCELLED,
    }[schedule_status]
    return {
        "id": str(uuid4()),
        "series_id": str(series_id),
        "episode_id": str(episode_id),
        "episode_video_id": str(uuid4()),
        "media_asset_id": None,
        "caption_id": str(caption_id),
        "clip_suggestion_id": None,
        "video_kind": CaptionVideoKind.FULL_EPISODE.value,
        "video_key": "full",
        "platform": platform.value,
        "status": schedule_status.value,
        "buffer_status": buffer_status.value,
        "buffer_post_id": f"buf_{str(caption_id).replace('-', '')[:12]}",
        "scheduled_for": (now + timedelta(hours=2)).isoformat(),
        "scheduled_caption_text": f"Scheduled copy for {platform.value}",
        "failure_reason": failure_reason,
        "live_url": live_url,
        "scheduled_at": now.isoformat(),
        "published_at": now.isoformat() if schedule_status == ScheduleStatus.PUBLISHED else None,
        "cancelled_at": now.isoformat() if schedule_status == ScheduleStatus.CANCELLED else None,
        "last_synced_at": now.isoformat(),
        "retry_count": retry_count,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }


def _row_payload(
    series_id: UUID,
    episode_id: UUID,
    platform: Platform,
    *,
    ready: bool = True,
    schedule_status: ScheduleStatus | None = None,
    failure_reason: str | None = None,
    live_url: str | None = None,
    retry_count: int = 0,
) -> dict[str, object]:
    caption_id = uuid4()
    schedule = (
        _schedule_payload(
            series_id,
            episode_id,
            caption_id,
            platform,
            schedule_status=schedule_status,
            failure_reason=failure_reason,
            live_url=live_url,
            retry_count=retry_count,
        )
        if schedule_status is not None
        else None
    )
    return {
        "caption_id": str(caption_id),
        "series_id": str(series_id),
        "episode_id": str(episode_id),
        "episode_video_id": str(uuid4()),
        "clip_suggestion_id": None,
        "video_kind": CaptionVideoKind.FULL_EPISODE.value,
        "video_key": "full",
        "platform": platform.value,
        "caption_status": CaptionStatus.READY.value if ready else CaptionStatus.NOT_STARTED.value,
        "caption_text": f"Caption for {platform.value}" if ready else None,
        "schedule": schedule,
        "is_captioned": ready,
        "media_ready": True,
        "schedule_ready": ready,
        "media_file_name": None,
        "can_create_schedule": ready and schedule_status is None,
        "can_reschedule": ready
        and schedule_status
        in {ScheduleStatus.SCHEDULED, ScheduleStatus.FAILED, ScheduleStatus.CANCELLED},
        "schedule_locked_reason": None
        if ready and schedule_status is None
        else failure_reason or ("Only captioned rows can be scheduled." if not ready else None),
    }


def test_short_clip_schedule_row_requires_uploaded_clip_media() -> None:
    series_id = uuid4()
    episode_id = uuid4()
    clip_id = uuid4()
    caption = EpisodeVideoPlatformCaption(
        id=uuid4(),
        series_id=series_id,
        episode_id=episode_id,
        episode_video_id=uuid4(),
        clip_suggestion_id=clip_id,
        video_kind=CaptionVideoKind.SHORT_CLIP,
        video_key=f"clip:{clip_id}",
        platform=Platform.INSTAGRAM,
        status=CaptionStatus.READY,
        caption_text="Captioned clip row",
    )
    clip_without_media = ClipSuggestion(
        id=clip_id,
        series_id=series_id,
        episode_id=episode_id,
        slot_number=1,
        title="Clip hook",
        rationale="A suggested clip moment.",
        start_timecode="00:00:10",
        end_timecode="00:00:40",
    )
    service = ScheduleService(session=None)  # type: ignore[arg-type]

    row = service._row_payload(
        caption,
        schedule=None,
        schedule_context={"channels": {}, "audits": {}},
        clip_lookup={clip_id: clip_without_media},
    )

    assert row["is_captioned"] is True
    assert row["media_ready"] is False
    assert row["schedule_ready"] is False
    assert row["can_create_schedule"] is False
    assert "Upload the suggested clip video" in str(row["schedule_locked_reason"])


class _AuditOnlySession:
    def add(self, value: object) -> None:
        return None


def _schedule_model(*, scheduled_for: datetime) -> EpisodeVideoPlatformSchedule:
    return EpisodeVideoPlatformSchedule(
        id=uuid4(),
        series_id=uuid4(),
        episode_id=uuid4(),
        episode_video_id=uuid4(),
        caption_id=uuid4(),
        video_kind=CaptionVideoKind.FULL_EPISODE,
        video_key="full",
        platform=Platform.LINKEDIN,
        status=ScheduleStatus.SCHEDULED,
        buffer_status=BufferPostStatus.QUEUED,
        buffer_post_id="buf_due_post",
        scheduled_for=scheduled_for,
        scheduled_caption_text="Scheduled copy",
        retry_count=0,
    )


@pytest.mark.asyncio
async def test_development_buffer_sync_marks_due_post_failed_not_published(monkeypatch) -> None:
    now = datetime.now(UTC)
    account = BufferAccount(
        id=uuid4(),
        name="PodoBot Buffer",
        status=BufferAccountStatus.CONNECTED,
        access_token_secret="dev-buffer-access-token",
        scopes=[],
        rate_limit={},
    )
    schedule = _schedule_model(scheduled_for=now - timedelta(minutes=5))
    service = BufferPublishingService(_AuditOnlySession())  # type: ignore[arg-type]

    async def fake_schedule_target(schedule):
        return account, None

    monkeypatch.setattr(service, "_schedule_target", fake_schedule_target)

    result = await service.sync_post(schedule, now)

    assert result.status == BufferPostStatus.FAILED
    assert "development Buffer connector" in str(result.failure_reason)


@pytest.mark.asyncio
async def test_live_buffer_sync_marks_overdue_queued_post_failed(monkeypatch) -> None:
    now = datetime.now(UTC)
    account = BufferAccount(
        id=uuid4(),
        name="Live Buffer",
        status=BufferAccountStatus.CONNECTED,
        access_token_secret="live-buffer-access-token",
        organization_id="org_123",
        scopes=[],
        rate_limit={},
    )
    schedule = _schedule_model(scheduled_for=now - timedelta(minutes=5))
    service = BufferPublishingService(_AuditOnlySession())  # type: ignore[arg-type]

    async def fake_schedule_target(schedule):
        return account, None

    def fake_live_sync_result(account, schedule):
        return BufferPostResult(
            post_id=schedule.buffer_post_id,
            status=BufferPostStatus.QUEUED,
            raw_response={"status": "scheduled"},
        )

    monkeypatch.setattr(service, "_schedule_target", fake_schedule_target)
    monkeypatch.setattr(service, "_live_sync_result", fake_live_sync_result)

    result = await service.sync_post(schedule, now)

    assert result.status == BufferPostStatus.FAILED
    assert result.raw_response and result.raw_response["overdue_queue"] is True
    assert "still reports this post as queued" in str(result.failure_reason)


def _workspace(
    series_id: UUID,
    *,
    first_schedule_status: ScheduleStatus | None = None,
    failure_reason: str | None = None,
    live_url: str | None = None,
    bulk_result: dict[str, int] | None = None,
    retry_count: int = 0,
) -> dict[str, object]:
    episode_id = uuid4()
    rows = [
        _row_payload(
            series_id,
            episode_id,
            Platform.LINKEDIN,
            schedule_status=first_schedule_status,
            failure_reason=failure_reason,
            live_url=live_url,
            retry_count=retry_count,
        ),
        _row_payload(series_id, episode_id, Platform.FACEBOOK, ready=False),
        _row_payload(series_id, episode_id, Platform.YOUTUBE),
    ]
    scheduled_count = sum(
        row["schedule"] is not None and row["schedule"]["status"] == "scheduled" for row in rows
    )
    published_count = sum(
        row["schedule"] is not None and row["schedule"]["status"] == "published" for row in rows
    )
    failed_count = sum(
        row["schedule"] is not None and row["schedule"]["status"] == "failed" for row in rows
    )
    locked_count = sum(not row["schedule_ready"] for row in rows)
    return {
        "series": _series_payload(series_id),
        "episodes": [
            {
                "episode_id": str(episode_id),
                "episode_number": 1,
                "episode_title": "Set the executive frame",
                "episode_premise": "Open the narrative with an operating model decision.",
                "episode_status": EpisodeStatus.SCHEDULED.value
                if scheduled_count
                else EpisodeStatus.CAPTIONING.value,
                "full_episode_rows": rows,
                "short_clip_slots": [
                    {
                        "clip_suggestion": _clip_payload(series_id, episode_id),
                        "rows": [],
                        "scheduled_count": 0,
                        "published_count": 0,
                        "failed_count": 0,
                    }
                ],
                "eligible_count": 2,
                "scheduled_count": scheduled_count,
                "published_count": published_count,
                "failed_count": failed_count,
                "locked_count": locked_count,
            }
        ],
        "readiness": {
            "total_row_count": 3,
            "eligible_row_count": 2,
            "scheduled_row_count": scheduled_count,
            "published_row_count": published_count,
            "failed_row_count": failed_count,
            "locked_row_count": locked_count,
            "bulk_schedulable_count": 2 if first_schedule_status is None else 1,
            "warnings": ["1 uncaptioned row(s) remain locked."],
        },
        "bulk_result": bulk_result,
    }


class FakeScheduleService:
    async def get_workspace(self, series_id: UUID):
        return _workspace(series_id)

    async def create_schedule(self, series_id: UUID, payload):
        return _workspace(series_id, first_schedule_status=ScheduleStatus.SCHEDULED)

    async def bulk_schedule(self, series_id: UUID, payload):
        return _workspace(
            series_id,
            first_schedule_status=ScheduleStatus.SCHEDULED,
            bulk_result={
                "requested_count": 3,
                "scheduled_count": 2,
                "failed_count": 0,
                "skipped_count": 1,
            },
        )

    async def update_schedule(self, series_id: UUID, schedule_id: UUID, payload):
        return _workspace(series_id, first_schedule_status=ScheduleStatus.SCHEDULED)

    async def reschedule(self, series_id: UUID, schedule_id: UUID, payload):
        return _workspace(
            series_id,
            first_schedule_status=ScheduleStatus.SCHEDULED,
            retry_count=1,
        )

    async def cancel_schedule(self, series_id: UUID, schedule_id: UUID):
        return _workspace(series_id)

    async def sync_statuses(self, series_id: UUID):
        return _workspace(
            series_id,
            first_schedule_status=ScheduleStatus.PUBLISHED,
            live_url="https://buffer.example/posts/buf_live",
        )


class FakeLockedScheduleService(FakeScheduleService):
    async def get_workspace(self, series_id: UUID):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Generate at least one caption before scheduling",
        )


class FakeUncaptionedScheduleService(FakeScheduleService):
    async def create_schedule(self, series_id: UUID, payload):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only captioned rows can be scheduled",
        )


class FakeFailedScheduleService(FakeScheduleService):
    async def create_schedule(self, series_id: UUID, payload):
        return _workspace(
            series_id,
            first_schedule_status=ScheduleStatus.FAILED,
            failure_reason="Buffer rejected X copy above 280 characters.",
        )


def _client(service: object | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_schedule_service] = lambda: service or FakeScheduleService()
    return TestClient(app)


def test_schedule_workspace_requires_caption_gate() -> None:
    response = _client(FakeLockedScheduleService()).get(f"/api/v1/series/{uuid4()}/schedules")

    assert response.status_code == 409
    assert "caption" in response.text


def test_schedule_workspace_shows_platform_rows_and_locks_uncaptioned_rows() -> None:
    response = _client().get(f"/api/v1/series/{uuid4()}/schedules")

    assert response.status_code == 200
    body = response.json()
    rows = body["episodes"][0]["full_episode_rows"]
    assert len(rows) == 3
    assert rows[0]["can_create_schedule"] is True
    assert rows[1]["is_captioned"] is False
    assert "Only captioned" in rows[1]["schedule_locked_reason"]


def test_schedule_creation_rejects_uncaptioned_rows() -> None:
    response = _client(FakeUncaptionedScheduleService()).post(
        f"/api/v1/series/{uuid4()}/schedules",
        json={"caption_id": str(uuid4()), "scheduled_for": datetime.now(UTC).isoformat()},
    )

    assert response.status_code == 409
    assert "captioned" in response.text


def test_schedule_creation_persists_buffer_post_id() -> None:
    response = _client().post(
        f"/api/v1/series/{uuid4()}/schedules",
        json={"caption_id": str(uuid4()), "scheduled_for": datetime.now(UTC).isoformat()},
    )

    assert response.status_code == 200
    schedule = response.json()["episodes"][0]["full_episode_rows"][0]["schedule"]
    assert schedule["status"] == "scheduled"
    assert schedule["buffer_post_id"].startswith("buf_")


def test_bulk_schedule_returns_accurate_counts() -> None:
    response = _client().post(
        f"/api/v1/series/{uuid4()}/schedules/bulk",
        json={"scheduled_for": datetime.now(UTC).isoformat(), "spacing_minutes": 30},
    )

    assert response.status_code == 200
    assert response.json()["bulk_result"] == {
        "requested_count": 3,
        "scheduled_count": 2,
        "failed_count": 0,
        "skipped_count": 1,
    }


def test_edit_scheduled_post_returns_scheduled_row() -> None:
    response = _client().patch(
        f"/api/v1/series/{uuid4()}/schedules/{uuid4()}",
        json={"scheduled_caption_text": "Edited Buffer copy"},
    )

    assert response.status_code == 200
    schedule = response.json()["episodes"][0]["full_episode_rows"][0]["schedule"]
    assert schedule["status"] == "scheduled"


def test_reschedule_failed_post_clears_failure_and_counts_retry() -> None:
    response = _client().post(
        f"/api/v1/series/{uuid4()}/schedules/{uuid4()}/reschedule",
        json={"scheduled_for": datetime.now(UTC).isoformat()},
    )

    assert response.status_code == 200
    schedule = response.json()["episodes"][0]["full_episode_rows"][0]["schedule"]
    assert schedule["status"] == "scheduled"
    assert schedule["retry_count"] == 1


def test_cancel_scheduled_post_removes_buffer_queue_row() -> None:
    response = _client().post(f"/api/v1/series/{uuid4()}/schedules/{uuid4()}/cancel")

    assert response.status_code == 200
    row = response.json()["episodes"][0]["full_episode_rows"][0]
    assert row["schedule"] is None
    assert row["can_create_schedule"] is True


def test_status_sync_publishes_due_rows_with_live_link() -> None:
    response = _client().post(f"/api/v1/series/{uuid4()}/schedules/sync")

    assert response.status_code == 200
    schedule = response.json()["episodes"][0]["full_episode_rows"][0]["schedule"]
    assert schedule["status"] == "published"
    assert schedule["live_url"].startswith("https://buffer.example/posts/")


def test_failed_buffer_posts_show_reason_and_are_reschedulable() -> None:
    response = _client(FakeFailedScheduleService()).post(
        f"/api/v1/series/{uuid4()}/schedules",
        json={"caption_id": str(uuid4()), "scheduled_for": datetime.now(UTC).isoformat()},
    )

    assert response.status_code == 200
    row = response.json()["episodes"][0]["full_episode_rows"][0]
    assert row["schedule"]["status"] == "failed"
    assert row["schedule"]["failure_reason"] == "Buffer rejected X copy above 280 characters."
    assert row["can_reschedule"] is True
