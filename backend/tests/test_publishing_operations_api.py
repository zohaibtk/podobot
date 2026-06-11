from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.publishing_operations import get_publishing_operations_service
from app.db.types import (
    BufferAccountStatus,
    BufferPostStatus,
    CaptionVideoKind,
    Platform,
    PublishingAuditStatus,
    ScheduleStatus,
)
from app.main import create_app
from app.modules.publishing_operations.service import (
    PublishingOperationsService,
    _latest_schedule_ordering,
)
from app.modules.schedules.buffer_service import BufferPostResult
from app.modules.schedules.models import BufferAccount, EpisodeVideoPlatformSchedule


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat()


def _channel() -> dict[str, object]:
    now = _iso()
    return {
        "id": str(uuid4()),
        "buffer_account_id": str(uuid4()),
        "buffer_channel_id": "buf-linkedin",
        "service": "linkedin",
        "name": "PodoBot LinkedIn",
        "display_name": "PodoBot LinkedIn",
        "avatar_url": None,
        "is_enabled": True,
        "is_queue_paused": False,
        "raw_payload": {},
        "last_synced_at": now,
        "created_at": now,
        "updated_at": now,
    }


def _audit(schedule_id: UUID | None = None) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "schedule_id": str(schedule_id) if schedule_id else None,
        "buffer_account_id": None,
        "buffer_channel_id": None,
        "action": "publishing.bulk.retry",
        "status": PublishingAuditStatus.SUCCEEDED.value,
        "idempotency_key": "idem",
        "request_payload": {},
        "response_payload": {},
        "error_message": None,
        "created_at": _iso(),
    }


def _queue_item(
    schedule_id: UUID | None = None,
    *,
    schedule_status: ScheduleStatus = ScheduleStatus.FAILED,
) -> dict[str, object]:
    item_id = schedule_id or uuid4()
    channel = _channel()
    return {
        "id": str(item_id),
        "series_id": str(uuid4()),
        "series_name": "Executive AI Briefings",
        "episode_id": str(uuid4()),
        "episode_number": 1,
        "episode_title": "Set the executive frame",
        "caption_id": str(uuid4()),
        "video_kind": CaptionVideoKind.FULL_EPISODE.value,
        "video_key": "full",
        "platform": Platform.LINKEDIN.value,
        "status": schedule_status.value,
        "buffer_status": (
            BufferPostStatus.FAILED.value
            if schedule_status == ScheduleStatus.FAILED
            else BufferPostStatus.QUEUED.value
        ),
        "buffer_post_id": "buf_post_123",
        "scheduled_for": _iso(_now() + timedelta(hours=2)),
        "scheduled_caption_text": "Publishing copy",
        "failure_reason": (
            "Buffer rejected the post." if schedule_status == ScheduleStatus.FAILED else None
        ),
        "live_url": None,
        "retry_count": 1,
        "next_retry_at": None,
        "last_synced_at": _iso(),
        "rate_limit_reset_at": None,
        "channel": channel,
        "latest_audit": _audit(item_id),
        "created_at": _iso(),
        "updated_at": _iso(),
    }


def _queue(schedule_id: UUID | None = None) -> dict[str, object]:
    return {
        "items": [_queue_item(schedule_id)],
        "total_count": 1,
        "filters": {"statuses": ["failed"], "platforms": [], "query": "", "limit": 100},
    }


def _analytics() -> dict[str, object]:
    return {
        "scheduled_count": 2,
        "published_count": 1,
        "failed_count": 1,
        "cancelled_count": 0,
        "retryable_count": 1,
        "active_channel_count": 1,
        "unhealthy_channel_count": 0,
        "audit_event_count": 3,
        "webhook_event_count": 1,
        "buffer_account_status": BufferAccountStatus.CONNECTED.value,
        "warnings": ["1 failed post(s) need recovery."],
    }


def _workspace(schedule_id: UUID | None = None) -> dict[str, object]:
    channel = _channel()
    audit = _audit(schedule_id)
    return {
        "analytics": _analytics(),
        "queue": _queue(schedule_id),
        "failed": _queue(schedule_id),
        "retry_center": _queue(schedule_id),
        "channel_health": [
            {
                "channel": channel,
                "mapped_platforms": [Platform.LINKEDIN.value],
                "scheduled_count": 2,
                "published_count": 1,
                "failed_count": 1,
                "health_status": "healthy",
                "warnings": [],
            }
        ],
        "timeline": [
            {
                "id": "audit:1",
                "event_type": "publishing.bulk.retry",
                "title": "Publishing Bulk Retry",
                "status": "succeeded",
                "description": "Publishing action recorded.",
                "occurred_at": _iso(),
                "schedule_id": str(schedule_id) if schedule_id else None,
                "series_id": str(uuid4()),
                "platform": Platform.LINKEDIN.value,
            }
        ],
        "activity_feed": [
            {
                "id": "audit:1",
                "event_type": "publishing.bulk.retry",
                "title": "Publishing Bulk Retry",
                "status": "succeeded",
                "description": "Publishing action recorded.",
                "occurred_at": _iso(),
                "schedule_id": str(schedule_id) if schedule_id else None,
                "series_id": str(uuid4()),
                "platform": Platform.LINKEDIN.value,
                "source": "audit",
            }
        ],
        "audit_logs": [audit],
        "webhooks": [],
        "buffer_account": {
            "id": str(uuid4()),
            "integration_id": str(uuid4()),
            "buffer_account_id": "buf-account",
            "organization_id": "buf-org",
            "name": "PodoBot Buffer",
            "status": BufferAccountStatus.CONNECTED.value,
            "scopes": ["posts:write"],
            "token_expires_at": None,
            "connected_at": _iso(),
            "last_synced_at": _iso(),
            "rate_limit": {},
            "created_at": _iso(),
            "updated_at": _iso(),
        },
    }


