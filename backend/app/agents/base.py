from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class AgentContext(BaseModel):
    correlation_id: str
    workspace_id: str | None = None
    actor_id: str | None = None
    prompt_version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel, Generic[OutputT]):
    output: OutputT
    audit_notes: list[str] = Field(default_factory=list)
    tool_call_ids: list[str] = Field(default_factory=list)


class BaseAgent(ABC, Generic[InputT, OutputT]):
    agent_id: str

    @abstractmethod
    async def run(self, input_data: InputT, context: AgentContext) -> AgentResult[OutputT]:
        raise NotImplementedError
