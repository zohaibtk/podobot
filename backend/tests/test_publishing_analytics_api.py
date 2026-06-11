from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.endpoints.publishing_analytics import get_publishing_analytics_service
from app.db.types import (
    BufferPostStatus,
    CaptionVideoKind,
    Platform,
    PublishingAuditStatus,
)
from app.main import create_app


def _iso() -> str:
    return datetime.now(UTC).isoformat()


def _audit_payload() -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "schedule_id": str(uuid4()),
        "buffer_account_id": None,
        "buffer_channel_id": None,
        "action": "publishing.create_post",
        "status": PublishingAuditStatus.SUCCEEDED.value,
        "idempotency_key": "idem",
        "request_payload": {},
        "response_payload": {"buffer_status": BufferPostStatus.PUBLISHED.value},
        "error_message": None,
        "created_at": _iso(),
    }


def _workspace() -> dict[str, object]:
    series_id = uuid4()
    episode_id = uuid4()
    channel_id = uuid4()
    return {
        "generated_at": _iso(),
        "filters": {
            "date_from": None,
            "date_to": None,
            "platforms": [Platform.LINKEDIN.value],
            "video_kinds": [CaptionVideoKind.FULL_EPISODE.value],
        },
        "success_metrics": {
            "total_rows": 4,
            "scheduled_count": 1,
            "published_count": 2,
            "failed_count": 1,
            "cancelled_count": 0,
            "retry_count": 1,
            "success_rate": 66.67,
            "failure_rate": 33.33,
            "average_retry_count": 0.25,
            "audit_event_count": 3,
            "webhook_event_count": 1,
        },
        "channel_performance": [
            {
                "channel_id": str(channel_id),
                "channel_name": "PodoBot LinkedIn",
                "platform": Platform.LINKEDIN.value,
                "scheduled_count": 1,
                "published_count": 2,
                "failed_count": 1,
                "cancelled_count": 0,
                "success_rate": 66.67,
                "failure_rate": 33.33,
                "retry_count": 1,
                "is_enabled": True,
                "is_queue_paused": False,
                "health_status": "degraded",
            }
        ],
        "content_performance": [
            {
                "series_id": str(series_id),
                "series_name": "Executive AI Briefings",
                "episode_id": str(episode_id),
                "episode_title": "Set the executive frame",
                "episode_number": 1,
                "video_kind": CaptionVideoKind.FULL_EPISODE.value,
                "platforms": [Platform.LINKEDIN.value],
                "scheduled_count": 1,
                "published_count": 2,
                "failed_count": 1,
                "success_rate": 66.67,
                "average_caption_characters": 180,
                "average_caption_generations": 1.5,
                "trend_score": 58.0,
            }
        ],
        "failure_metrics": [
            {
                "reason": "Buffer rejected the post.",
                "count": 1,
                "platforms": [Platform.LINKEDIN.value],
                "latest_at": _iso(),
            }
        ],
        "best_times": [
            {
                "day_of_week": "Monday",
                "hour": 9,
                "scheduled_count": 2,
                "published_count": 2,
                "failed_count": 0,
                "success_rate": 100.0,
            }
        ],
        "caption_effectiveness": [
            {
                "bucket": "standard",
                "label": "Standard captions",
                "scheduled_count": 3,
                "published_count": 2,
                "failed_count": 1,
                "success_rate": 66.67,
                "average_generation_count": 1.3,
            }
        ],
        "trends": [
            {
                "period": "2026-W23",
                "scheduled_count": 4,
                "published_count": 2,
                "failed_count": 1,
                "success_rate": 66.67,
            }
        ],
        "executive_insights": [
            {
                "severity": "warning",
                "title": "Top failure reason",
                "summary": "Buffer rejected the post affected 1 row.",
            }
        ],
        "audit_events": [_audit_payload()],
    }


class FakePublishingAnalyticsService:
    def __init__(self) -> None:
        self.filters = None
        self.limit = None
        self.page = None
        self.page_size = None

    async def workspace(self, filters):
        self.filters = filters
        return _workspace()

    async def channels(self, filters):
        self.filters = filters
        return _workspace()["channel_performance"]

    async def content(self, filters):
        self.filters = filters
        return _workspace()["content_performance"]

    async def executive_report(self, filters):
        self.filters = filters
        workspace = _workspace()
        return {
            "generated_at": workspace["generated_at"],
            "filters": workspace["filters"],
            "success_metrics": workspace["success_metrics"],
            "top_channels": workspace["channel_performance"],
            "top_content": workspace["content_performance"],
            "best_times": workspace["best_times"],
            "executive_insights": workspace["executive_insights"],
            "audit_events": workspace["audit_events"],
        }

    async def audit_events(self, *, filters, limit=100):
        self.filters = filters
        self.limit = limit
        return [_audit_payload()]

    async def audit_events_page(self, *, filters, page=1, page_size=20):
        self.filters = filters
        self.page = page
        self.page_size = page_size
        return {
            "items": [_audit_payload()],
            "total": 1,
            "page": page,
            "page_size": page_size,
            "total_pages": 1,
            "has_next": False,
            "has_previous": False,
        }


def _client(service: FakePublishingAnalyticsService | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_publishing_analytics_service] = lambda: (
        service or FakePublishingAnalyticsService()
    )
    return TestClient(app)


def test_publishing_analytics_workspace_returns_intelligence_sections() -> None:
    response = _client().get("/api/v1/publishing-analytics/workspace")

    assert response.status_code == 200
    body = response.json()
    assert body["success_metrics"]["published_count"] == 2
    assert body["channel_performance"][0]["channel_name"] == "PodoBot LinkedIn"
    assert body["content_performance"][0]["trend_score"] == 58.0
    assert body["audit_events"][0]["action"] == "publishing.create_post"


def test_publishing_analytics_filters_are_passed_to_service() -> None:
    service = FakePublishingAnalyticsService()

    response = _client(service).get(
        "/api/v1/publishing-analytics/channels?platform=linkedin&video_kind=full_episode"
    )

    assert response.status_code == 200
    assert service.filters.platforms == [Platform.LINKEDIN]
    assert service.filters.video_kinds == [CaptionVideoKind.FULL_EPISODE]
    assert response.json()["items"][0]["channel_name"] == "PodoBot LinkedIn"


def test_publishing_analytics_audit_events_are_paginated() -> None:
    service = FakePublishingAnalyticsService()

    response = _client(service).get("/api/v1/publishing-analytics/audit-events?page=2&page_size=25")

    assert response.status_code == 200
    assert service.page == 2
    assert service.page_size == 25
    assert response.json()["items"][0]["status"] == PublishingAuditStatus.SUCCEEDED.value
