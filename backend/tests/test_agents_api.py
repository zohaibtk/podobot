from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.agents.schemas import AgentRunRequest, AgentRunRetryRequest, PromptVersionCreateRequest
from app.api.v1.endpoints.agents import get_agent_service
from app.db.types import AgentRunStatus, PromptVersionStatus, WorkspaceUserStatus
from app.main import create_app
from app.security.auth import CurrentUser, get_current_user


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _agent(agent_key: str = "narrative") -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "key": agent_key,
        "name": f"{agent_key.title()} Agent",
        "responsibility": "Narrow workflow responsibility.",
        "tools": ["mock_tool"],
        "required_permission": "narrative.generate",
        "is_enabled": True,
        "created_at": _now(),
        "updated_at": _now(),
    }


def _prompt(
    prompt_key: str = "narrative.v1",
    status_value: PromptVersionStatus = PromptVersionStatus.ACTIVE,
) -> dict[str, object]:
    agent_id = uuid4()
    template_id = uuid4()
    version = {
        "id": str(uuid4()),
        "prompt_template_id": str(template_id),
        "agent_id": str(agent_id),
        "prompt_key": prompt_key,
        "agent_key": prompt_key.split(".", 1)[0],
        "version_number": 1,
        "template_body": "Return structured JSON and preserve human gates.",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "status": status_value.value,
        "created_by": "system",
        "created_at": _now(),
    }
    return {
        "id": str(template_id),
        "key": prompt_key,
        "agent_id": str(agent_id),
        "agent_key": prompt_key.split(".", 1)[0],
        "name": "Narrative default prompt",
        "description": "Default prompt.",
        "created_by": "system",
        "active_version": version if status_value == PromptVersionStatus.ACTIVE else None,
        "versions": [version],
        "created_at": _now(),
        "updated_at": _now(),
    }


def _run(
    *,
    run_id: UUID | None = None,
    agent_key: str = "narrative",
    status_value: AgentRunStatus = AgentRunStatus.SUCCEEDED,
    error_reason: str | None = None,
    retry_of_run_id: UUID | None = None,
) -> dict[str, object]:
    return {
        "id": str(run_id or uuid4()),
        "agent_id": str(uuid4()),
        "agent_key": agent_key,
        "prompt_version_id": str(uuid4()),
        "prompt_key": f"{agent_key}.v1",
        "prompt_version_number": 1,
        "status": status_value.value,
        "entity_type": "series",
        "entity_id": str(uuid4()),
        "workflow_stage": "narrative",
        "trigger": "manual",
        "input_payload": {"series_id": "example"},
        "output_payload": None
        if error_reason
        else {"summary": "Generated", "needs_approval": True},
        "output_metadata": {"provider": "mock", "api_key": "[redacted]"},
        "validation_summary": {"status": "passed", "needs_approval": True, "errors": []},
        "error_reason": error_reason,
        "regeneration_reason": None,
        "retry_of_run_id": str(retry_of_run_id) if retry_of_run_id else None,
        "attempt_number": 2 if retry_of_run_id else 1,
        "started_at": _now(),
        "completed_at": _now(),
        "created_at": _now(),
        "updated_at": _now(),
    }


def _run_detail(**kwargs) -> dict[str, object]:
    run = _run(**kwargs)
    return {
        **run,
        "audit_logs": [
            {
                "id": str(uuid4()),
                "run_id": run["id"],
                "agent_id": run["agent_id"],
                "action": "run_completed",
                "actor_id": str(uuid4()),
                "message": "Run completed.",
                "metadata": {"provider": "mock"},
                "created_at": _now(),
            }
        ],
        "validation_results": [
            {
                "id": str(uuid4()),
                "run_id": run["id"],
                "status": "passed",
                "checks": [{"name": "approval_gate_flag", "passed": True}],
                "errors": [],
                "created_at": _now(),
            }
        ],
    }


