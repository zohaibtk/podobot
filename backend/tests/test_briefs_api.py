from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.api.v1.endpoints.briefs import get_brief_service
from app.db.types import (
    BriefKind,
    BriefStatus,
    BriefVersionSource,
    DiscoveryStatus,
    EpisodeOutlineStatus,
    EpisodeStatus,
    SeriesStage,
    SeriesStatus,
)
from app.main import create_app


def _series_payload(series_id: UUID, recordings_unlocked: bool = False) -> dict[str, object]:
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
            SeriesStage.RECORDINGS.value if recordings_unlocked else SeriesStage.BRIEFS.value
        ),
        "episode_plan_generated_at": now,
        "plan_locked_at": now,
        "briefs_approved_at": now if recordings_unlocked else None,
        "created_at": now,
        "updated_at": now,
    }


def _version_payload(
    series_id: UUID,
    brief_id: UUID,
    episode_id: UUID,
    number: int = 1,
    source: BriefVersionSource = BriefVersionSource.GENERATION,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid4()),
        "brief_id": str(brief_id),
        "series_id": str(series_id),
        "episode_id": str(episode_id),
        "outline_id": str(uuid4()),
        "outline_version_id": str(uuid4()),
        "version_number": number,
        "title": "Generated host brief: Set the executive frame for Maya Chen",
        "brief_markdown": "## Host Brief\n\n- Uses latest approved outline.",
        "source": source.value,
        "created_at": now,
    }


def _brief_payload(
    series_id: UUID,
    episode_id: UUID,
    kind: BriefKind,
    status_value: BriefStatus = BriefStatus.GENERATED,
    version_count: int = 1,
    source: BriefVersionSource = BriefVersionSource.GENERATION,
    invalidated: bool = False,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    brief_id = uuid4()
    versions = [
        _version_payload(series_id, brief_id, episode_id, number, source)
        for number in range(version_count, 0, -1)
    ]
    current_version_id = versions[0]["id"]
    return {
        "id": str(brief_id),
        "series_id": str(series_id),
        "episode_id": str(episode_id),
        "kind": kind.value,
        "title": f"Generated {kind.value} brief: Set the executive frame",
        "brief_markdown": versions[0]["brief_markdown"],
        "status": status_value.value,
        "current_version_id": current_version_id,
        "approved_version_id": current_version_id if status_value == BriefStatus.APPROVED else None,
        "approved_at": now if status_value == BriefStatus.APPROVED else None,
        "approval_invalidated_at": now if invalidated else None,
        "created_at": now,
        "updated_at": now,
        "profile_id": str(uuid4()),
        "profile_name": "Maya Chen" if kind == BriefKind.HOST else "Avery Stone",
        "profile_role_title": "Executive host" if kind == BriefKind.HOST else "Industry expert",
        "version_count": version_count,
        "latest_version_number": version_count,
        "can_edit": True,
        "read_only_reason": None,
        "versions": versions,
    }


def _workspace(
    series_id: UUID,
    *,
    generated: bool = True,
    approved: bool = False,
    invalidated: bool = False,
    source: BriefVersionSource = BriefVersionSource.GENERATION,
    version_count: int = 1,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    episode_id = uuid4()
    host_status = BriefStatus.APPROVED if approved else BriefStatus.GENERATED
    guest_status = BriefStatus.APPROVED if approved else BriefStatus.GENERATED
    if invalidated:
        host_status = BriefStatus.DRAFT
    host_brief = (
        _brief_payload(
            series_id,
            episode_id,
            BriefKind.HOST,
            host_status,
            version_count,
            source,
            invalidated,
        )
        if generated
        else None
    )
    guest_brief = (
        _brief_payload(
            series_id,
            episode_id,
            BriefKind.GUEST,
            guest_status,
            1,
            BriefVersionSource.GENERATION,
            invalidated,
        )
        if generated
        else None
    )
    return {
        "series": _series_payload(series_id, recordings_unlocked=approved),
        "episodes": [
            {
                "episode_id": str(episode_id),
                "episode_number": 1,
                "episode_title": "Set the executive frame",
                "episode_premise": "Open the narrative with an operating model decision.",
                "episode_status": (
                    EpisodeStatus.APPROVED.value if approved else EpisodeStatus.BRIEF_READY.value
                ),
                "requirement": {
                    "episode_id": str(episode_id),
                    "episode_number": 1,
                    "episode_title": "Set the executive frame",
                    "host_profile_id": str(uuid4()),
                    "host_profile_name": "Maya Chen",
                    "guest_profile_id": str(uuid4()),
                    "guest_profile_name": "Avery Stone",
                    "outline_id": str(uuid4()),
                    "outline_status": EpisodeOutlineStatus.APPROVED.value,
                    "outline_current_version_id": str(uuid4()),
                    "missing_requirements": [],
                    "can_generate": True,
                },
                "host_brief": host_brief,
                "guest_brief": guest_brief,
                "pair_generated": generated,
                "pair_approved": approved,
                "pair_approved_at": now if approved else None,
                "approval_invalidated_at": now if invalidated else None,
            }
        ],
        "readiness": {
            "total_episode_count": 1,
            "generated_episode_count": 1 if generated else 0,
            "approved_episode_count": 1 if approved else 0,
            "recordings_unlocked": approved,
            "warnings": []
            if approved
            else ["Approve one host/guest brief pair to unlock Recordings."],
        },
    }


class FakeBriefService:
    async def get_workspace(self, series_id: UUID):
        return _workspace(series_id, generated=False)

    async def generate_pair(self, series_id: UUID, episode_id: UUID):
        return _workspace(series_id)

    async def update_brief(self, series_id: UUID, brief_id: UUID, payload):
        return _workspace(
            series_id,
            invalidated=True,
            source=BriefVersionSource.MANUAL_EDIT,
            version_count=2,
        )

    async def regenerate_brief(self, series_id: UUID, brief_id: UUID):
        return _workspace(
            series_id,
            invalidated=True,
            source=BriefVersionSource.REGENERATION,
            version_count=2,
        )

    async def approve_pair(self, series_id: UUID, episode_id: UUID):
        return _workspace(series_id, approved=True)

    async def download_brief(self, series_id: UUID, brief_id: UUID):
        return "episode-1-host-brief-v1.md", "## Host Brief\n\n- Downloadable markdown."


class FakeUnlockedBriefService(FakeBriefService):
    async def get_workspace(self, series_id: UUID):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lock the episode plan before working on briefs",
        )


class FakeMissingRequirementsBriefService(FakeBriefService):
    async def generate_pair(self, series_id: UUID, episode_id: UUID):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Brief generation blocked: guest profile, outline approval",
        )


