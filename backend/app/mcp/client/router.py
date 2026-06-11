from app.mcp.adapters.llm import LLMMCPAdapter
from app.mcp.adapters.research import ResearchMCPAdapter
from app.mcp.client.base import BaseMCPClient, MCPClientRequest, MCPClientResponse


class MCPRouterClient:
    def __init__(
        self,
        *,
        research_client: BaseMCPClient,
        llm_client: BaseMCPClient | None = None,
    ) -> None:
        self.research_client = research_client
        self.llm_client = llm_client or LLMMCPAdapter()

    @classmethod
    def default(cls, session: object) -> "MCPRouterClient":
        from app.agents.llm.database import DatabaseLLMProvider

        return cls(
            research_client=ResearchMCPAdapter(session),
            llm_client=LLMMCPAdapter(DatabaseLLMProvider(session)),
        )

    async def execute(self, request: MCPClientRequest) -> MCPClientResponse:
        if request.tool_key.startswith("llm."):
            return await self.llm_client.execute(request)
        return await self.research_client.execute(request)