class FakeAgentService:
    def __init__(self) -> None:
        self.original_run_id = uuid4()

    async def list_agents(self):
        return [_agent("research"), _agent("narrative"), _agent("coordinator")]

    async def get_agent(self, agent_key: str):
        return _agent(agent_key)

    async def list_prompts(self):
        return [_prompt("narrative.v1")]

    async def get_prompt(self, prompt_key: str):
        return _prompt(prompt_key)

    async def create_prompt_version(self, prompt_key: str, payload: PromptVersionCreateRequest):
        prompt = _prompt(prompt_key)["active_version"]
        prompt["id"] = str(uuid4())
        prompt["version_number"] = 2
        prompt["template_body"] = payload.template_body
        prompt["status"] = payload.status.value
        return prompt

    async def run_agent(
        self,
        agent_key: str,
        payload: AgentRunRequest,
        current_user: CurrentUser,
    ):
        if agent_key == "narrative" and not current_user.has_permission("narrative.generate"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission required: narrative.generate",
            )
        if payload.input_payload.get("force_failure"):
            return _run_detail(
                agent_key=agent_key,
                status_value=AgentRunStatus.FAILED,
                error_reason="Mock provider forced failure",
            )
        detail = _run_detail(agent_key=agent_key)
        detail["input_payload"] = payload.input_payload
        detail["entity_type"] = payload.entity_type
        detail["entity_id"] = str(payload.entity_id) if payload.entity_id else None
        detail["workflow_stage"] = payload.workflow_stage
        return detail

    async def retry_run(
        self,
        run_id: UUID,
        payload: AgentRunRetryRequest,
        current_user: CurrentUser,
    ):
        return _run_detail(agent_key="narrative", retry_of_run_id=run_id)

    async def list_runs(self, **kwargs):
        return [_run(agent_key=kwargs.get("agent_key") or "narrative")]

    async def get_run_detail(self, run_id: UUID):
        return _run_detail(run_id=run_id)

    async def token_stats(self, period: str = "day"):
        return {
            "period": period,
            "generated_at": _now(),
            "window_start": _now(),
            "window_end": _now(),
            "totals": {
                "prompt_tokens": 120,
                "completion_tokens": 80,
                "cached_tokens": 0,
                "reasoning_tokens": 0,
                "total_tokens": 200,
                "run_count": 2,
                "tokenized_run_count": 2,
                "average_tokens_per_run": 100,
            },
            "agents": [
                {
                    "agent_id": str(uuid4()),
                    "agent_key": "narrative",
                    "agent_name": "Narrative Agent",
                    "provider": "mock",
                    "prompt_tokens": 120,
                    "completion_tokens": 80,
                    "cached_tokens": 0,
                    "reasoning_tokens": 0,
                    "total_tokens": 200,
                    "run_count": 2,
                    "tokenized_run_count": 2,
                    "average_tokens_per_run": 100,
                    "share_percentage": 100,
                    "last_run_at": _now(),
                }
            ],
            "timeline": [
                {
                    "label": "00:00",
                    "prompt_tokens": 120,
                    "completion_tokens": 80,
                    "total_tokens": 200,
                    "run_count": 2,
                }
            ],
            "requests": [
                {
                    "id": str(uuid4()),
                    "agent_id": str(uuid4()),
                    "agent_key": "narrative",
                    "agent_name": "Narrative Agent",
                    "provider": "mock",
                    "status": "succeeded",
                    "trigger": "manual",
                    "workflow_stage": "narrative",
                    "sequence_number": 1,
                    "label": "Narrative #1",
                    "created_at": _now(),
                    "completed_at": _now(),
                    "prompt_tokens": 70,
                    "completion_tokens": 30,
                    "cached_tokens": 0,
                    "reasoning_tokens": 0,
                    "total_tokens": 100,
                    "estimated_prompt_tokens": 70,
                    "estimated_completion_tokens": 30,
                    "estimated_total_tokens": 100,
                    "display_prompt_tokens": 70,
                    "display_completion_tokens": 30,
                    "display_total_tokens": 100,
                    "is_estimated": False,
                },
                {
                    "id": str(uuid4()),
                    "agent_id": str(uuid4()),
                    "agent_key": "narrative",
                    "agent_name": "Narrative Agent",
                    "provider": "mock",
                    "status": "succeeded",
                    "trigger": "manual",
                    "workflow_stage": "narrative",
                    "sequence_number": 2,
                    "label": "Narrative #2",
                    "created_at": _now(),
                    "completed_at": _now(),
                    "prompt_tokens": 50,
                    "completion_tokens": 50,
                    "cached_tokens": 0,
                    "reasoning_tokens": 0,
                    "total_tokens": 100,
                    "estimated_prompt_tokens": 50,
                    "estimated_completion_tokens": 50,
                    "estimated_total_tokens": 100,
                    "display_prompt_tokens": 50,
                    "display_completion_tokens": 50,
                    "display_total_tokens": 100,
                    "is_estimated": False,
                },
            ],
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


def _client(current_user: CurrentUser | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()
    app.dependency_overrides[get_current_user] = lambda: (
        current_user
        or _current_user(
            "narrative.generate",
            "settings.manage",
            "series.view",
        )
    )
    return TestClient(app)


def test_agent_registry_lists_seeded_agents() -> None:
    response = _client().get("/api/v1/agents")

    assert response.status_code == 200
    keys = {agent["key"] for agent in response.json()["items"]}
    assert {"research", "narrative", "coordinator"}.issubset(keys)


def test_prompt_registry_returns_active_prompt_version() -> None:
    response = _client().get("/api/v1/prompts/narrative.v1")

    assert response.status_code == 200
    assert response.json()["active_version"]["status"] == "active"


def test_only_one_active_prompt_version_contract() -> None:
    response = _client().post(
        "/api/v1/prompts/narrative.v1/versions",
        json={
            "template_body": "Updated prompt",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "status": "active",
            "created_by": "operator",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "active"
    assert response.json()["version_number"] == 2


def test_agent_run_is_created_and_stores_metadata() -> None:
    response = _client().post(
        "/api/v1/agents/narrative/run",
        json={
            "input_payload": {"series_id": "series-1"},
            "entity_type": "series",
            "entity_id": str(uuid4()),
            "workflow_stage": "narrative",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["input_payload"]["series_id"] == "series-1"
    assert body["output_metadata"]["provider"] == "mock"
    assert "mock-secret" not in response.text


def test_failed_agent_run_stores_error_reason() -> None:
    response = _client().post(
        "/api/v1/agents/narrative/run",
        json={"input_payload": {"force_failure": True}},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    assert response.json()["error_reason"] == "Mock provider forced failure"


def test_retry_creates_new_auditable_run() -> None:
    original_run_id = uuid4()
    response = _client().post(
        f"/api/v1/agents/runs/{original_run_id}/retry",
        json={"regeneration_reason": "Retry after provider failure."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["retry_of_run_id"] == str(original_run_id)
    assert body["attempt_number"] == 2
    assert body["audit_logs"]


def test_regeneration_requires_reason() -> None:
    response = _client().post(
        "/api/v1/agents/narrative/run",
        json={"trigger": "regeneration", "input_payload": {}},
    )

    assert response.status_code == 422


def test_agent_output_does_not_bypass_approval_gates() -> None:
    response = _client().post(
        "/api/v1/agents/narrative/run",
        json={"input_payload": {"series_id": "series-1"}},
    )

    assert response.status_code == 201
    assert response.json()["output_payload"]["needs_approval"] is True


def test_unauthorized_users_cannot_run_restricted_agents() -> None:
    response = _client(_current_user("series.view")).post(
        "/api/v1/agents/narrative/run",
        json={"input_payload": {}},
    )

    assert response.status_code == 403


def test_workflow_agent_history_is_returned() -> None:
    entity_id = uuid4()
    response = _client().get(f"/api/v1/workflow/series/{entity_id}/agent-history")

    assert response.status_code == 200
    assert response.json()["items"][0]["entity_type"] == "series"


def test_agent_token_stats_are_returned_by_period() -> None:
    response = _client().get("/api/v1/agents/token-stats?period=week")

    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "week"
    assert body["totals"]["total_tokens"] == 200
    assert body["agents"][0]["agent_key"] == "narrative"
    assert body["requests"][0]["display_total_tokens"] == 100
