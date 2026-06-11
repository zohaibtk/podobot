from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from app.db.types import MCPServerStatus
from app.mcp.models import MCPServer


def circuit_is_open(server: MCPServer) -> bool:
    return bool(server.circuit_open_until and server.circuit_open_until > datetime.now(UTC))


def assert_server_available(server: MCPServer) -> None:
    if server.status == MCPServerStatus.DISABLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"MCP server {server.key} is disabled.",
        )
    if circuit_is_open(server):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"MCP server {server.key} circuit breaker is open.",
        )
    if server.is_critical and server.status == MCPServerStatus.BROKEN:
        reason = server.failure_reason or "critical MCP server is broken"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Critical MCP server {server.key} blocks this workflow: {reason}",
        )


def apply_circuit_failure(server: MCPServer, policy: dict[str, object]) -> None:
    threshold = max(1, int(policy.get("failure_threshold", 3)))
    cooldown_seconds = max(1, int(policy.get("cooldown_seconds", 300)))
    server.failure_count += 1
    if server.failure_count >= threshold:
        server.circuit_open_until = datetime.now(UTC) + timedelta(seconds=cooldown_seconds)


def apply_circuit_success(server: MCPServer) -> None:
    server.failure_count = 0
    server.circuit_open_until = None
