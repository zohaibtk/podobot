from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.outlines import get_outline_service
from app.db.types import (
    DiscoveryStatus,
    EpisodeOutlineStatus,
    OutlineVersionSource,
    SeriesStage,
    SeriesStatus,
)
from app.main import create_app
from app.modules.outlines.models import EpisodeOutline
from app.modules.outlines.service import OutlineService


def _series_payload(series_id: UUID) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(series_id),
        "name": "Executive AI Briefings",
        "audience": "Enterprise technology leaders",
        "description": "A series about operational AI adoption.",
        "guest_name": "Provided Guest",
        "status": SeriesStatus.IN_PRODUCTION.value,
        "discovery_status": DiscoveryStatus.COMPLETE.value,
        "current_stage": SeriesStage.OUTLINES.value,
        "episode_plan_generated_at": now,
        "plan_locked_at": now,
        "created_at": now,
        "updated_at": now,
    }


def _version_payload(
    series_id: UUID,
    outline_id: UUID,
    episode_id: UUID,
    number: int = 1,
    source: OutlineVersionSource = OutlineVersionSource.LOCK_GENERATED,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid4()),
        "outline_id": str(outline_id),
        "series_id": str(series_id),
        "episode_id": str(episode_id),
        "version_number": number,
        "title": "Generated outline: Set the executive frame",
        "outline_markdown": "## Narrative promise\n\n- Latest outline context.",
        "source": source.value,
        "created_at": now,
    }


def _workspace(
    series_id: UUID,
    *,
    status_value: EpisodeOutlineStatus = EpisodeOutlineStatus.GENERATED,
    version_count: int = 1,
    approved: bool = False,
    source: OutlineVersionSource = OutlineVersionSource.LOCK_GENERATED,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    outline_id = uuid4()
    episode_id = uuid4()
    versions = [
        _version_payload(series_id, outline_id, episode_id, number, source)
        for number in range(version_count, 0, -1)
    ]
    current_version_id = versions[0]["id"]
    approved_version_id = current_version_id if approved else None
    return {
        "series": _series_payload(series_id),
        "outlines": [
            {
                "id": str(outline_id),
                "series_id": str(series_id),
                "episode_id": str(episode_id),
                "title": "Generated outline: Set the executive frame",
                "outline_markdown": versions[0]["outline_markdown"],
                "status": status_value.value,
                "current_version_id": current_version_id,
                "approved_version_id": approved_version_id,
                "approved_at": now if approved else None,
                "created_at": now,
                "updated_at": now,
                "episode_number": 1,
                "episode_title": "Set the executive frame",
                "episode_premise": "Open the narrative with an operating model decision.",
                "version_count": version_count,
                "latest_version_number": version_count,
                "can_edit": True,
                "read_only_reason": None,
                "is_ready_for_brief": approved,
                "versions": versions,
            }
        ],
        "readiness": {
            "total_outline_count": 1,
            "approved_outline_count": 1 if approved else 0,
            "is_ready_for_briefs": approved,
            "warnings": []
            if approved
            else ["Every outline must be approved before Brief generation is ready."],
        },
    }


class FakeOutlineService:
    async def get_workspace(self, series_id: UUID):
        return _workspace(series_id)

    async def update_outline(self, series_id: UUID, outline_id: UUID, payload):
        return _workspace(
            series_id,
            status_value=EpisodeOutlineStatus.DRAFT,
            version_count=2,
            source=OutlineVersionSource.MANUAL_EDIT,
        )

    async def regenerate_outline(self, series_id: UUID, outline_id: UUID, payload=None):
        return _workspace(
            series_id,
            status_value=EpisodeOutlineStatus.GENERATED,
            version_count=2,
            source=OutlineVersionSource.REGENERATION,
        )

    async def approve_outline(self, series_id: UUID, outline_id: UUID):
        return _workspace(series_id, status_value=EpisodeOutlineStatus.APPROVED, approved=True)

    async def list_versions(self, series_id: UUID, outline_id: UUID, *, page=1, page_size=20):
        versions = _workspace(series_id)["outlines"][0]["versions"]
        return {
            "items": versions,
            "total": len(versions),
            "page": page,
            "page_size": page_size,
            "total_pages": 1,
            "has_next": False,
            "has_previous": False,
        }


class FakeUnlockedOutlineService(FakeOutlineService):
    async def get_workspace(self, series_id: UUID):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lock the episode plan before working on outlines",
        )


