from collections.abc import Mapping
from dataclasses import dataclass

from app.db.types import ResearchSourceProviderType
from app.research.providers.base import ProviderMode
from app.security.secrets import SecretDecryptionError, decrypt_secret, is_encrypted_secret


@dataclass(frozen=True)
class ProviderCredential:
    env_name: str | None
    value: str | None
    required: bool

    @property
    def is_configured(self) -> bool:
        return not self.required or bool(self.value)


class ResearchCredentialProvider:
    def credential_for(
        self,
        provider_type: ResearchSourceProviderType,
        source_config: Mapping[str, object] | None = None,
    ) -> ProviderCredential:
        source_key = self._source_secret(source_config)
        if provider_type == ResearchSourceProviderType.YOUTUBE_DATA_API:
            return ProviderCredential("YouTube API key", source_key, True)
        if provider_type == ResearchSourceProviderType.EXA:
            return ProviderCredential("Exa API key", source_key, True)
        if provider_type == ResearchSourceProviderType.FIRECRAWL:
            return ProviderCredential("Firecrawl API key", source_key, True)
        if provider_type == ResearchSourceProviderType.SERPAPI:
            return ProviderCredential("SerpAPI key", source_key, True)
        if provider_type == ResearchSourceProviderType.OPENAI:
            return ProviderCredential("OpenAI API key", source_key, True)
        if provider_type == ResearchSourceProviderType.GEMINI:
            return ProviderCredential("Gemini API key", source_key, True)
        if provider_type == ResearchSourceProviderType.GROK_X:
            return ProviderCredential("Grok API key", source_key, True)
        if provider_type == ResearchSourceProviderType.GROQ:
            return ProviderCredential("Groq API key", source_key, True)
        return ProviderCredential(None, None, False)

    def provider_mode(
        self,
        provider_type: ResearchSourceProviderType,
        source_config: Mapping[str, object] | None = None,
    ) -> ProviderMode:
        credential = self.credential_for(provider_type, source_config)
        if credential.is_configured:
            return ProviderMode.REAL
        return ProviderMode.UNAVAILABLE

    def missing_configuration(
        self,
        provider_type: ResearchSourceProviderType,
        source_config: Mapping[str, object] | None = None,
    ) -> bool:
        credential = self.credential_for(provider_type, source_config)
        return credential.required and not credential.value

    def safe_configuration_status(
        self,
        provider_type: ResearchSourceProviderType,
        source_config: Mapping[str, object] | None = None,
    ) -> str:
        if self._source_secret(source_config):
            return "source_api_key_configured"
        credential = self.credential_for(provider_type, source_config)
        if not credential.required:
            return "no_credentials_required"
        if credential.value:
            return "source_api_key_configured"
        if credential.env_name is None:
            return "future_credentials_required"
        return "database_api_key_missing"

    def _source_secret(self, source_config: Mapping[str, object] | None) -> str | None:
        if not source_config:
            return None
        value = source_config.get("api_key_ciphertext")
        if is_encrypted_secret(value):
            try:
                return decrypt_secret(str(value))
            except SecretDecryptionError:
                return None
        return None
