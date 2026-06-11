from pydantic import BaseModel, Field


class AgentSpec(BaseModel):
    agent_id: str
    display_name: str
    responsibility: str
    allowed_tools: list[str] = Field(default_factory=list)
    active_prompt_version: str | None = None
    enabled: bool = False


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, AgentSpec] = {}

    def register(self, spec: AgentSpec) -> None:
        self._agents[spec.agent_id] = spec

    def get(self, agent_id: str) -> AgentSpec:
        return self._agents[agent_id]

    def list(self) -> list[AgentSpec]:
        return list(self._agents.values())
