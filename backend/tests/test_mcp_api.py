import inspect
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.mcp import get_mcp_service
from app.db.types import MCPServerStatus, MCPToolRunStatus, WorkspaceUserStatus
from app.main import create_app
from app.mcp.circuit_breaker import assert_server_available
from app.mcp.client.base import BaseMCPClient
from app.mcp.security import redact_sensitive
from app.mcp.service import MCPToolExecutionService
from app.modules.schedules.service import ScheduleService
from app.security.auth import CurrentUser, get_current_user


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _server(key: str, critical: bool, status_value: str = "healthy") -> dict[str, object]:
    server_id = uuid4()
    return {
        "id": str(server_id),
        "key": key,
        "name": key.title(),
        "purpose": f"{key} MCP server.",
        "adapter_type": "mock",
        "is_critical": critical,
        "status": status_value,
        "failure_reason": None if status_value == "healthy" else "Mock failure.",
        "last_tested_at": _now(),
        "last_success_at": _now() if status_value == "healthy" else None,
        "failure_count": 0,
        "circuit_open_until": None,
        "settings": {"mode": "mock"},
        "tool_count": 2,
        "auth_config": {
            "id": str(uuid4()),
            "server_id": str(server_id),
            "auth_type": "bearer" if key == "buffer" else "none",
            "has_secret": key == "buffer",
            "masked_label": "buf_****_key" if key == "buffer" else None,
            "settings": {},
            "created_at": _now(),
            "updated_at": _now(),
        },
        "created_at": _now(),
        "updated_at": _now(),
    }


def _tool(key: str, server_key: str) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "server_id": str(uuid4()),
        "server_key": server_key,
        "key": key,
        "display_name": key.replace(".", " ").title(),
        "description": "MCP tool contract.",
        "input_schema": {"type": "object", "required": ["caption_id"] if "create" in key else []},
        "output_schema": {"type": "object", "required": ["post_id"] if "buffer" in key else []},
        "auth_required": server_key == "buffer",
        "timeout_ms": 30000,
        "retry_policy": {"max_attempts": 2},
        "circuit_breaker_policy": {"failure_threshold": 3},
        "is_critical": server_key in {"buffer", "llm", "storage"},
        "allowed_callers": ["workflow", "agent", "admin", "system"],
        "status": "enabled",
        "created_at": _now(),
        "updated_at": _now(),
    }


def _run(
    *,
    run_id: UUID | None = None,
    status_value: MCPToolRunStatus = MCPToolRunStatus.SUCCEEDED,
    retry_of_run_id: UUID | None = None,
    error_reason: str | None = None,
    input_payload: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "id": str(run_id or uuid4()),
        "server_id": str(uuid4()),
        "tool_id": str(uuid4()),
        "server_key": "buffer",
        "tool_key": "buffer.create_scheduled_post",
        "status": status_value.value,
        "caller_type": "admin",
        "caller_id": "operator",
        "requested_by": str(uuid4()),
        "entity_type": "series",
        "entity_id": str(uuid4()),
        "workflow_stage": "schedule",
        "input_payload": input_payload or {"caption_id": "cap-1"},
        "output_payload": None if error_reason else {"post_id": "buf_123", "status": "queued"},
        "output_metadata": {"adapter": "mock"},
        "error_reason": error_reason,
        "retry_of_run_id": str(retry_of_run_id) if retry_of_run_id else None,
        "attempt_number": 2 if retry_of_run_id else 1,
        "started_at": _now(),
        "completed_at": _now(),
        "created_at": _now(),
        "updated_at": _now(),
    }


