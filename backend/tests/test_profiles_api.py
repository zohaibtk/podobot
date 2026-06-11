from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.api.v1.endpoints.profiles import get_profile_service
from app.db.types import ProfileKind
from app.main import create_app


def _profile_payload(
    kind: ProfileKind = ProfileKind.HOST,
    profile_id: UUID | None = None,
    name: str | None = None,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(profile_id or uuid4()),
        "name": name or ("Maya Chen" if kind == ProfileKind.HOST else "Avery Stone"),
        "role_title": "Executive host" if kind == ProfileKind.HOST else "Industry expert",
        "kind": kind.value,
        "archetype": "Calm operator" if kind == ProfileKind.HOST else "External expert",
        "bio": "Production-ready profile voice.",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }


class FakeProfileService:
    async def list_profiles(
        self,
        kind=None,
        search=None,
        archetype=None,
        include_inactive=False,
    ):
        items = [
            _profile_payload(ProfileKind.HOST),
            _profile_payload(ProfileKind.GUEST),
        ]
        if kind is not None:
            items = [item for item in items if item["kind"] == kind.value]
        return items

    async def get_profile(self, profile_id, expected_kind=None):
        profile = _profile_payload(profile_id=profile_id)
        if expected_kind is not None and profile["kind"] != expected_kind.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Profile must be a {expected_kind.value}",
            )
        return profile

    async def create_profile(self, payload):
        if payload.name == "Duplicate":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A profile with this name and kind already exists",
            )
        return _profile_payload(payload.kind, name=payload.name)

    async def update_profile(self, profile_id, payload):
        return _profile_payload(
            payload.kind or ProfileKind.HOST,
            profile_id=profile_id,
            name=payload.name or "Updated Profile",
        )

    async def deactivate_profile(self, profile_id):
        profile = _profile_payload(profile_id=profile_id)
        profile["is_active"] = False
        return profile

    async def recommendations(self, kind, search=None, limit=5):
        return [
            {
                "profile": _profile_payload(kind),
                "reason": "Matches the requested persona lane.",
                "confidence_score": 91,
            }
        ][:limit]

    @property
    def session(self):
        class Session:
            async def commit(self) -> None:
                return None

        return Session()


def _client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_profile_service] = lambda: FakeProfileService()
    return TestClient(app)


def test_profiles_can_be_searched_and_filtered() -> None:
    response = _client().get("/api/v1/profiles/search?q=maya&kind=host")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["kind"] == "host"
    assert body["items"][0]["bio"]


def test_profile_create_requires_required_fields() -> None:
    response = _client().post("/api/v1/profiles", json={"name": "Only name"})

    assert response.status_code == 422


def test_profile_create_returns_library_record() -> None:
    response = _client().post(
        "/api/v1/profiles",
        json={
            "name": "Nora Vale",
            "role_title": "Customer host",
            "kind": "host",
            "archetype": "Concise operator",
            "bio": "Keeps the conversation crisp.",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Nora Vale"
    assert body["kind"] == "host"


def test_profile_duplicate_name_and_kind_conflicts() -> None:
    response = _client().post(
        "/api/v1/profiles",
        json={
            "name": "Duplicate",
            "role_title": "Executive host",
            "kind": "host",
            "archetype": "Calm operator",
        },
    )

    assert response.status_code == 409


def test_profile_update_and_detail_routes() -> None:
    profile_id = uuid4()

    detail = _client().get(f"/api/v1/profiles/{profile_id}")
    update = _client().patch(
        f"/api/v1/profiles/{profile_id}",
        json={"name": "Updated Profile", "kind": "guest"},
    )

    assert detail.status_code == 200
    assert update.status_code == 200
    assert update.json()["kind"] == "guest"


def test_profile_delete_deactivates_profile() -> None:
    profile_id = uuid4()

    response = _client().delete(f"/api/v1/profiles/{profile_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(profile_id)
    assert response.json()["is_active"] is False


def test_profile_recommendations_return_chip_data() -> None:
    response = _client().get("/api/v1/profiles/recommendations?kind=guest&limit=3")

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["profile"]["kind"] == "guest"
    assert body["items"][0]["reason"]
    assert body["items"][0]["confidence_score"] == 91
