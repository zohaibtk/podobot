from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.v1.endpoints.research import get_research_scoring_service, get_research_service
from app.db.types import WorkspaceUserStatus
from app.main import create_app
from app.security.auth import CurrentUser, get_current_user


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _run_payload(run_id: UUID | None = None) -> dict[str, object]:
    now = _now()
    return {
        "id": str(run_id or uuid4()),
        "run_type": "discovery",
        "status": "completed",
        "query_text": "Executive AI governance",
        "series_id": str(uuid4()),
        "episode_id": None,
        "strategy_run_id": None,
        "agent_run_id": None,
        "mcp_tool_run_id": str(uuid4()),
        "initiated_by_user_id": str(uuid4()),
        "started_at": now,
        "completed_at": now,
        "duration_ms": 240,
        "failure_reason": None,
        "enabled_source_count": 3,
        "successful_source_count": 2,
        "failed_source_count": 0,
        "skipped_source_count": 1,
        "total_documents_found": 12,
        "total_documents_used": 8,
        "metadata_json": {"adapter": "test"},
        "created_at": now,
        "updated_at": now,
    }


def _usage_payload(run_id: UUID) -> dict[str, object]:
    now = _now()
    return {
        "id": str(uuid4()),
        "research_run_id": str(run_id),
        "source_id": str(uuid4()),
        "source_key": "exa",
        "source_name": "Exa",
        "provider_type": "exa",
        "status": "used",
        "query_text": "Executive AI governance",
        "documents_found": 12,
        "documents_used": 8,
        "latency_ms": 240,
        "failure_reason": None,
        "started_at": now,
        "completed_at": now,
        "created_at": now,
    }


def _document_payload(run_id: UUID) -> dict[str, object]:
    now = _now()
    return {
        "id": str(uuid4()),
        "research_run_id": str(run_id),
        "source_id": str(uuid4()),
        "source_key": "exa",
        "source_name": "Exa",
        "provider_type": "exa",
        "external_resource_id": "doc-1",
        "title": "AI governance operating model",
        "url": "https://example.com/ai-governance",
        "author": "Research Desk",
        "published_at": now,
        "fetched_at": now,
        "resource_type": "article",
        "content_excerpt": "Evidence about AI governance operating cadence.",
        "normalized_content": "Evidence about AI governance operating cadence.",
        "raw_metadata_json": {"score": 0.9},
        "tier": "A",
        "tier_score": 85,
        "engagement_score": 90,
        "freshness_score": 100,
        "author_score": 82,
        "composite_score": 88,
        "trend_score": 72,
        "trend_available": True,
        "trend_source": "serpapi",
        "trend_failure_reason": None,
        "confidence_level": "High",
        "score_explanation_json": {
            "formula": (
                "tier_score * 0.50 + engagement_score * 0.25 + "
                "freshness_score * 0.15 + author_score * 0.10"
            ),
            "composite_score": 88,
            "confidence_level": "High",
            "explanation": "Composite score 88 = Tier 85 x 50%.",
        },
        "used_in_output": True,
        "archived": False,
        "created_at": now,
    }


def _ledger_payload(run_id: UUID, document_id: UUID | None = None) -> dict[str, object]:
    now = _now()
    return {
        "id": str(uuid4()),
        "research_run_id": str(run_id),
        "document_id": str(document_id or uuid4()),
        "source_id": str(uuid4()),
        "source_key": "exa",
        "source_name": "Exa",
        "provider_type": "exa",
        "document_title": "AI governance operating model",
        "document_url": "https://example.com/ai-governance",
        "document_tier": "A",
        "document_tier_score": 85,
        "document_engagement_score": 90,
        "document_freshness_score": 100,
        "document_author_score": 82,
        "document_composite_score": 88,
        "document_confidence_level": "High",
        "document_trend_score": 72,
        "document_trend_available": True,
        "document_score_explanation_json": {
            "explanation": "Composite score 88 = Tier 85 x 50%."
        },
        "series_id": str(uuid4()),
        "episode_id": None,
        "strategy_idea_id": None,
        "ledger_type": "source",
        "evidence_summary": "Exa found evidence about AI governance operating cadence.",
        "created_at": now,
    }


