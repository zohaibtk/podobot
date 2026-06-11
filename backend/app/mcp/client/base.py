from typing import Protocol

from pydantic import BaseModel, Field


class MCPClientRequest(BaseModel):
    server_key: str
    tool_key: str
    input_payload: dict[str, object] = Field(default_factory=dict)
    timeout_ms: int = 30_000
    caller_context: dict[str, object] = Field(default_factory=dict)


class MCPClientResponse(BaseModel):
    output_payload: dict[str, object] = Field(default_factory=dict)
    output_metadata: dict[str, object] = Field(default_factory=dict)


class BaseMCPClient(Protocol):
    async def execute(self, request: MCPClientRequest) -> MCPClientResponse:
        """Execute an MCP tool through a concrete server adapter."""