def _client(service: object | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_brief_service] = lambda: service or FakeBriefService()
    return TestClient(app)


def test_brief_workspace_requires_locked_plan() -> None:
    response = _client(FakeUnlockedBriefService()).get(f"/api/v1/series/{uuid4()}/briefs")

    assert response.status_code == 409


def test_brief_workspace_starts_without_auto_generation() -> None:
    response = _client().get(f"/api/v1/series/{uuid4()}/briefs")

    assert response.status_code == 200
    episode = response.json()["episodes"][0]
    assert episode["pair_generated"] is False
    assert episode["host_brief"] is None
    assert episode["guest_brief"] is None


def test_brief_generation_blocks_missing_profile_or_outline_requirements() -> None:
    response = _client(FakeMissingRequirementsBriefService()).post(
        f"/api/v1/series/{uuid4()}/briefs/episodes/{uuid4()}/generate"
    )

    assert response.status_code == 409
    assert "guest profile" in response.text


def test_brief_generation_creates_separate_host_and_guest_documents() -> None:
    response = _client().post(f"/api/v1/series/{uuid4()}/briefs/episodes/{uuid4()}/generate")

    assert response.status_code == 200
    episode = response.json()["episodes"][0]
    assert episode["pair_generated"] is True
    assert episode["host_brief"]["kind"] == "host"
    assert episode["guest_brief"]["kind"] == "guest"
    assert episode["host_brief"]["status"] == "generated"


def test_pair_approval_unlocks_recordings_gate() -> None:
    response = _client().post(f"/api/v1/series/{uuid4()}/briefs/episodes/{uuid4()}/approve")

    assert response.status_code == 200
    body = response.json()
    assert body["episodes"][0]["pair_approved"] is True
    assert body["readiness"]["recordings_unlocked"] is True
    assert body["series"]["current_stage"] == "recordings"


def test_editing_brief_invalidates_pair_approval() -> None:
    response = _client().patch(
        f"/api/v1/series/{uuid4()}/briefs/{uuid4()}",
        json={"brief_markdown": "## Edited Host Brief"},
    )

    assert response.status_code == 200
    episode = response.json()["episodes"][0]
    assert episode["pair_approved"] is False
    assert episode["approval_invalidated_at"] is not None
    assert episode["host_brief"]["status"] == "draft"
    assert episode["host_brief"]["versions"][0]["source"] == "manual_edit"


def test_regenerating_brief_invalidates_pair_approval_and_versions() -> None:
    response = _client().post(f"/api/v1/series/{uuid4()}/briefs/{uuid4()}/regenerate")

    assert response.status_code == 200
    episode = response.json()["episodes"][0]
    assert episode["pair_approved"] is False
    assert episode["approval_invalidated_at"] is not None
    assert episode["host_brief"]["latest_version_number"] == 2
    assert episode["host_brief"]["versions"][0]["source"] == "regeneration"


def test_brief_update_requires_markdown() -> None:
    response = _client().patch(
        f"/api/v1/series/{uuid4()}/briefs/{uuid4()}",
        json={"title": "Edited brief"},
    )

    assert response.status_code == 422


def test_brief_download_returns_markdown_attachment() -> None:
    response = _client().get(f"/api/v1/series/{uuid4()}/briefs/{uuid4()}/download")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "episode-1-host-brief-v1.md" in response.headers["content-disposition"]
    assert "Host Brief" in response.text
