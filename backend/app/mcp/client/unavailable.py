from datetime import UTC, datetime

from app.mcp.client.base import MCPClientRequest, MCPClientResponse


class UnavailableMCPClient:
    async def execute(self, request: MCPClientRequest) -> MCPClientResponse:
        if request.input_payload.get("force_failure") is True:
            raise RuntimeError(f"MCP failure requested for {request.tool_key}")
        raise RuntimeError(f"No production MCP adapter is configured for {request.tool_key}.")

    def _response(
        self,
        output_payload: dict[str, object],
        output_metadata: dict[str, object] | None = None,
    ) -> MCPClientResponse:
        return MCPClientResponse(
            output_payload=output_payload,
            output_metadata={
                "adapter": "production",
                "executed_at": datetime.now(UTC).isoformat(),
                **(output_metadata or {}),
            },
        )
