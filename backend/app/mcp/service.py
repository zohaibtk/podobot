from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.types import MCPServerStatus, MCPToolRunStatus, MCPToolStatus
from app.mcp.circuit_breaker import (
    apply_circuit_failure,
    apply_circuit_success,
    assert_server_available,
)
from app.mcp.client.base import BaseMCPClient, MCPClientRequest
from app.mcp.client.router import MCPRouterClient
from app.mcp.defaults import DEFAULT_MCP_SERVERS, DEFAULT_MCP_TOOLS
from app.mcp.models import MCPAuthConfig, MCPServer, MCPTool, MCPToolAuditLog, MCPToolRun
from app.mcp.schemas.runtime import MCPToolRunRequest
from app.mcp.security import mask_secret, redact_sensitive
from app.modules.research.models import ResearchRun
from app.schemas.pagination import cursor_meta, decode_cursor, encode_cursor
from app.security.auth import CurrentUser

VALID_CALLER_TYPES = {"workflow", "agent", "admin", "system"}


class MCPRegistryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_defaults(self, *, commit: bool = True) -> None:
        changed = False
        servers_by_key = await self._servers_by_key()
        for default in DEFAULT_MCP_SERVERS:
            server = servers_by_key.get(default.key)
            if server is None:
                server = MCPServer(
                    key=default.key,
                    name=default.name,
                    purpose=default.purpose,
                    adapter_type=default.adapter_type,
                    is_critical=default.is_critical,
                    status=default.status,
                    settings=default.settings or {},
                )
                self.session.add(server)
                changed = True
            else:
                previous_adapter_type = server.adapter_type
                server.name = default.name
                server.purpose = default.purpose
                server.adapter_type = default.adapter_type
                server.is_critical = default.is_critical
                if (
                    server.status == MCPServerStatus.NOT_CONFIGURED
                    or (
                        server.key == "llm"
                        and default.adapter_type == "gemini"
                        and previous_adapter_type != "gemini"
                    )
                ):
                    server.status = default.status
                    server.failure_reason = None
                server.settings = {**(server.settings or {}), **(default.settings or {})}
                changed = True

        if changed:
            await self.session.flush()

        servers_by_key = await self._servers_by_key()
        auth_by_server_id = await self._auth_by_server_id()
        for default in DEFAULT_MCP_SERVERS:
            server = servers_by_key[default.key]
            auth = auth_by_server_id.get(server.id)
            if auth is None:
                self.session.add(
                    MCPAuthConfig(
                        server_id=server.id,
                        auth_type=default.auth_type,
                        secret_ref=default.secret_ref,
                        has_secret=default.secret_ref is not None,
                        masked_label=default.masked_label or mask_secret(default.secret_ref),
                        settings={},
                    )
                )
                changed = True
            else:
                auth.auth_type = default.auth_type
                auth.secret_ref = default.secret_ref
                auth.has_secret = default.secret_ref is not None
                auth.masked_label = default.masked_label or mask_secret(default.secret_ref)
                changed = True

        tools_by_key = await self._tools_by_key()
        for default in DEFAULT_MCP_TOOLS:
            server = servers_by_key[default.server_key]
            tool = tools_by_key.get(default.key)
            retry_policy = default.retry_policy or {"max_attempts": 2, "backoff_ms": 250}
            circuit_policy = default.circuit_breaker_policy or {
                "failure_threshold": 3,
                "cooldown_seconds": 300,
            }
            if tool is None:
                self.session.add(
                    MCPTool(
                        server_id=server.id,
                        server_key=server.key,
                        key=default.key,
                        display_name=default.display_name,
                        description=default.description,
                        input_schema=default.input_schema,
                        output_schema=default.output_schema,
                        auth_required=default.auth_required,
                        timeout_ms=default.timeout_ms,
                        retry_policy=retry_policy,
                        circuit_breaker_policy=circuit_policy,
                        is_critical=default.is_critical,
                        allowed_callers=default.allowed_callers or [],
                        status=default.status,
                    )
                )
                changed = True
            else:
                tool.server_id = server.id
                tool.server_key = server.key
                tool.display_name = default.display_name
                tool.description = default.description
                tool.input_schema = default.input_schema
                tool.output_schema = default.output_schema
                tool.auth_required = default.auth_required
                tool.timeout_ms = default.timeout_ms
                tool.retry_policy = retry_policy
                tool.circuit_breaker_policy = circuit_policy
                tool.is_critical = default.is_critical
                tool.allowed_callers = default.allowed_callers or []
                if (
                    tool.status == MCPToolStatus.DISABLED
                    and default.status != MCPToolStatus.ENABLED
                ):
                    tool.status = default.status
                changed = True

        if changed and commit:
            await self.session.commit()
        elif changed:
            await self.session.flush()

    async def list_servers(self) -> list[dict[str, object]]:
        await self.ensure_defaults()
        servers = await self._servers()
        tool_counts = await self._tool_counts()
        auth_by_server_id = await self._auth_by_server_id()
        return [
            self._server_payload(
                server,
                tool_count=tool_counts.get(server.id, 0),
                auth_config=auth_by_server_id.get(server.id),
            )
            for server in servers
        ]

    async def get_server(self, server_key: str) -> dict[str, object]:
        await self.ensure_defaults()
        server = await self._server_by_key_or_404(server_key)
        tool_counts = await self._tool_counts()
        auth_by_server_id = await self._auth_by_server_id()
        return self._server_payload(
            server,
            tool_count=tool_counts.get(server.id, 0),
            auth_config=auth_by_server_id.get(server.id),
        )

    async def list_tools(self, *, server_key: str | None = None) -> list[MCPTool]:
        await self.ensure_defaults()
        statement = select(MCPTool).order_by(MCPTool.server_key.asc(), MCPTool.key.asc())
        if server_key:
            statement = statement.where(MCPTool.server_key == server_key)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_tool(self, tool_key: str) -> MCPTool:
        await self.ensure_defaults()
        return await self._tool_by_key_or_404(tool_key)

    async def _servers(self) -> list[MCPServer]:
        result = await self.session.execute(
            select(MCPServer).order_by(MCPServer.is_critical.desc(), MCPServer.key.asc())
        )
        return list(result.scalars().all())

    async def _servers_by_key(self) -> dict[str, MCPServer]:
        result = await self.session.execute(select(MCPServer))
        return {server.key: server for server in result.scalars().all()}

    async def _server_by_key_or_404(self, server_key: str) -> MCPServer:
        result = await self.session.execute(select(MCPServer).where(MCPServer.key == server_key))
        server = result.scalar_one_or_none()
        if server is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP server not found",
            )
        return server

    async def _tools_by_key(self) -> dict[str, MCPTool]:
        result = await self.session.execute(select(MCPTool))
        return {tool.key: tool for tool in result.scalars().all()}

    async def _tool_by_key_or_404(self, tool_key: str) -> MCPTool:
        result = await self.session.execute(select(MCPTool).where(MCPTool.key == tool_key))
        tool = result.scalar_one_or_none()
        if tool is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP tool not found")
        return tool

    async def _auth_by_server_id(self) -> dict[UUID, MCPAuthConfig]:
        result = await self.session.execute(select(MCPAuthConfig))
        return {auth.server_id: auth for auth in result.scalars().all()}

    async def _tool_counts(self) -> dict[UUID, int]:
        result = await self.session.execute(
            select(MCPTool.server_id, func.count(MCPTool.id)).group_by(MCPTool.server_id)
        )
        return {server_id: int(count) for server_id, count in result.all()}

    def _server_payload(
        self,
        server: MCPServer,
        *,
        tool_count: int,
        auth_config: MCPAuthConfig | None,
    ) -> dict[str, object]:
        return {
            "id": server.id,
            "key": server.key,
            "name": server.name,
            "purpose": server.purpose,
            "adapter_type": server.adapter_type,
            "is_critical": server.is_critical,
            "status": server.status,
            "failure_reason": server.failure_reason,
            "last_tested_at": server.last_tested_at,
            "last_success_at": server.last_success_at,
            "failure_count": server.failure_count,
            "circuit_open_until": server.circuit_open_until,
            "settings": server.settings or {},
            "tool_count": tool_count,
            "auth_config": self._auth_payload(auth_config),
            "created_at": server.created_at,
            "updated_at": server.updated_at,
        }

    def _auth_payload(self, auth_config: MCPAuthConfig | None) -> dict[str, object] | None:
        if auth_config is None:
            return None
        return {
            "id": auth_config.id,
            "server_id": auth_config.server_id,
            "auth_type": auth_config.auth_type,
            "has_secret": auth_config.has_secret,
            "masked_label": auth_config.masked_label,
            "settings": redact_sensitive(auth_config.settings or {}),
            "created_at": auth_config.created_at,
            "updated_at": auth_config.updated_at,
        }


