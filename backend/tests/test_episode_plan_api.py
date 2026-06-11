from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.api.v1.endpoints.episodes import get_episode_plan_service
from app.api.v1.endpoints.profiles import get_profile_service
from app.db.types import (
    DiscoveryStatus,
    EpisodeOutlineStatus,
    EpisodeStatus,
    ProfileKind,
    SeriesStage,
    SeriesStatus,
)
from app.main import create_app


def _series_payload(series_id: UUID, locked: bool = False) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(series_id),
        "name": "Executive AI Briefings",
        "audience": "Enterprise technology leaders",
        "description": "A series about operational AI adoption.",
        "guest_name": "Provided Guest",
        "status": SeriesStatus.IN_PRODUCTION.value if locked else SeriesStatus.PLANNING.value,
        "discovery_status": DiscoveryStatus.COMPLETE.value,
        "current_stage": SeriesStage.OUTLINES.value if locked else SeriesStage.PLAN.value,
        "episode_plan_generated_at": now,
        "plan_locked_at": now if locked else None,
        "created_at": now,
        "updated_at": now,
    }


def _episode_payload(
    series_id: UUID,
    episode_id: UUID | None = None,
    number: int = 1,
    missing: list[str] | None = None,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    missing_assignments = missing or []
    return {
        "id": str(episode_id or uuid4()),
        "series_id": str(series_id),
        "episode_number": number,
        "title": "Set the executive frame",
        "premise": "Open the narrative with an operating model decision.",
        "status": EpisodeStatus.PLANNED.value,
        "host_profile_id": str(uuid4()) if "host" not in missing_assignments else None,
        "guest_profile_id": None,
        "guest_name_override": None,
        "host_profile_name": None if "host" in missing_assignments else "Maya Chen",
        "guest_profile_name": None,
        "effective_host_name": None if "host" in missing_assignments else "Maya Chen",
        "effective_guest_name": None if "guest" in missing_assignments else "Provided Guest",
        "can_edit": True,
        "missing_assignments": missing_assignments,
        "created_at": now,
        "updated_at": now,
    }


def _workspace(
    series_id: UUID,
    locked: bool = False,
    missing: list[str] | None = None,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    episode = _episode_payload(series_id, missing=missing)
    return {
        "series": _series_payload(series_id, locked=locked),
        "episodes": [episode],
        "outlines": [
            {
                "id": str(uuid4()),
                "series_id": str(series_id),
                "episode_id": episode["id"],
                "title": "Outline placeholder: Set the executive frame",
                "outline_markdown": "## Narrative promise",
                "status": EpisodeOutlineStatus.GENERATED.value,
                "created_at": now,
                "updated_at": now,
            }
        ]
        if locked
        else [],
        "selected_narrative_id": str(uuid4()),
        "is_locked": locked,
        "lock_readiness": {
            "is_ready": not missing,
            "missing_episode_count": 1 if missing else 0,
            "missing_episode_ids": [episode["id"]] if missing else [],
            "warnings": ["1 episode(s) need a host profile"] if missing else [],
        },
    }


def _profile_payload(kind: ProfileKind) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid4()),
        "name": "Maya Chen" if kind == ProfileKind.HOST else "Avery Stone",
        "role_title": "Executive host" if kind == ProfileKind.HOST else "Industry expert",
        "kind": kind.value,
        "archetype": "Calm operator",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }


class FakeEpisodePlanService:
    async def get_plan(self, series_id: UUID):
        return _workspace(series_id)

    async def add_episode(self, series_id: UUID, payload):
        return _workspace(series_id)

    async def update_episode(self, series_id: UUID, episode_id: UUID, payload):
        return _workspace(series_id)

    async def generate_episode_draft(self, series_id: UUID, payload):
        return {
            "title": "Sharper executive frame",
            "premise": f"Generated from: {payload.instruction}",
        }

    async def remove_episode(self, series_id: UUID, episode_id: UUID):
        return _workspace(series_id)

    async def reorder_episodes(self, series_id: UUID, payload):
        if len(set(payload.episode_ids)) != len(payload.episode_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reorder payload must include every episode exactly once",
            )
        return _workspace(series_id)

    async def assign_profiles(self, series_id: UUID, episode_id: UUID, payload):
        if (
            payload.host_profile_id is not None
            and payload.guest_profile_id is not None
            and payload.host_profile_id == payload.guest_profile_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Host and guest must be different profiles",
            )
        return _workspace(series_id)

    async def lock_plan(self, series_id: UUID):
        return _workspace(series_id, locked=True)


class FakeBlockedEpisodePlanService(FakeEpisodePlanService):
    async def lock_plan(self, series_id: UUID):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Every episode requires an effective host and guest before lock",
        )


class FakeProfileService:
    async def list_profiles(
        self,
        kind=None,
        search=None,
        archetype=None,
        include_inactive=False,
    ):
        return [_profile_payload(ProfileKind.HOST), _profile_payload(ProfileKind.GUEST)]

    @property
    def session(self):
        class Session:
            async def commit(self) -> None:
                return None

        return Session()


def _client(service: object | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_episode_plan_service] = lambda: service or FakeEpisodePlanService()
    app.dependency_overrides[get_profile_service] = lambda: FakeProfileService()
    return TestClient(app)


def test_episode_plan_generates_board_contract() -> None:
    response = _client().get(f"/api/v1/series/{uuid4()}/episodes/plan")

    assert response.status_code == 200
    body = response.json()
    assert len(body["episodes"]) == 1
    assert body["lock_readiness"]["is_ready"] is True
    assert body["is_locked"] is False


def test_add_episode_requires_title_and_premise() -> None:
    response = _client().post(f"/api/v1/series/{uuid4()}/episodes", json={})

    assert response.status_code == 422


def test_episode_draft_generation_returns_title_and_premise() -> None:
    response = _client().post(
        f"/api/v1/series/{uuid4()}/episodes/draft",
        json={
            "instruction": "Make it more concrete for CEOs.",
            "current_title": "Set the executive frame",
            "current_premise": "Open the narrative with an operating model decision.",
        },
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Sharper executive frame"
    assert "Make it more concrete" in response.json()["premise"]


def test_assignment_rejects_same_host_and_guest_profile() -> None:
    profile_id = uuid4()
    response = _client().post(
        f"/api/v1/series/{uuid4()}/episodes/{uuid4()}/assign",
        json={"host_profile_id": str(profile_id), "guest_profile_id": str(profile_id)},
    )

    assert response.status_code == 400


def test_lock_plan_generates_outlines_and_unlocks_production() -> None:
    response = _client().post(f"/api/v1/series/{uuid4()}/episodes/lock")

    assert response.status_code == 200
    body = response.json()
    assert body["is_locked"] is True
    assert body["series"]["current_stage"] == "outlines"
    assert body["outlines"][0]["status"] == "generated"


def test_lock_plan_blocks_missing_assignments() -> None:
    response = _client(FakeBlockedEpisodePlanService()).post(
        f"/api/v1/series/{uuid4()}/episodes/lock"
    )

    assert response.status_code == 409


def test_profiles_endpoint_returns_assignment_options() -> None:
    response = _client().get("/api/v1/profiles")

    assert response.status_code == 200
    kinds = {item["kind"] for item in response.json()["items"]}
    assert kinds == {"host", "guest"}
