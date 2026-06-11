from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.v1.endpoints.series import get_discovery_service
from app.db.types import (
    DiscoverySourceStatus,
    DiscoveryStatus,
    NarrativeStatus,
    SeriesStage,
    SeriesStatus,
)
from app.main import create_app


def _series_payload(series_id: UUID) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(series_id),
        "name": "Executive AI Briefings",
        "audience": "Enterprise technology leaders",
        "description": "A series about operational AI adoption.",
        "guest_name": None,
        "status": SeriesStatus.RESEARCHING.value,
        "discovery_status": DiscoveryStatus.RUNNING.value,
        "current_stage": SeriesStage.DISCOVERY.value,
        "created_at": now,
        "updated_at": now,
    }


def _ledger_payload(series_id: UUID) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    return [
        {
            "id": str(uuid4()),
            "series_id": str(series_id),
            "source_name": "Executive AI Index",
            "source_type": "research report",
            "source_url": "https://example.com/report",
            "status": DiscoverySourceStatus.COMPLETE.value,
            "signal_title": "AI pilots are becoming operating rhythms",
            "signal_summary": "Executives are asking for durable adoption patterns.",
            "confidence_score": 91,
            "sort_order": 1,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": str(uuid4()),
            "series_id": str(series_id),
            "source_name": "Workflow Radar",
            "source_type": "trend monitor",
            "source_url": "https://example.com/radar",
            "status": DiscoverySourceStatus.RUNNING.value,
            "signal_title": "Workflow automation demand is rising",
            "signal_summary": "Research is still gathering operational examples.",
            "confidence_score": 74,
            "sort_order": 2,
            "created_at": now,
            "updated_at": now,
        },
    ]


def _narrative_payload(series_id: UUID, selected: bool = False) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid4()),
        "series_id": str(series_id),
        "title": "From AI experiments to operating rhythm",
        "thesis": "The story is about moving from pilots to repeatable cadence.",
        "summary": "A practical direction for leaders who need ownership and adoption rituals.",
        "confidence_score": 88,
        "supporting_signals": [
            {
                "source_name": "Executive AI Index",
                "signal_title": "AI pilots are becoming operating rhythms",
                "confidence_score": 91,
            }
        ],
        "generation": 1,
        "status": NarrativeStatus.SELECTED.value if selected else NarrativeStatus.CANDIDATE.value,
        "is_selected": selected,
        "selected_at": now if selected else None,
        "created_at": now,
        "updated_at": now,
    }


class FakeDiscoveryService:
    async def get_workspace(self, series_id: UUID):
        narrative = _narrative_payload(series_id)
        return {
            "series": _series_payload(series_id),
            "progress_percent": 50,
            "ledger": _ledger_payload(series_id),
            "narratives": [narrative],
            "selected_narrative_id": None,
        }

    async def regenerate_narratives(self, series_id: UUID):
        return await self.get_workspace(series_id)

    async def run_discovery(self, series_id: UUID):
        return await self.get_workspace(series_id)

    async def select_narrative(self, series_id: UUID, narrative_id: UUID):
        narrative = _narrative_payload(series_id, selected=True)
        narrative["id"] = str(narrative_id)
        series = _series_payload(series_id)
        series["status"] = SeriesStatus.PLANNING.value
        series["current_stage"] = SeriesStage.PLAN.value
        series["discovery_status"] = DiscoveryStatus.COMPLETE.value
        return {
            "series": series,
            "progress_percent": 100,
            "ledger": _ledger_payload(series_id),
            "narratives": [narrative],
            "selected_narrative_id": str(narrative_id),
        }


def _client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_discovery_service] = lambda: FakeDiscoveryService()
    return TestClient(app)


def test_discovery_workspace_returns_ledger_and_narratives() -> None:
    response = _client().get(f"/api/v1/series/{uuid4()}/discovery")

    assert response.status_code == 200
    body = response.json()
    assert body["progress_percent"] == 50
    assert len(body["ledger"]) == 2
    assert body["narratives"][0]["supporting_signals"]


def test_select_narrative_unlocks_plan_stage() -> None:
    series_id = uuid4()
    narrative_id = uuid4()

    response = _client().post(f"/api/v1/series/{series_id}/narratives/{narrative_id}/select")

    assert response.status_code == 200
    body = response.json()
    assert body["selected_narrative_id"] == str(narrative_id)
    assert body["series"]["current_stage"] == "plan"
    assert body["series"]["status"] == "planning"


def test_regenerate_narratives_reuses_existing_workspace_contract() -> None:
    response = _client().post(f"/api/v1/series/{uuid4()}/narratives/regenerate")

    assert response.status_code == 200
    assert response.json()["ledger"][0]["source_name"] == "Executive AI Index"


def test_run_discovery_returns_workspace_contract() -> None:
    response = _client().post(f"/api/v1/series/{uuid4()}/discovery/run")

    assert response.status_code == 200
    body = response.json()
    assert body["ledger"][0]["source_name"] == "Executive AI Index"
    assert body["narratives"][0]["supporting_signals"]
