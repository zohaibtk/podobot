from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.api.v1.endpoints.strategy import get_strategy_service
from app.db.types import (
    AgentRunStatus,
    DiscoveryStatus,
    SeriesStage,
    SeriesStatus,
    StrategyIdeaStatus,
)
from app.main import create_app


def _series_payload(series_id: UUID) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(series_id),
        "name": "AI governance rituals for operating teams",
        "audience": "COOs, CIOs, and transformation leaders",
        "description": "A practical series on AI governance cadence.",
        "guest_name": "Avery Stone",
        "status": SeriesStatus.PLANNING.value,
        "discovery_status": DiscoveryStatus.COMPLETE.value,
        "current_stage": SeriesStage.PLAN.value,
        "episode_plan_generated_at": now,
        "plan_locked_at": None,
        "briefs_approved_at": None,
        "captions_unlocked_at": None,
        "scheduling_unlocked_at": None,
        "created_at": now,
        "updated_at": now,
    }


def _run_payload(run_id: UUID, run_date: date) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(run_id),
        "run_date": run_date.isoformat(),
        "topic": "Executive AI operating model scan",
        "status": AgentRunStatus.SUCCEEDED.value,
        "started_at": now,
        "completed_at": now,
        "idea_count": 2,
        "created_at": now,
        "updated_at": now,
    }


def _idea_payload(
    run_id: UUID,
    *,
    idea_id: UUID | None = None,
    status_value: StrategyIdeaStatus = StrategyIdeaStatus.PROPOSED,
    converted_series_id: UUID | None = None,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    run_date = date.today()
    return {
        "id": str(idea_id or uuid4()),
        "run_id": str(run_id),
        "title": "AI governance rituals for operating teams",
        "audience": "COOs, CIOs, and transformation leaders",
        "description": "A practical series on AI governance cadence.",
        "proposed_guest_name": "Avery Stone",
        "thesis": "AI governance needs operating rhythm.",
        "rationale": "The proposal connects executive ownership, proof, and risk.",
        "evidence_signals": [
            {
                "source_name": "Operating model research",
                "signal_title": "AI accountability is moving into line teams",
                "confidence_score": 92,
            }
        ],
        "source_proposal": {
            "proposal_title": "AI governance rituals for operating teams",
            "opportunity_intelligence": {
                "sources_found": 4,
                "sources_used": 3,
                "signals_extracted": 3,
            },
            "episode_plan": [
                {
                    "title": "Governance as an operating rhythm",
                    "premise": "Move from policy to weekly decisions.",
                }
            ],
        },
        "confidence_score": 91,
        "opportunity_score": 88,
        "opportunity_score_breakdown": {
            "research_confidence": 91,
            "source_coverage": 85,
            "trend_strength": 82,
            "audience_fit": 90,
            "content_depth": 86,
            "competition_signal": 74,
            "formula": (
                "research_confidence * 0.25 + source_coverage * 0.20 + "
                "trend_strength * 0.20 + audience_fit * 0.15 + "
                "content_depth * 0.10 + competition_signal * 0.10"
            ),
        },
        "opportunity_score_explanation": (
            "Opportunity score 88 = Research confidence 91 x 25% + Source coverage 85 x 20% "
            "+ Trend strength 82 x 20% + Audience fit 90 x 15% + Content depth 86 x 10% "
            "+ Competition signal 74 x 10%."
        ),
        "audience_intelligence": {
            "audience": "COOs, CIOs, and transformation leaders",
            "source_mix": [
                {"label": "Enterprise research", "percentage": 62, "count": 3},
                {"label": "Operator communities", "percentage": 38, "count": 2},
            ],
            "reason": "Enterprise research and operator communities show the strongest fit.",
            "fit_score": 90,
        },
        "lifecycle_stage": "hot",
        "season_potential": {
            "potential_episodes": 4,
            "reason": "4 episode paths identified from governance themes.",
            "research_coverage": {
                "source_count": 3,
                "document_count": 4,
                "signals_extracted": 3,
            },
            "theme_count": 4,
            "themes": ["governance", "operating rhythm", "risk"],
        },
        "trend_intelligence": {
            "trend_available": True,
            "trend_source": "pytrends",
            "current_trend": 82,
            "previous_trend": 64,
            "trend_velocity": 18,
            "velocity_label": "Growing",
        },
        "source_count": 3,
        "potential_episode_count": 4,
        "theme_count": 4,
        "generated_at": now,
        "status": status_value.value,
        "reviewed_at": now if status_value != StrategyIdeaStatus.PROPOSED else None,
        "dismissed_at": now if status_value == StrategyIdeaStatus.DISMISSED else None,
        "converted_at": now if status_value == StrategyIdeaStatus.CONVERTED else None,
        "converted_series_id": str(converted_series_id) if converted_series_id else None,
        "run_date": run_date.isoformat(),
        "run_topic": "Executive AI operating model scan",
        "created_at": now,
        "updated_at": now,
    }


def _workspace(
    *,
    status_value: StrategyIdeaStatus = StrategyIdeaStatus.PROPOSED,
    converted_series_id: UUID | None = None,
) -> dict[str, object]:
    run_id = uuid4()
    run_date = date.today()
    idea = _idea_payload(
        run_id,
        status_value=status_value,
        converted_series_id=converted_series_id,
    )
    return {
        "runs": [_run_payload(run_id, run_date)],
        "groups": [
            {
                "run_id": str(run_id),
                "run_date": run_date.isoformat(),
                "run_topic": "Executive AI operating model scan",
                "status": status_value.value,
                "ideas": [idea],
            }
        ],
        "summary": {
            "run_count": 1,
            "proposed_count": 1 if status_value == StrategyIdeaStatus.PROPOSED else 0,
            "in_review_count": 1 if status_value == StrategyIdeaStatus.IN_REVIEW else 0,
            "dismissed_count": 1 if status_value == StrategyIdeaStatus.DISMISSED else 0,
            "converted_count": 1 if status_value == StrategyIdeaStatus.CONVERTED else 0,
            "new_opportunities_count": 1
            if status_value in {StrategyIdeaStatus.PROPOSED, StrategyIdeaStatus.IN_REVIEW}
            else 0,
            "high_confidence_count": 1,
            "hot_trends_count": 1,
            "converted_this_month_count": 1
            if status_value == StrategyIdeaStatus.CONVERTED
            else 0,
            "average_opportunity_score": 88,
        },
    }


class FakeStrategyService:
    async def get_workspace(self):
        return _workspace()

    async def create_research_run(self):
        return _workspace()

    async def review_idea(self, idea_id: UUID):
        workspace = _workspace(status_value=StrategyIdeaStatus.IN_REVIEW)
        return {"workspace": workspace, "idea": workspace["groups"][0]["ideas"][0]}

    async def dismiss_idea(self, idea_id: UUID):
        workspace = _workspace(status_value=StrategyIdeaStatus.DISMISSED)
        return {"workspace": workspace, "idea": workspace["groups"][0]["ideas"][0]}

    async def restore_idea(self, idea_id: UUID):
        workspace = _workspace(status_value=StrategyIdeaStatus.IN_REVIEW)
        return {"workspace": workspace, "idea": workspace["groups"][0]["ideas"][0]}

    async def convert_idea(self, idea_id: UUID):
        series_id = uuid4()
        workspace = _workspace(
            status_value=StrategyIdeaStatus.CONVERTED,
            converted_series_id=series_id,
        )
        return {
            "workspace": workspace,
            "idea": workspace["groups"][0]["ideas"][0],
            "converted_series": _series_payload(series_id),
        }


class FakeAlreadyConvertedStrategyService(FakeStrategyService):
    async def convert_idea(self, idea_id: UUID):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Converted ideas cannot be converted again",
        )