class FakeResearchService:
    def __init__(self) -> None:
        self.run_id = uuid4()
        self.document_id = uuid4()

    async def list_runs(self, **kwargs):
        return {
            "items": [_run_payload(self.run_id)],
            "stats": {
                "total_runs": 1,
                "running_runs": 0,
                "failed_runs": 0,
                "total_documents_found": 12,
                "total_documents_used": 8,
                "average_duration_ms": 240,
            },
            "total": 1,
            "page": kwargs["page"],
            "page_size": kwargs["page_size"],
            "total_pages": 1,
            "has_next": False,
            "has_previous": False,
        }

    async def get_run_detail(self, run_id: UUID):
        return {
            **_run_payload(run_id),
            "source_usage": [_usage_payload(run_id)],
            "documents": [_document_payload(run_id)],
            "ledger_entries": [_ledger_payload(run_id, self.document_id)],
            "score_summary": _score_summary(),
        }

    async def list_documents(self, **kwargs):
        return self._page([_document_payload(self.run_id)], kwargs)

    async def list_ledger_entries(self, **kwargs):
        return self._page([_ledger_payload(self.run_id, self.document_id)], kwargs)

    async def list_source_usage(self, **kwargs):
        return self._page([_usage_payload(self.run_id)], kwargs)

    async def retry_run(self, run_id: UUID):
        return {
            "success": True,
            "message": "Research retry placeholder created for orchestration.",
            "run": _run_payload(run_id),
        }

    async def archive_document(self, document_id: UUID):
        document = _document_payload(self.run_id)
        document["id"] = str(document_id)
        document["archived"] = True
        return {"success": True, "message": "Research document archived.", "document": document}

    async def clear_failed_runs(self):
        return {"success": True, "message": "Cleared 1 failed research run(s)."}

    def _page(self, items: list[dict[str, object]], kwargs: dict[str, object]):
        return {
            "items": items,
            "total": len(items),
            "page": kwargs["page"],
            "page_size": kwargs["page_size"],
            "total_pages": 1,
            "has_next": False,
            "has_previous": False,
        }


class FakeResearchScoringService:
    async def get_document_score(self, document_id: UUID):
        return _document_score_payload(document_id)

    async def score_document(self, document_id: UUID):
        payload = _document_score_payload(document_id)
        payload["composite_score"] = 90
        payload["confidence_level"] = "High"
        return payload

    async def score_run_documents(self, run_id: UUID):
        return {
            "success": True,
            "message": "Scored 1 research document(s).",
            "score_summary": _score_summary(),
        }

    async def explain_score(self, payload: dict[str, object]):
        return {
            "formula": (
                "tier_score * 0.50 + engagement_score * 0.25 + "
                "freshness_score * 0.15 + author_score * 0.10"
            ),
            "formula_version": "prd-r4-v1",
            "tier_score": payload["tier_score"],
            "engagement_score": payload["engagement_score"],
            "freshness_score": payload["freshness_score"],
            "author_score": payload["author_score"],
            "composite_score": 82,
            "confidence_level": "Medium",
            "explanation": "Composite score 82 = Tier 90 x 50%.",
        }

    async def run_score_summary(self, run_id: UUID):
        return _score_summary()

    async def entity_score_breakdown(self, entity_type, entity_id: UUID):
        return {
            "id": uuid4(),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "research_run_id": None,
            "tier_score_avg": 0,
            "engagement_score_avg": 0,
            "freshness_score_avg": 0,
            "author_score_avg": 0,
            "composite_score": 0,
            "trend_score": None,
            "trend_available": False,
            "confidence_level": "Weak",
            "formula_version": "prd-r4-v1",
            "explanation_json": {"explanation": "No supporting evidence available"},
            "created_at": datetime.now(UTC),
        }


def _score_summary() -> dict[str, object]:
    return {
        "document_count": 1,
        "tier_score_avg": 85,
        "engagement_score_avg": 90,
        "freshness_score_avg": 100,
        "author_score_avg": 82,
        "composite_score": 88,
        "trend_score": 72,
        "trend_available": True,
        "confidence_level": "High",
        "confidence_distribution": {"High": 1, "Medium": 0, "Low": 0, "Weak": 0},
        "tier_distribution": {"S": 0, "A": 1, "B": 0, "C": 0, "D": 0},
        "explanation": "Average composite score 88 from 1 linked research document(s).",
    }


def _document_score_payload(document_id: UUID) -> dict[str, object]:
    return {
        "document_id": document_id,
        "research_run_id": uuid4(),
        "source_id": uuid4(),
        "source_key": "exa",
        "source_name": "Exa",
        "provider_type": "exa",
        "title": "AI governance operating model",
        "tier": "A",
        "tier_score": 85,
        "engagement_score": 90,
        "freshness_score": 100,
        "author_score": 82,
        "composite_score": 88,
        "trend_score": 72,
        "trend_available": True,
        "trend_source": "serpapi",
        "trend_failure_reason": None,
        "confidence_level": "High",
        "score_explanation_json": {
            "explanation": "Composite score 88 = Tier 85 x 50%."
        },
    }