class MCPToolExecutionService(MCPRegistryService):
    def __init__(
        self,
        session: AsyncSession,
        client: BaseMCPClient | None = None,
    ) -> None:
        super().__init__(session)
        self.client = client or MCPRouterClient.default(session)

    async def test_server(
        self,
        server_key: str,
        current_user: CurrentUser,
    ) -> dict[str, object]:
        self._assert_user_can_manage(current_user)
        tool_key, input_payload = self._health_check_tool(server_key)
        run = await self.execute_tool(
            tool_key,
            MCPToolRunRequest(
                input_payload=input_payload,
                caller_type="admin",
                caller_id=str(current_user.id),
                entity_type="mcp_server",
                workflow_stage="connection_test",
            ),
            current_user=current_user,
            commit=False,
        )
        server = await self._server_by_key_or_404(server_key)
        server.last_tested_at = datetime.now(UTC)
        if run.status == MCPToolRunStatus.SUCCEEDED:
            server.status = MCPServerStatus.HEALTHY
            server.failure_reason = None
            server.last_success_at = datetime.now(UTC)
        else:
            server.status = (
                MCPServerStatus.BROKEN if server.is_critical else MCPServerStatus.DEGRADED
            )
            server.failure_reason = run.error_reason
        await self.session.commit()
        return {
            "server": await self.get_server(server_key),
            "run": run,
            "success": run.status == MCPToolRunStatus.SUCCEEDED,
            "message": run.error_reason
            or str((run.output_payload or {}).get("message") or "MCP server test succeeded."),
        }

    async def execute_tool(
        self,
        tool_key: str,
        payload: MCPToolRunRequest,
        *,
        current_user: CurrentUser | None = None,
        retry_of_run: MCPToolRun | None = None,
        commit: bool = True,
    ) -> MCPToolRun:
        await self.ensure_defaults(commit=False)
        tool = await self._tool_by_key_or_404(tool_key)
        server = await self._server_by_key_or_404(tool.server_key)
        if current_user is not None:
            self._assert_user_can_manage(current_user)
        self._assert_tool_runnable(tool, server, payload, current_user)
        self._validate_schema(tool.input_schema, payload.input_payload)

        now = datetime.now(UTC)
        run = MCPToolRun(
            server_id=server.id,
            tool_id=tool.id,
            server_key=server.key,
            tool_key=tool.key,
            status=MCPToolRunStatus.RUNNING,
            caller_type=payload.caller_type,
            caller_id=payload.caller_id,
            requested_by=current_user.id if current_user else None,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            workflow_stage=payload.workflow_stage,
            input_payload=redact_sensitive(payload.input_payload),
            retry_of_run_id=retry_of_run.id if retry_of_run else None,
            attempt_number=(retry_of_run.attempt_number + 1) if retry_of_run else 1,
            started_at=now,
        )
        self.session.add(run)
        await self.session.flush()
        self._audit(
            run,
            tool,
            server,
            action="tool_run_started",
            actor_id=current_user.id if current_user else None,
            message=f"{tool.display_name} started.",
            metadata={"caller_type": payload.caller_type, "input": payload.input_payload},
        )

        try:
            response = await self.client.execute(
                MCPClientRequest(
                    server_key=server.key,
                    tool_key=tool.key,
                    input_payload=payload.input_payload,
                    timeout_ms=tool.timeout_ms,
                    caller_context={
                        "caller_type": payload.caller_type,
                        "caller_id": payload.caller_id,
                        "entity_type": payload.entity_type,
                        "entity_id": str(payload.entity_id) if payload.entity_id else None,
                        "workflow_stage": payload.workflow_stage,
                    },
                )
            )
            self._validate_schema(tool.output_schema, response.output_payload)
            run.status = MCPToolRunStatus.SUCCEEDED
            run.output_payload = redact_sensitive(response.output_payload)
            run.output_metadata = redact_sensitive(response.output_metadata)
            research_run_id = self._research_run_id(response.output_metadata)
            if research_run_id is not None:
                run.research_run_id = research_run_id
                await self.session.execute(
                    update(ResearchRun)
                    .where(ResearchRun.id == research_run_id)
                    .values(mcp_tool_run_id=run.id)
                )
            run.completed_at = datetime.now(UTC)
            server.last_success_at = run.completed_at
            if payload.workflow_stage == "connection_test":
                server.last_tested_at = run.completed_at
            if server.status in {MCPServerStatus.BROKEN, MCPServerStatus.NOT_CONFIGURED}:
                server.status = MCPServerStatus.HEALTHY
                server.failure_reason = None
            apply_circuit_success(server)
            self._audit(
                run,
                tool,
                server,
                action="tool_run_completed",
                actor_id=current_user.id if current_user else None,
                message=f"{tool.display_name} completed successfully.",
                metadata={"output": response.output_payload, "metadata": response.output_metadata},
            )
        except Exception as exc:
            run.status = MCPToolRunStatus.FAILED
            run.error_reason = str(exc)
            run.output_metadata = {"adapter": "unavailable", "error": str(exc)}
            run.completed_at = datetime.now(UTC)
            server.failure_reason = str(exc)
            server.status = (
                MCPServerStatus.BROKEN if server.is_critical else MCPServerStatus.DEGRADED
            )
            apply_circuit_failure(server, tool.circuit_breaker_policy or {})
            self._audit(
                run,
                tool,
                server,
                action="tool_run_failed",
                actor_id=current_user.id if current_user else None,
                message=str(exc),
                metadata={"error": str(exc), "input": payload.input_payload},
            )

        await self.session.flush()
        if commit:
            await self.session.commit()
        await self.session.refresh(run)
        return run

    async def retry_run(
        self,
        run_id: UUID,
        payload: "MCPToolRunRetryRequestLike",
        current_user: CurrentUser,
    ) -> MCPToolRun:
        self._assert_user_can_manage(current_user)
        original = await self._run(run_id)
        retry_payload = MCPToolRunRequest(
            input_payload=payload.input_payload or original.input_payload,
            caller_type=original.caller_type,
            caller_id=original.caller_id,
            entity_type=original.entity_type,
            entity_id=original.entity_id,
            workflow_stage=original.workflow_stage,
        )
        return await self.execute_tool(
            original.tool_key,
            retry_payload,
            current_user=current_user,
            retry_of_run=original,
        )

    async def run_workflow_tool(
        self,
        tool_key: str,
        *,
        input_payload: dict[str, object],
        caller_type: str = "workflow",
        caller_id: str | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        workflow_stage: str | None = None,
        commit: bool = False,
    ) -> MCPToolRun:
        return await self.execute_tool(
            tool_key,
            MCPToolRunRequest(
                input_payload=input_payload,
                caller_type=caller_type,
                caller_id=caller_id,
                entity_type=entity_type,
                entity_id=entity_id,
                workflow_stage=workflow_stage,
            ),
            commit=commit,
        )

    async def list_runs(
        self,
        *,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        tool_key: str | None = None,
        server_key: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, object]:
        await self.ensure_defaults()
        cursor_token = decode_cursor(cursor)
        statement = select(MCPToolRun)
        if entity_type is not None:
            statement = statement.where(MCPToolRun.entity_type == entity_type)
        if entity_id is not None:
            statement = statement.where(MCPToolRun.entity_id == entity_id)
        if tool_key is not None:
            statement = statement.where(MCPToolRun.tool_key == tool_key)
        if server_key is not None:
            statement = statement.where(MCPToolRun.server_key == server_key)
        if cursor_token is not None:
            statement = statement.where(
                or_(
                    MCPToolRun.created_at < cursor_token.created_at,
                    and_(
                        MCPToolRun.created_at == cursor_token.created_at,
                        MCPToolRun.id < cursor_token.id,
                    ),
                )
            )
        statement = statement.order_by(MCPToolRun.created_at.desc(), MCPToolRun.id.desc()).limit(
            limit + 1
        )
        result = await self.session.execute(statement)
        rows = list(result.scalars().all())
        has_next = len(rows) > limit
        items = rows[:limit]
        next_cursor = (
            encode_cursor(items[-1].created_at, items[-1].id) if has_next and items else None
        )
        return {
            "items": items,
            **cursor_meta(
                page_size=limit,
                has_next=has_next,
                next_cursor=next_cursor,
                previous_cursor=None,
            ),
        }

    async def get_run_detail(self, run_id: UUID) -> dict[str, object]:
        run = await self._run(run_id)
        audit_logs = await self._audit_logs(run_id)
        return {**run.__dict__, "audit_logs": audit_logs}

    async def _run(self, run_id: UUID) -> MCPToolRun:
        result = await self.session.execute(select(MCPToolRun).where(MCPToolRun.id == run_id))
        run = result.scalar_one_or_none()
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP tool run not found",
            )
        return run

    async def _audit_logs(self, run_id: UUID) -> list[MCPToolAuditLog]:
        result = await self.session.execute(
            select(MCPToolAuditLog)
            .where(MCPToolAuditLog.run_id == run_id)
            .order_by(MCPToolAuditLog.created_at.asc())
        )
        return list(result.scalars().all())

    def _health_check_tool(self, server_key: str) -> tuple[str, dict[str, object]]:
        if server_key == "buffer":
            return "buffer.test_connection", {}
        if server_key == "research":
            return "research.list_enabled_sources", {}
        if server_key == "llm":
            return "llm.validate_output", {"output": {"summary": "health check"}}
        if server_key == "storage":
            return "storage.get_signed_url", {"path": "health/check.txt"}
        return f"{server_key}.test_connection", {}

    def _assert_tool_runnable(
        self,
        tool: MCPTool,
        server: MCPServer,
        payload: MCPToolRunRequest,
        current_user: CurrentUser | None,
    ) -> None:
        if payload.caller_type not in VALID_CALLER_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MCP caller type",
            )
        if tool.status != MCPToolStatus.ENABLED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"MCP tool {tool.key} is {tool.status.value}.",
            )
        if payload.caller_type not in (tool.allowed_callers or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"MCP tool {tool.key} cannot be called by {payload.caller_type}.",
            )
        if payload.caller_type == "admin":
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
            self._assert_user_can_manage(current_user)
        assert_server_available(server)

    def _assert_user_can_manage(self, current_user: CurrentUser) -> None:
        if not current_user.has_permission("integration.manage"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission required: integration.manage",
            )

    def _validate_schema(self, schema: dict[str, object], payload: dict[str, object]) -> None:
        required = schema.get("required", [])
        if not isinstance(required, list):
            return
        missing = [str(key) for key in required if str(key) not in payload]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"MCP payload missing required field(s): {', '.join(missing)}",
            )
        null_required = [str(key) for key in required if payload.get(str(key)) is None]
        if null_required:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"MCP payload field(s) cannot be null: {', '.join(null_required)}",
            )

        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            return
        for key, value in payload.items():
            property_schema = properties.get(key)
            if not isinstance(property_schema, dict):
                continue
            expected_types = self._schema_types(property_schema.get("type"))
            if expected_types and not self._matches_schema_type(value, expected_types):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"MCP payload field '{key}' must be "
                        f"{self._schema_type_label(expected_types)}"
                    ),
                )

    def _schema_types(self, value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            return (value,)
        if isinstance(value, list):
            return tuple(item for item in value if isinstance(item, str))
        return ()

    def _matches_schema_type(self, value: object, expected_types: tuple[str, ...]) -> bool:
        if value is None:
            return "null" in expected_types
        for expected_type in expected_types:
            if expected_type == "string" and isinstance(value, str):
                return True
            if expected_type == "number" and isinstance(value, int | float) and not isinstance(
                value, bool
            ):
                return True
            if (
                expected_type == "integer"
                and isinstance(value, int)
                and not isinstance(value, bool)
            ):
                return True
            if expected_type == "boolean" and isinstance(value, bool):
                return True
            if expected_type == "object" and isinstance(value, dict):
                return True
            if expected_type == "array" and isinstance(value, list):
                return True
        return False

    def _schema_type_label(self, expected_types: tuple[str, ...]) -> str:
        if len(expected_types) == 1:
            return expected_types[0]
        return " or ".join(expected_types)

    def _research_run_id(self, metadata: dict[str, object]) -> UUID | None:
        value = metadata.get("research_run_id")
        if value in (None, ""):
            return None
        try:
            return UUID(str(value))
        except ValueError:
            return None

    def _audit(
        self,
        run: MCPToolRun,
        tool: MCPTool,
        server: MCPServer,
        *,
        action: str,
        actor_id: UUID | None,
        message: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.session.add(
            MCPToolAuditLog(
                run_id=run.id,
                server_id=server.id,
                tool_id=tool.id,
                action=action,
                actor_id=actor_id,
                message=message,
                metadata_payload=redact_sensitive(metadata or {}),
            )
        )


class MCPToolRunRetryRequestLike:
    input_payload: dict[str, object] | None