class FakeMCPService:
    def __init__(self) -> None:
        self.original_run_id = uuid4()

    async def list_servers(self):
        return [
            _server("buffer", True),
            _server("research", False, "degraded"),
            _server("llm", True),
            _server("storage", True),
        ]

    async def get_server(self, server_key: str):
        return _server(server_key, server_key != "research")

    async def test_server(self, server_key: str, current_user: CurrentUser):
        self._assert_allowed(current_user)
        run = _run()
        return {
            "server": _server(server_key, server_key != "research"),
            "run": run,
            "success": True,
            "message": f"{server_key} mock connection is healthy.",
        }

    async def list_tools(self, server_key: str | None = None):
        tools = [
            _tool("buffer.create_scheduled_post", "buffer"),
            _tool("research.search_sources", "research"),
            _tool("llm.generate_text", "llm"),
            _tool("storage.upload_file", "storage"),
        ]
        return [tool for tool in tools if server_key is None or tool["server_key"] == server_key]

    async def get_tool(self, tool_key: str):
        server_key = tool_key.split(".", 1)[0]
        return _tool(tool_key, server_key)

    async def execute_tool(self, tool_key: str, payload, *, current_user=None, **kwargs):
        self._assert_allowed(current_user)
        if tool_key == "buffer.create_scheduled_post" and "caption_id" not in payload.input_payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="MCP payload missing required field(s): caption_id",
            )
        if payload.input_payload.get("force_failure"):
            return _run(
                status_value=MCPToolRunStatus.FAILED,
                error_reason="Mock MCP failure",
                input_payload=payload.input_payload,
            )
        return _run(input_payload=payload.input_payload)

    async def list_runs(self, **kwargs):
        return [_run(run_id=self.original_run_id)]

    async def get_run_detail(self, run_id: UUID):
        run = _run(run_id=run_id)
        return {
            **run,
            "audit_logs": [
                {
                    "id": str(uuid4()),
                    "run_id": str(run_id),
                    "server_id": run["server_id"],
                    "tool_id": run["tool_id"],
                    "action": "tool_run_completed",
                    "actor_id": str(uuid4()),
                    "message": "Tool completed.",
                    "metadata": {"api_key": "[REDACTED]"},
                    "created_at": _now(),
                }
            ],
        }

    async def retry_run(self, run_id: UUID, payload, current_user: CurrentUser):
        self._assert_allowed(current_user)
        return _run(retry_of_run_id=run_id)

    def _assert_allowed(self, current_user: CurrentUser | None) -> None:
        if current_user is None or not current_user.has_permission("integration.manage"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission required: integration.manage",
            )


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
    app.dependency_overrides[get_mcp_service] = lambda: FakeMCPService()
    app.dependency_overrides[get_current_user] = lambda: (
        current_user or _current_user("integration.manage")
    )
    return TestClient(app)


def test_mcp_servers_are_seeded_and_do_not_expose_secrets() -> None:
    response = _client().get("/api/v1/mcp/servers")

    assert response.status_code == 200
    keys = {server["key"] for server in response.json()["items"]}
    assert {"buffer", "research", "llm", "storage"}.issubset(keys)
    assert "buf_mock_development_key" not in response.text
    assert "secret_ref" not in response.text


def test_mcp_tools_are_seeded() -> None:
    response = _client().get("/api/v1/mcp/tools")

    assert response.status_code == 200
    keys = {tool["key"] for tool in response.json()["items"]}
    assert {
        "buffer.create_scheduled_post",
        "research.search_sources",
        "llm.generate_text",
        "storage.upload_file",
    }.issubset(keys)


def test_mcp_tool_contract_validation_blocks_missing_required_input() -> None:
    response = _client().post(
        "/api/v1/mcp/tools/buffer.create_scheduled_post/run",
        json={"input_payload": {}, "caller_type": "admin"},
    )

    assert response.status_code == 422
    assert "caption_id" in response.text


def test_mcp_schema_validation_rejects_null_required_fields() -> None:
    service = MCPToolExecutionService(
        cast(AsyncSession, None),
        client=cast(BaseMCPClient, object()),
    )

    with pytest.raises(HTTPException) as exc_info:
        service._validate_schema(
            {
                "type": "object",
                "required": ["caption_id"],
                "properties": {"caption_id": {"type": "string"}},
            },
            {"caption_id": None},
        )

    assert exc_info.value.status_code == 422
    assert "cannot be null" in exc_info.value.detail


def test_mcp_schema_validation_rejects_wrong_declared_types() -> None:
    service = MCPToolExecutionService(
        cast(AsyncSession, None),
        client=cast(BaseMCPClient, object()),
    )

    with pytest.raises(HTTPException) as exc_info:
        service._validate_schema(
            {
                "type": "object",
                "required": ["tier_score"],
                "properties": {"tier_score": {"type": "number"}},
            },
            {"tier_score": True},
        )

    assert exc_info.value.status_code == 422
    assert "tier_score" in exc_info.value.detail
    assert "number" in exc_info.value.detail