class FakePublishingOperationsService:
    def __init__(self) -> None:
        self.last_statuses = None
        self.last_platforms = None
        self.last_query = None

    async def workspace(self):
        return _workspace()

    async def analytics(self):
        return _analytics()

    async def queue_items(self, *, statuses=None, platforms=None, query=None, limit=100):
        self.last_statuses = statuses
        self.last_platforms = platforms
        self.last_query = query
        return _queue()

    async def audit_logs(self, *, limit=100):
        return [_audit()]

    async def retry_bulk(self, payload):
        schedule_id = payload.schedule_ids[0]
        return {
            "action": "retry",
            "requested_count": 1,
            "succeeded_count": 1,
            "failed_count": 0,
            "results": [
                {
                    "schedule_id": str(schedule_id),
                    "success": True,
                    "message": "Retry queued.",
                    "status": ScheduleStatus.SCHEDULED.value,
                }
            ],
            "workspace": _workspace(schedule_id),
        }

    async def sync_bulk(self, payload):
        schedule_id = payload.schedule_ids[0]
        return {
            "action": "sync",
            "requested_count": 1,
            "succeeded_count": 1,
            "failed_count": 0,
            "results": [
                {
                    "schedule_id": str(schedule_id),
                    "success": True,
                    "message": "Status synced.",
                    "status": ScheduleStatus.PUBLISHED.value,
                }
            ],
            "workspace": _workspace(schedule_id),
        }

    async def stop_bulk(self, payload):
        schedule_id = payload.schedule_ids[0]
        workspace = _workspace(schedule_id)
        workspace["queue"] = {
            "items": [],
            "total_count": 0,
            "filters": {"statuses": [], "platforms": [], "query": "", "limit": 100},
        }
        return {
            "action": "stop",
            "requested_count": 1,
            "succeeded_count": 1,
            "failed_count": 0,
            "results": [
                {
                    "schedule_id": str(schedule_id),
                    "success": True,
                    "message": "Publishing stopped and Buffer queue item removed.",
                    "status": None,
                }
            ],
            "workspace": workspace,
        }


def _client(service: FakePublishingOperationsService | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_publishing_operations_service] = lambda: (
        service or FakePublishingOperationsService()
    )
    return TestClient(app)


def test_publishing_workspace_returns_queue_health_and_activity() -> None:
    response = _client().get("/api/v1/publishing/workspace")

    assert response.status_code == 200
    body = response.json()
    assert body["analytics"]["failed_count"] == 1
    assert body["queue"]["items"][0]["failure_reason"] == "Buffer rejected the post."
    assert body["channel_health"][0]["health_status"] == "healthy"
    assert body["activity_feed"][0]["source"] == "audit"


def test_publishing_queue_accepts_search_and_filters() -> None:
    service = FakePublishingOperationsService()

    response = _client(service).get(
        "/api/v1/publishing/queue?status=failed&platform=linkedin&query=Executive"
    )

    assert response.status_code == 200
    assert service.last_statuses == [ScheduleStatus.FAILED]
    assert service.last_platforms == [Platform.LINKEDIN]
    assert service.last_query == "Executive"


def test_publishing_queue_orders_latest_records_first() -> None:
    order_by = [str(expression) for expression in _latest_schedule_ordering()]

    assert "scheduled_for DESC" in order_by[0]
    assert "created_at DESC" in order_by[1]
    assert "id DESC" in order_by[2]


class _PublishingSyncSession:
    def __init__(self) -> None:
        self.flushed = False
        self.committed = False
        self.added = []

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        self.flushed = True

    async def commit(self) -> None:
        self.committed = True


class _FakePublishingBuffer:
    def __init__(self) -> None:
        self.synced_count = 0

    async def sync_post(self, schedule, now):
        self.synced_count += 1
        return BufferPostResult(
            post_id=schedule.buffer_post_id,
            status=BufferPostStatus.FAILED,
            failure_reason="Buffer still reports this post as queued after the scheduled time.",
        )

    def apply_result(self, schedule, result, scheduled_for):
        schedule.buffer_post_id = result.post_id
        schedule.buffer_status = result.status
        schedule.status = ScheduleStatus.FAILED
        schedule.failure_reason = result.failure_reason
        schedule.live_url = result.live_url
        schedule.scheduled_for = scheduled_for


