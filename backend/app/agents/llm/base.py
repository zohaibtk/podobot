from typing import Protocol

from pydantic import BaseModel, Field


class LLMRequest(BaseModel):
    agent_key: str
    prompt_key: str
    prompt_version: int
    template_body: str
    input_payload: dict[str, object] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    output: dict[str, object]
    metadata: dict[str, object] = Field(default_factory=dict)


class BaseLLMProvider(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate structured output for an agent request."""