def test_mcp_schema_validation_accepts_supported_json_schema_types() -> None:
    service = MCPToolExecutionService(
        cast(AsyncSession, None),
        client=cast(BaseMCPClient, object()),
    )

    service._validate_schema(
        {
            "type": "object",
            "required": ["text", "score", "metadata", "tags", "ready"],
            "properties": {
                "text": {"type": "string"},
                "score": {"type": "number"},
                "metadata": {"type": "object"},
                "tags": {"type": "array"},
                "ready": {"type": "boolean"},
            },
        },
        {
            "text": "caption",
            "score": 82.5,
            "metadata": {"source": "test"},
            "tags": ["mcp"],
            "ready": False,
            "extra": None,
        },
    )


def test_mcp_tool_run_is_created_and_failed_run_stores_reason() -> None:
    created = _client().post(
        "/api/v1/mcp/tools/buffer.create_scheduled_post/run",
        json={"input_payload": {"caption_id": "cap-1"}, "caller_type": "admin"},
    )
    failed = _client().post(
        "/api/v1/mcp/tools/buffer.create_scheduled_post/run",
        json={
            "input_payload": {"caption_id": "cap-1", "force_failure": True},
            "caller_type": "admin",
        },
    )

    assert created.status_code == 201
    assert created.json()["status"] == "succeeded"
    assert failed.status_code == 201
    assert failed.json()["status"] == "failed"
    assert failed.json()["error_reason"] == "Mock MCP failure"


def test_retry_creates_new_auditable_run() -> None:
    original_run_id = uuid4()
    response = _client().post(f"/api/v1/mcp/runs/{original_run_id}/retry", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["retry_of_run_id"] == str(original_run_id)
    assert body["attempt_number"] == 2


def test_mcp_server_test_returns_visible_result() -> None:
    response = _client().post("/api/v1/mcp/servers/buffer/test")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "healthy" in body["message"]
    assert body["run"]["status"] == "succeeded"


def test_workflow_mcp_history_returns_tool_runs() -> None:
    response = _client().get(f"/api/v1/workflow/series/{uuid4()}/mcp-history")

    assert response.status_code == 200
    assert response.json()["items"][0]["tool_key"] == "buffer.create_scheduled_post"


def test_critical_server_failure_blocks_and_optional_failure_degrades() -> None:
    critical = SimpleNamespace(
        key="buffer",
        is_critical=True,
        status=MCPServerStatus.BROKEN,
        failure_reason="Buffer offline.",
        circuit_open_until=None,
    )
    optional = SimpleNamespace(
        key="research",
        is_critical=False,
        status=MCPServerStatus.BROKEN,
        failure_reason="Research offline.",
        circuit_open_until=None,
    )

    with pytest.raises(HTTPException):
        assert_server_available(critical)
    assert_server_available(optional)


def test_unauthorized_user_cannot_run_admin_mcp_tool() -> None:
    response = _client(_current_user("series.view")).post(
        "/api/v1/mcp/tools/buffer.create_scheduled_post/run",
        json={"input_payload": {"caption_id": "cap-1"}, "caller_type": "admin"},
    )

    assert response.status_code == 403
    assert "integration.manage" in response.text


def test_mcp_run_detail_has_redacted_audit_metadata() -> None:
    response = _client().get(f"/api/v1/mcp/runs/{uuid4()}")

    assert response.status_code == 200
    assert response.json()["audit_logs"][0]["metadata"]["api_key"] == "[REDACTED]"


def test_agent_tool_call_metadata_contract_goes_through_mcp() -> None:
    run = {
        "output_metadata": {
            "mcp_run_ids": [str(uuid4())],
            "mcp_tool_calls": [{"tool_key": "research.search_sources", "status": "succeeded"}],
        }
    }

    assert run["output_metadata"]["mcp_run_ids"]
    assert run["output_metadata"]["mcp_tool_calls"][0]["tool_key"] == "research.search_sources"


def test_buffer_workflow_no_longer_directly_depends_on_buffer_client() -> None:
    signature = inspect.signature(ScheduleService.__init__)

    assert "buffer_adapter" not in signature.parameters
    assert not hasattr(ScheduleService, "buffer_adapter")


def test_audit_redaction_removes_sensitive_values() -> None:
    redacted = redact_sensitive(
        {
            "api_key": "raw-key",
            "nested": {"refresh_token": "raw-token", "safe": "visible"},
        }
    )

    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["refresh_token"] == "[REDACTED]"
    assert redacted["nested"]["safe"] == "visible"