class _DuePublishingOperationsService(PublishingOperationsService):
    def __init__(self, session, schedules, development_published_schedules=None):
        super().__init__(session)
        self.buffer_service = _FakePublishingBuffer()
        self.schedules = schedules
        self.development_published_schedules = development_published_schedules or []
        self.due_lookup_count = 0
        self.refreshed_series_ids = []

    async def _due_schedules(self, now):
        self.due_lookup_count += 1
        return self.schedules

    async def _development_published_schedules(self):
        return self.development_published_schedules

    async def _refresh_series_publish_state(self, series_id):
        self.refreshed_series_ids.append(series_id)


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
        buffer_post_id="buf_overdue",
        scheduled_for=scheduled_for,
        scheduled_caption_text="Scheduled copy",
        retry_count=0,
    )


@pytest.mark.asyncio
async def test_publishing_operations_syncs_due_schedules_once_before_listing() -> None:
    schedule = _schedule_model(scheduled_for=datetime.now(UTC) - timedelta(minutes=9))
    session = _PublishingSyncSession()
    service = _DuePublishingOperationsService(session, [schedule])

    await service._sync_due_schedules()
    await service._sync_due_schedules()

    assert service.due_lookup_count == 1
    assert service.buffer_service.synced_count == 1
    assert schedule.status == ScheduleStatus.FAILED
    assert "queued after the scheduled time" in str(schedule.failure_reason)
    assert service.refreshed_series_ids == [schedule.series_id]
    assert session.flushed is True
    assert session.committed is True


@pytest.mark.asyncio
async def test_publishing_operations_reconciles_development_published_rows() -> None:
    schedule = _schedule_model(scheduled_for=datetime.now(UTC) - timedelta(minutes=30))
    schedule.status = ScheduleStatus.PUBLISHED
    schedule.buffer_status = BufferPostStatus.PUBLISHED
    schedule.live_url = f"https://buffer.com/app/posts/{schedule.buffer_post_id}"
    session = _PublishingSyncSession()
    service = _DuePublishingOperationsService(session, [], [schedule])

    await service._sync_due_schedules()

    assert schedule.status == ScheduleStatus.FAILED
    assert schedule.buffer_status == BufferPostStatus.FAILED
    assert schedule.live_url is None
    assert "development mode does not publish" in str(schedule.failure_reason)
    assert service.refreshed_series_ids == [schedule.series_id]
    assert session.added
    assert session.committed is True


class _QueueSyncPublishingOperationsService(PublishingOperationsService):
    def __init__(self):
        super().__init__(_PublishingSyncSession())  # type: ignore[arg-type]
        self.sync_count = 0

    async def _sync_due_schedules(self):
        self.sync_count += 1

    async def _schedule_rows(self, **kwargs):
        return []

    async def _schedule_count(self, **kwargs):
        return 0

    async def _latest_audits_by_schedule(self, schedule_ids):
        return {}


@pytest.mark.asyncio
async def test_publishing_queue_triggers_due_sync_before_returning_rows() -> None:
    service = _QueueSyncPublishingOperationsService()

    response = await service.queue_items()

    assert service.sync_count == 1
    assert response["items"] == []


def test_publishing_warnings_explain_development_buffer_connector() -> None:
    service = PublishingOperationsService(_PublishingSyncSession())  # type: ignore[arg-type]
    account = BufferAccount(
        id=uuid4(),
        name="PodoBot Buffer",
        status=BufferAccountStatus.CONNECTED,
        access_token_secret="dev-buffer-access-token",
        scopes=[],
        rate_limit={},
    )

    warnings = service._warnings(account, [], [], Counter())

    assert any("development mode" in warning for warning in warnings)


def test_publishing_audits_endpoint_returns_audit_logs() -> None:
    response = _client().get("/api/v1/publishing/audits")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["action"] == "publishing.bulk.retry"
    assert payload["has_next"] is False


def test_bulk_retry_returns_validated_action_result() -> None:
    schedule_id = uuid4()

    response = _client().post(
        "/api/v1/publishing/bulk/retry",
        json={"schedule_ids": [str(schedule_id)]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "retry"
    assert body["succeeded_count"] == 1
    assert body["results"][0]["schedule_id"] == str(schedule_id)


def test_bulk_stop_returns_validated_action_result() -> None:
    schedule_id = uuid4()

    response = _client().post(
        "/api/v1/publishing/bulk/stop",
        json={"schedule_ids": [str(schedule_id)]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "stop"
    assert body["succeeded_count"] == 1
    assert body["results"][0]["schedule_id"] == str(schedule_id)
    assert body["results"][0]["status"] is None
