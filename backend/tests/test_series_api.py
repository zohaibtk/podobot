from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.v1.endpoints.series import get_series_service
from app.db.types import DiscoveryStatus, SeriesStage, SeriesStatus
from app.main import create_app
from app.schemas.pagination import offset_meta


def _series_payload(series_id: UUID | None = None) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(series_id or uuid4()),
        "name": "Executive AI Briefings",
        "audience": "Enterprise technology leaders",
        "description": "A sharp series about operational AI adoption.",
        "guest_name": None,
        "status": SeriesStatus.RESEARCHING.value,
        "discovery_status": DiscoveryStatus.RUNNING.value,
        "current_stage": SeriesStage.DISCOVERY.value,
        "created_at": now,
        "updated_at": now,
    }


class FakeSeriesService:
    last_list_kwargs = None

    async def list_series(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status_filter: SeriesStatus | None = None,
        sort: str = "-created_at",
    ):
        FakeSeriesService.last_list_kwargs = {
            "page": page,
            "page_size": page_size,
            "search": search,
            "status_filter": status_filter,
            "sort": sort,
        }
        items = [_series_payload()]
        return {
            "items": items,
            **offset_meta(total=len(items), page=page, page_size=page_size),
        }

    async def create_series(self, payload):
        return {
            **_series_payload(),
            **payload.model_dump(),
            "status": SeriesStatus.RESEARCHING.value,
            "discovery_status": DiscoveryStatus.RUNNING.value,
            "current_stage": SeriesStage.DISCOVERY.value,
        }

    async def get_series(self, series_id: UUID):
        return _series_payload(series_id)

    async def update_series(self, series_id: UUID, payload):
        return {
            **_series_payload(series_id),
            **payload.model_dump(exclude_unset=True),
        }

    async def delete_series(self, series_id: UUID) -> None:
        return None


def _client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_series_service] = lambda: FakeSeriesService()
    return TestClient(app)


def test_create_series_requires_core_fields() -> None:
    response = _client().post("/api/v1/series", json={})

    assert response.status_code == 422


def test_create_series_forbids_removed_setup_fields() -> None:
    response = _client().post(
        "/api/v1/series",
        json={
            "name": "AI Briefings",
            "audience": "CIOs",
            "description": "Weekly executive conversations.",
            "duration": "30 minutes",
            "tone": "formal",
            "format": "interview",
            "citation_density": "high",
            "keywords": ["AI"],
        },
    )

    assert response.status_code == 422


def test_create_series_returns_running_discovery_state() -> None:
    response = _client().post(
        "/api/v1/series",
        json={
            "name": "AI Briefings",
            "audience": "CIOs",
            "description": "Weekly executive conversations.",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "researching"
    assert body["discovery_status"] == "running"
    assert body["current_stage"] == "discovery"


def test_list_series_returns_items() -> None:
    response = _client().get("/api/v1/series")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_list_series_defaults_to_latest_created_first() -> None:
    FakeSeriesService.last_list_kwargs = None

    response = _client().get("/api/v1/series")

    assert response.status_code == 200
    assert FakeSeriesService.last_list_kwargs is not None
    assert FakeSeriesService.last_list_kwargs["sort"] == "-created_at"
