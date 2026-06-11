from collections.abc import Mapping
from typing import Protocol

from app.agents.llm.base import LLMResponse
from app.mcp.client.base import MCPClientRequest, MCPClientResponse


class LLMProvider(Protocol):
    async def generate_text(
        self,
        prompt: str,
        *,
        context: Mapping[str, object],
    ) -> LLMResponse:
        ...

    async def validate_output(self, output: Mapping[str, object]) -> LLMResponse:
        ...


class LLMMCPAdapter:
    """MCP adapter for DB-configured LLM tools."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        if provider is None:
            from app.agents.llm.gemini import GeminiLLMProvider

            provider = GeminiLLMProvider()
        self.provider = provider

    async def execute(self, request: MCPClientRequest) -> MCPClientResponse:
        if request.tool_key == "llm.generate_text":
            prompt = str(request.input_payload.get("prompt") or "")
            response = await self.provider.generate_text(
                prompt,
                context={
                    "input": request.input_payload,
                    "caller_context": request.caller_context,
                },
            )
            return MCPClientResponse(
                output_payload=response.output,
                output_metadata={
                    "adapter": "llm",
                    **response.metadata,
                },
            )

        if request.tool_key == "llm.validate_output":
            output = request.input_payload.get("output")
            if not isinstance(output, dict):
                output = {"value": output}
            response = await self.provider.validate_output(output)
            return MCPClientResponse(
                output_payload=response.output,
                output_metadata={
                    "adapter": "llm",
                    **response.metadata,
                },
            )

        raise RuntimeError(f"Unsupported LLM MCP tool: {request.tool_key}")