class FakeDismissedStrategyService(FakeStrategyService):
    async def convert_idea(self, idea_id: UUID):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Restore dismissed ideas before conversion",
        )


def _client(service: object | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_strategy_service] = lambda: service or FakeStrategyService()
    return TestClient(app)


def test_strategy_workspace_groups_ideas_by_run_date_and_status() -> None:
    response = _client().get("/api/v1/strategy")

    assert response.status_code == 200
    body = response.json()
    assert body["runs"][0]["idea_count"] == 2
    assert body["groups"][0]["status"] == "proposed"
    assert body["groups"][0]["run_date"] == date.today().isoformat()
    assert body["groups"][0]["ideas"][0]["source_proposal"]["episode_plan"]


def test_strategy_run_creation_returns_workspace() -> None:
    response = _client().post("/api/v1/strategy/runs")

    assert response.status_code == 200
    assert response.json()["summary"]["run_count"] == 1


def test_review_dismiss_and_restore_lifecycle_actions() -> None:
    idea_id = uuid4()

    review = _client().post(f"/api/v1/strategy/ideas/{idea_id}/review")
    dismiss = _client().post(f"/api/v1/strategy/ideas/{idea_id}/dismiss")
    restore = _client().post(f"/api/v1/strategy/ideas/{idea_id}/restore")

    assert review.status_code == 200
    assert review.json()["idea"]["status"] == "in_review"
    assert dismiss.status_code == 200
    assert dismiss.json()["idea"]["status"] == "dismissed"
    assert restore.status_code == 200
    assert restore.json()["idea"]["status"] == "in_review"


def test_convert_creates_plan_stage_draft_without_bypassing_gates() -> None:
    response = _client().post(f"/api/v1/strategy/ideas/{uuid4()}/convert")

    assert response.status_code == 200
    body = response.json()
    assert body["idea"]["status"] == "converted"
    assert body["converted_series"]["current_stage"] == "plan"
    assert body["converted_series"]["status"] == "planning"
    assert body["converted_series"]["plan_locked_at"] is None
    assert body["converted_series"]["briefs_approved_at"] is None
    assert body["converted_series"]["captions_unlocked_at"] is None
    assert body["converted_series"]["scheduling_unlocked_at"] is None


def test_converted_idea_cannot_be_converted_again() -> None:
    response = _client(FakeAlreadyConvertedStrategyService()).post(
        f"/api/v1/strategy/ideas/{uuid4()}/convert"
    )

    assert response.status_code == 409


def test_dismissed_idea_must_be_restored_before_conversion() -> None:
    response = _client(FakeDismissedStrategyService()).post(
        f"/api/v1/strategy/ideas/{uuid4()}/convert"
    )

    assert response.status_code == 409
