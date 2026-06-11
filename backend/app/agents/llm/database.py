from collections.abc import Awaitable, Callable, Mapping
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm.base import LLMRequest, LLMResponse
from app.agents.llm.gemini import GeminiLLMProvider
from app.agents.llm.grok import GrokLLMProvider
from app.agents.llm.groq import GroqLLMProvider
from app.agents.llm.openai import OpenAILLMProvider
from app.db.types import ResearchSourceProviderType
from app.modules.research_sources.models import ResearchSource
from app.modules.research_sources.service import ResearchSourceService
from app.research.providers.credentials import ResearchCredentialProvider

LLMProvider = OpenAILLMProvider | GeminiLLMProvider | GrokLLMProvider | GroqLLMProvider
T = TypeVar("T")


class DatabaseLLMProvider:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.credential_provider = ResearchCredentialProvider()

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return await self._with_fallback(
            lambda provider: provider.generate(request),
        )

    async def generate_text(
        self,
        prompt: str,
        *,
        context: Mapping[str, object] | None = None,
    ) -> LLMResponse:
        return await self._with_fallback(
            lambda provider: provider.generate_text(prompt, context=context),
        )

    async def generate_json(self, prompt: str) -> dict[str, object]:
        return await self._with_fallback(
            lambda provider: provider.generate_json(prompt),
        )

    async def validate_output(self, output: Mapping[str, object]) -> LLMResponse:
        return await self._with_fallback(
            lambda provider: provider.validate_output(output),
        )

    async def _with_fallback(
        self,
        operation: Callable[[LLMProvider], Awaitable[T]],
    ) -> T:
        providers = await self._configured_providers()
        if not providers:
            raise RuntimeError(
                "OpenAI, Gemini, Groq, or Grok API key must be configured in Integrations."
            )

        failures: list[str] = []
        for label, provider in providers:
            try:
                return await operation(provider)
            except RuntimeError as exc:
                failures.append(f"{label}: {exc}")
        raise RuntimeError(f"LLM providers failed: {'; '.join(failures)}")

    async def _configured_providers(self) -> list[tuple[str, LLMProvider]]:
        await ResearchSourceService(self.session).ensure_defaults()
        providers: list[tuple[str, LLMProvider]] = []
        openai = await self._provider_for(ResearchSourceProviderType.OPENAI)
        if openai is not None:
            providers.append(("openai", openai))
        gemini = await self._provider_for(ResearchSourceProviderType.GEMINI)
        if gemini is not None:
            providers.append(("gemini", gemini))
        groq = await self._provider_for(ResearchSourceProviderType.GROQ)
        if groq is not None:
            providers.append(("groq", groq))
        grok = await self._provider_for(ResearchSourceProviderType.GROK_X)
        if grok is not None:
            providers.append(("grok", grok))
        return providers

    async def _provider_for(
        self,
        provider_type: ResearchSourceProviderType,
    ) -> LLMProvider | None:
        result = await self.session.execute(
            select(ResearchSource).where(ResearchSource.provider_type == provider_type)
        )
        source = result.scalar_one_or_none()
        if source is None or not source.enabled:
            return None
        credential = self.credential_provider.credential_for(
            source.provider_type,
            source.config_json,
        )
        if not credential.is_configured:
            return None
        if provider_type == ResearchSourceProviderType.OPENAI:
            return OpenAILLMProvider(api_key=credential.value)
        if provider_type == ResearchSourceProviderType.GROK_X:
            return GrokLLMProvider(api_key=credential.value)
        if provider_type == ResearchSourceProviderType.GROQ:
            return GroqLLMProvider(api_key=credential.value)
        return GeminiLLMProvider(api_key=credential.value)


class DatabaseGeminiLLMProvider(DatabaseLLMProvider):
    """Backward-compatible name for the DB-backed LLM provider."""
