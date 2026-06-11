from app.agents.llm.base import LLMRequest, LLMResponse


class UnavailableLLMProvider:
    async def generate(self, request: LLMRequest) -> LLMResponse:
        raise RuntimeError("No production LLM provider is configured.")
