from app.mcp.schemas.base import McpToolDefinition


class McpToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, McpToolDefinition] = {}

    def register(self, tool: McpToolDefinition) -> None:
        self._tools[tool.name] = tool

    def list(self) -> list[McpToolDefinition]:
        return list(self._tools.values())