class FakeReadonlyOutlineService(FakeOutlineService):
    async def update_outline(self, series_id: UUID, outline_id: UUID, payload):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Outline is read-only because downstream dependencies already exist",
        )


class FakeInstructionOutlineService(FakeOutlineService):
    def __init__(self) -> None:
        self.received_instruction: str | None = None

    async def regenerate_outline(self, series_id: UUID, outline_id: UUID, payload=None):
        self.received_instruction = payload.instruction if payload else None
        return await super().regenerate_outline(series_id, outline_id, payload)


def _client(service: object | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_outline_service] = lambda: service or FakeOutlineService()
    return TestClient(app)


def test_outline_workspace_returns_latest_visible_outline_and_versions() -> None:
    response = _client().get(f"/api/v1/series/{uuid4()}/outlines")

    assert response.status_code == 200
    body = response.json()
    outline = body["outlines"][0]
    assert outline["status"] == "generated"
    assert outline["current_version_id"] == outline["versions"][0]["id"]
    assert outline["version_count"] == 1


def test_outline_workspace_requires_locked_plan() -> None:
    response = _client(FakeUnlockedOutlineService()).get(f"/api/v1/series/{uuid4()}/outlines")

    assert response.status_code == 409


def test_outline_update_requires_markdown() -> None:
    response = _client().patch(
        f"/api/v1/series/{uuid4()}/outlines/{uuid4()}",
        json={"title": "Edited outline"},
    )

    assert response.status_code == 422


def test_outline_manual_edit_creates_new_draft_version() -> None:
    response = _client().patch(
        f"/api/v1/series/{uuid4()}/outlines/{uuid4()}",
        json={"outline_markdown": "## Edited outline"},
    )

    assert response.status_code == 200
    outline = response.json()["outlines"][0]
    assert outline["status"] == "draft"
    assert outline["version_count"] == 2
    assert outline["versions"][0]["source"] == "manual_edit"


def test_outline_regeneration_creates_new_generated_version() -> None:
    response = _client().post(f"/api/v1/series/{uuid4()}/outlines/{uuid4()}/regenerate")

    assert response.status_code == 200
    outline = response.json()["outlines"][0]
    assert outline["status"] == "generated"
    assert outline["version_count"] == 2
    assert outline["versions"][0]["source"] == "regeneration"


def test_outline_regeneration_accepts_producer_instruction() -> None:
    service = FakeInstructionOutlineService()

    response = _client(service).post(
        f"/api/v1/series/{uuid4()}/outlines/{uuid4()}/regenerate",
        json={"instruction": "Make it more practical for the client success team."},
    )

    assert response.status_code == 200
    assert service.received_instruction == "Make it more practical for the client success team."


def test_outline_approval_marks_readiness_without_generating_briefs() -> None:
    response = _client().post(f"/api/v1/series/{uuid4()}/outlines/{uuid4()}/approve")

    assert response.status_code == 200
    body = response.json()
    outline = body["outlines"][0]
    assert outline["status"] == "approved"
    assert outline["approved_version_id"] == outline["current_version_id"]
    assert body["readiness"]["is_ready_for_briefs"] is True


def test_outline_readonly_state_blocks_edits_after_downstream_dependencies() -> None:
    response = _client(FakeReadonlyOutlineService()).patch(
        f"/api/v1/series/{uuid4()}/outlines/{uuid4()}",
        json={"outline_markdown": "## Edited outline"},
    )

    assert response.status_code == 409


def test_approved_outline_blocks_manual_edit_service_guard() -> None:
    service = OutlineService(cast(AsyncSession, object()))

    with pytest.raises(HTTPException) as exc:
        service._assert_outline_not_approved(
            EpisodeOutline(status=EpisodeOutlineStatus.APPROVED)
        )

    assert exc.value.status_code == 409
    assert "Approved outlines are read-only" in exc.value.detail