def _current_user(*permissions: str) -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="operator@example.com",
        full_name="Operator",
        status=WorkspaceUserStatus.ACTIVE,
        role_keys=frozenset({"producer"}),
        permissions=frozenset(permissions),
    )


def _client(
    *,
    service: FakeResearchService | None = None,
    scoring_service: FakeResearchScoringService | None = None,
    current_user: CurrentUser | None = None,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_research_service] = lambda: service or FakeResearchService()
    app.dependency_overrides[get_research_scoring_service] = lambda: (
        scoring_service or FakeResearchScoringService()
    )
    app.dependency_overrides[get_current_user] = lambda: (
        current_user or _current_user("research.view", "research.manage")
    )
    return TestClient(app)


def test_research_run_list_is_paginated() -> None:
    response = _client().get("/api/v1/research/runs?page=1&page_size=20")

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 1
    assert body["stats"]["total_documents_found"] == 12


def test_run_detail_returns_source_usage_documents_and_ledger() -> None:
    response = _client().get(f"/api/v1/research/runs/{uuid4()}")

    assert response.status_code == 200
    body = response.json()
    assert body["source_usage"][0]["source_key"] == "exa"
    assert body["documents"][0]["title"] == "AI governance operating model"
    assert body["ledger_entries"][0]["evidence_summary"]


def test_research_document_list_is_paginated() -> None:
    response = _client().get("/api/v1/research/documents?page=1&page_size=10")

    assert response.status_code == 200
    assert response.json()["items"][0]["used_in_output"] is True


def test_discovery_ledger_list_is_paginated() -> None:
    response = _client().get("/api/v1/research/ledger?page=1&page_size=10")

    assert response.status_code == 200
    assert response.json()["items"][0]["ledger_type"] == "source"


def test_source_usage_history_is_paginated() -> None:
    response = _client().get("/api/v1/research/source-usage?page=1&page_size=10")

    assert response.status_code == 200
    assert response.json()["items"][0]["status"] == "used"


def test_research_document_score_endpoint_returns_explanation() -> None:
    response = _client().get(f"/api/v1/research/documents/{uuid4()}/score")

    assert response.status_code == 200
    body = response.json()
    assert body["composite_score"] == 88
    assert body["score_explanation_json"]["explanation"]


def test_research_document_rescore_requires_manage_permission() -> None:
    response = _client(current_user=_current_user("research.view")).post(
        f"/api/v1/research/documents/{uuid4()}/rescore"
    )

    assert response.status_code == 403
    assert "research.manage" in response.text


def test_research_run_score_documents_requires_manage_permission() -> None:
    response = _client(current_user=_current_user("research.view")).post(
        f"/api/v1/research/runs/{uuid4()}/score-documents"
    )

    assert response.status_code == 403
    assert "research.manage" in response.text


def test_research_score_explain_endpoint_returns_formula() -> None:
    response = _client().post(
        "/api/v1/research/score/explain",
        json={
            "tier_score": 90,
            "engagement_score": 70,
            "freshness_score": 85,
            "author_score": 80,
        },
    )

    assert response.status_code == 200
    assert response.json()["confidence_level"] == "Medium"


def test_entity_without_evidence_returns_weak_breakdown() -> None:
    response = _client().get(
        f"/api/v1/research/entities/research_document/{uuid4()}/score-breakdown"
    )

    assert response.status_code == 200
    assert response.json()["confidence_level"] == "Weak"


def test_unauthorized_user_is_blocked_from_research_runs() -> None:
    response = _client(current_user=_current_user("series.view")).get("/api/v1/research/runs")

    assert response.status_code == 403
    assert "research.view" in response.text


def test_retry_permission_is_enforced() -> None:
    response = _client(current_user=_current_user("research.view")).post(
        f"/api/v1/research/runs/{uuid4()}/retry"
    )

    assert response.status_code == 403
    assert "research.manage" in response.text


def test_retry_allows_research_manager() -> None:
    response = _client().post(f"/api/v1/research/runs/{uuid4()}/retry")

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_archive_document_requires_manage_permission() -> None:
    response = _client(current_user=_current_user("research.view")).post(
        f"/api/v1/research/documents/{uuid4()}/archive"
    )

    assert response.status_code == 403
    assert "research.manage" in response.text


def test_clear_failed_runs_requires_manage_permission() -> None:
    response = _client(current_user=_current_user("research.view")).post(
        "/api/v1/research/runs/clear-failed"
    )

    assert response.status_code == 403
    assert "research.manage" in response.text
