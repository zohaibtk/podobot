import json
import os
from pathlib import Path

from pydantic import Field, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POSTGRES_PASSWORD = "podobot"
DEFAULT_BUFFER_WEBHOOK_SECRET = "podobot-buffer-webhook-development-secret"
DEFAULT_AUTH_JWT_SECRET = "podobot-development-secret-change-me"
DEFAULT_AUTH_DEV_ADMIN_PASSWORD = "admin"


def default_local_storage_root() -> str:
    if os.getenv("VERCEL"):
        return "/tmp/podobot-storage"
    return str(REPOSITORY_ROOT / ".local/storage")


def is_tmp_path(path: Path) -> bool:
    tmp_root = Path("/tmp").resolve()
    resolved_path = path.resolve()
    return resolved_path == tmp_root or tmp_root in resolved_path.parents


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PodoBot API"
    app_version: str = "0.1.0"
    environment: str = Field(default="development")
    api_prefix: str = "/api"
    enable_openapi: bool = True
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    cors_origin_regex: str | None = None

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "podobot"
    postgres_user: str = "podobot"
    postgres_password: str = DEFAULT_POSTGRES_PASSWORD
    database_url_override: str | None = None
    database_pool_size: int = Field(default=20, ge=1)
    database_max_overflow: int = Field(default=20, ge=0)
    database_pool_timeout_seconds: int = Field(default=10, ge=1)
    database_pool_recycle_seconds: int = Field(default=3600, ge=1)

    redis_url: RedisDsn = "redis://localhost:6379/0"
    celery_result_backend_url: RedisDsn = "redis://localhost:6379/1"

    local_storage_root: str = Field(default_factory=default_local_storage_root)
    max_upload_bytes: int = 5_368_709_120
    media_signed_url_seconds: int = 900
    media_upload_chunk_bytes: int = 1_048_576

    buffer_api_base_url: str = "https://api.buffer.com"
    buffer_auth_url: str = "https://auth.buffer.com/auth"
    buffer_token_url: str = "https://auth.buffer.com/oauth/token"
    buffer_client_id: str | None = None
    buffer_client_secret: str | None = None
    buffer_redirect_uri: str = "http://localhost:8000/api/v1/buffer/oauth/callback"
    buffer_webhook_secret: str = DEFAULT_BUFFER_WEBHOOK_SECRET
    buffer_request_timeout_seconds: int = 20
    buffer_max_publish_retries: int = 3
    buffer_access_token: str | None = None

    gemini_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_fallback_models: str = (
        "gpt-4o-mini,gpt-4o,gpt-4.1-nano,gpt-4-turbo,gpt-4,"
        "gpt-3.5-turbo,o4-mini,o3-mini,o3,o1"
    )
    openai_api_base_url: str = "https://api.openai.com/v1"
    gemini_model: str = "gemini-2.5-flash"
    grok_model: str = "grok-latest"
    grok_api_base_url: str = "https://api.x.ai/v1"
    groq_model: str = "llama-3.3-70b-versatile"
    groq_api_base_url: str = "https://api.groq.com/openai/v1"
    youtube_api_key: str | None = None
    exa_api_key: str | None = None
    serpapi_key: str | None = None
    firecrawl_api_key: str | None = None
    secrets_encryption_key: str | None = None

    auth_jwt_secret: str = DEFAULT_AUTH_JWT_SECRET
    auth_access_token_minutes: int = 60
    auth_refresh_token_days: int = 14
    auth_dev_auto_login: bool = False
    auth_dev_admin_password: str = DEFAULT_AUTH_DEV_ADMIN_PASSWORD

    log_level: str = "INFO"

    @field_validator("local_storage_root", mode="after")
    @classmethod
    def resolve_local_storage_root(cls, value: str) -> str:
        path = Path(value)
        if os.getenv("VERCEL"):
            if path.is_absolute():
                if is_tmp_path(path):
                    return str(path)
                return "/tmp/podobot-storage"
            return str(Path("/tmp") / path)
        if path.is_absolute():
            return str(path)
        return str(REPOSITORY_ROOT / path)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        cleaned = value.strip()
        if not cleaned:
            return []
        if cleaned.startswith("["):
            return json.loads(cleaned)
        return [origin.strip() for origin in cleaned.split(",") if origin.strip()]

    @model_validator(mode="after")
    def reject_unsafe_production_defaults(self) -> "Settings":
        if self.environment.lower() != "production":
            return self

        unsafe_settings = []
        if self.auth_jwt_secret == DEFAULT_AUTH_JWT_SECRET:
            unsafe_settings.append("auth_jwt_secret")
        if self.auth_dev_auto_login:
            unsafe_settings.append("auth_dev_auto_login")
        if self.buffer_webhook_secret == DEFAULT_BUFFER_WEBHOOK_SECRET:
            unsafe_settings.append("buffer_webhook_secret")
        if self.auth_dev_admin_password == DEFAULT_AUTH_DEV_ADMIN_PASSWORD:
            unsafe_settings.append("auth_dev_admin_password")
        if not self.secrets_encryption_key and self.auth_jwt_secret == DEFAULT_AUTH_JWT_SECRET:
            unsafe_settings.append("secrets_encryption_key")
        if not self.database_url_override and self.postgres_password == DEFAULT_POSTGRES_PASSWORD:
            unsafe_settings.append("postgres_password")

        if unsafe_settings:
            joined = ", ".join(unsafe_settings)
            raise ValueError(f"Unsafe production configuration: {joined}")
        return self

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override

        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
