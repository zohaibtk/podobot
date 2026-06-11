from dataclasses import dataclass

from app.core.config import settings
from app.db.types import MCPServerStatus, MCPToolStatus


@dataclass(frozen=True)
class MCPServerDefault:
    key: str
    name: str
    purpose: str
    is_critical: bool
    adapter_type: str = "unavailable"
    status: MCPServerStatus = MCPServerStatus.HEALTHY
    auth_type: str = "none"
    secret_ref: str | None = None
    masked_label: str | None = None
    settings: dict[str, object] | None = None


@dataclass(frozen=True)
class MCPToolDefault:
    key: str
    server_key: str
    display_name: str
    description: str
    input_schema: dict[str, object]
    output_schema: dict[str, object]
    auth_required: bool
    timeout_ms: int = 30_000
    retry_policy: dict[str, object] | None = None
    circuit_breaker_policy: dict[str, object] | None = None
    is_critical: bool = False
    allowed_callers: list[str] | None = None
    status: MCPToolStatus = MCPToolStatus.ENABLED


def object_schema(
    required: list[str] | None = None,
    properties: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "type": "object",
        "required": required or [],
        "properties": properties or {},
        "additionalProperties": True,
    }


def string_input_schema(required: list[str]) -> dict[str, object]:
    return object_schema(
        required,
        {key: {"type": "string"} for key in required},
    )


def numeric_input_schema(required: list[str]) -> dict[str, object]:
    return object_schema(
        required,
        {key: {"type": "number"} for key in required},
    )


DEFAULT_MCP_SERVERS = [
    MCPServerDefault(
        key="buffer",
        name="Buffer",
        purpose="Publishing and schedule management.",
        is_critical=True,
        auth_type="bearer",
        secret_ref="integration:buffer",
        masked_label="buf_****_key",
        adapter_type="buffer",
        settings={"mode": "production"},
    ),
    MCPServerDefault(
        key="research",
        name="Research",
        purpose="Provider-registry research access, scraping, trends, and classification.",
        is_critical=False,
        status=MCPServerStatus.DEGRADED,
        adapter_type="provider_registry",
        settings={"mode": "provider_registry", "fallback": False},
    ),
    MCPServerDefault(
        key="llm",
        name="LLM",
        purpose=(
            "OpenAI-first LLM execution with Gemini and Groq fallback for agents "
            "and workflow tools."
        ),
        is_critical=True,
        adapter_type="gemini",
        status=MCPServerStatus.HEALTHY,
        settings={
            "mode": "openai_with_llm_fallbacks",
            "primary_model": settings.openai_model,
            "fallback_model": settings.gemini_model,
            "secondary_fallback_model": settings.groq_model,
            "final_fallback_model": settings.grok_model,
        },
    ),
    MCPServerDefault(
        key="storage",
        name="Local Storage",
        purpose="Object/file storage operations.",
        is_critical=True,
        adapter_type="local_filesystem",
        settings={"mode": "local_filesystem"},
    ),
]


DEFAULT_RETRY_POLICY = {"max_attempts": 2, "backoff_ms": 250}
DEFAULT_CIRCUIT_POLICY = {"failure_threshold": 3, "cooldown_seconds": 300}


DEFAULT_MCP_TOOLS = [
    MCPToolDefault(
        key="buffer.test_connection",
        server_key="buffer",
        display_name="Test Buffer connection",
        description="Validate Buffer availability through the MCP publishing adapter.",
        input_schema=object_schema(),
        output_schema=object_schema(["success", "message"]),
        auth_required=True,
        is_critical=True,
        allowed_callers=["agent", "admin", "system"],
    ),
    MCPToolDefault(
        key="buffer.list_channels",
        server_key="buffer",
        display_name="List Buffer channels",
        description="Return available Buffer publishing channels.",
        input_schema=object_schema(),
        output_schema=object_schema(["channels"]),
        auth_required=True,
        is_critical=True,
        allowed_callers=["workflow", "admin", "system"],
    ),
    MCPToolDefault(
        key="buffer.create_scheduled_post",
        server_key="buffer",
        display_name="Create scheduled Buffer post",
        description="Create one scheduled post for a captioned video/platform row.",
        input_schema=string_input_schema(["caption_id", "platform", "scheduled_for", "text"]),
        output_schema=object_schema(["post_id", "status"]),
        auth_required=True,
        is_critical=True,
        allowed_callers=["workflow", "agent", "system"],
    ),
    MCPToolDefault(
        key="buffer.update_scheduled_post",
        server_key="buffer",
        display_name="Update scheduled Buffer post",
        description="Edit scheduled Buffer post copy or time.",
        input_schema=string_input_schema(["post_id", "platform", "scheduled_for", "text"]),
        output_schema=object_schema(["post_id", "status"]),
        auth_required=True,
        is_critical=True,
        allowed_callers=["workflow", "agent", "system"],
    ),
    MCPToolDefault(
        key="buffer.cancel_scheduled_post",
        server_key="buffer",
        display_name="Cancel scheduled Buffer post",
        description="Cancel a scheduled post in Buffer.",
        input_schema=string_input_schema(["post_id"]),
        output_schema=object_schema(["post_id", "status"]),
        auth_required=True,
        is_critical=True,
        allowed_callers=["workflow", "agent", "system"],
    ),
    MCPToolDefault(
        key="buffer.get_post_status",
        server_key="buffer",
        display_name="Get Buffer post status",
        description="Synchronize Buffer post publishing status.",
        input_schema=string_input_schema(["post_id", "scheduled_for", "platform", "text"]),
        output_schema=object_schema(["post_id", "status"]),
        auth_required=True,
        is_critical=True,
        allowed_callers=["workflow", "agent", "system"],
    ),
    MCPToolDefault(
        key="research.list_enabled_sources",
        server_key="research",
        display_name="List enabled research sources",
        description="Return enabled research sources with provider mode and health status.",
        input_schema=object_schema(),
        output_schema=object_schema(["sources"]),
        auth_required=False,
        timeout_ms=10_000,
        retry_policy=DEFAULT_RETRY_POLICY,
        circuit_breaker_policy=DEFAULT_CIRCUIT_POLICY,
        allowed_callers=["workflow", "agent", "admin", "system"],
    ),
    MCPToolDefault(
        key="research.test_source_connection",
        server_key="research",
        display_name="Test research source connection",
        description="Resolve a source through the provider registry and test the adapter.",
        input_schema=string_input_schema(["source_key"]),
        output_schema=object_schema(["source", "success", "message"]),
        auth_required=False,
        timeout_ms=20_000,
        retry_policy=DEFAULT_RETRY_POLICY,
        circuit_breaker_policy=DEFAULT_CIRCUIT_POLICY,
        allowed_callers=["workflow", "agent", "admin", "system"],
    ),
    MCPToolDefault(
        key="research.search_sources",
        server_key="research",
        display_name="Search research sources",
        description="Search enabled research sources through provider adapters.",
        input_schema=string_input_schema(["query"]),
        output_schema=object_schema(["results"]),
        auth_required=False,
        timeout_ms=30_000,
        retry_policy=DEFAULT_RETRY_POLICY,
        circuit_breaker_policy=DEFAULT_CIRCUIT_POLICY,
        allowed_callers=["workflow", "agent", "admin", "system"],
    ),
    MCPToolDefault(
        key="research.fetch_resource",
        server_key="research",
        display_name="Fetch research resource",
        description="Fetch a normalized resource by URL or provider identifier.",
        input_schema=string_input_schema(["resource_id_or_url"]),
        output_schema=object_schema(["document"]),
        auth_required=False,
        timeout_ms=30_000,
        retry_policy=DEFAULT_RETRY_POLICY,
        circuit_breaker_policy=DEFAULT_CIRCUIT_POLICY,
        allowed_callers=["workflow", "agent", "admin", "system"],
    ),
    MCPToolDefault(
        key="research.fetch_source",
        server_key="research",
        display_name="Fetch research source",
        description="Backward-compatible alias for fetching one source document by URL or ID.",
        input_schema=string_input_schema(["source"]),
        output_schema=object_schema(["source", "content"]),
        auth_required=False,
        timeout_ms=30_000,
        retry_policy=DEFAULT_RETRY_POLICY,
        circuit_breaker_policy=DEFAULT_CIRCUIT_POLICY,
        allowed_callers=["workflow", "agent", "system"],
    ),
    MCPToolDefault(
        key="research.scrape_resource",
        server_key="research",
        display_name="Scrape research resource",
        description="Scrape a URL through Firecrawl and return normalized page content.",
        input_schema=string_input_schema(["url"]),
        output_schema=object_schema(["document"]),
        auth_required=False,
        timeout_ms=45_000,
        retry_policy={"max_attempts": 2, "backoff_ms": 500},
        circuit_breaker_policy=DEFAULT_CIRCUIT_POLICY,
        allowed_callers=["workflow", "agent", "admin", "system"],
    ),
    MCPToolDefault(
        key="research.get_trend_score",
        server_key="research",
        display_name="Get trend score",
        description=(
            "Use SerpAPI trends with pytrends fallback and return a nonblocking trend result."
        ),
        input_schema=string_input_schema(["query"]),
        output_schema=object_schema(["trend_available"]),
        auth_required=False,
        timeout_ms=20_000,
        retry_policy=DEFAULT_RETRY_POLICY,
        circuit_breaker_policy=DEFAULT_CIRCUIT_POLICY,
        allowed_callers=["workflow", "agent", "admin", "system"],
    ),
    MCPToolDefault(
        key="research.calculate_provider_scores",
        server_key="research",
        display_name="Calculate provider scores",
        description="Return provider-specific scoring inputs without composite PRD scoring.",
        input_schema=object_schema(
            ["normalized_result"],
            {"normalized_result": {"type": "object"}},
        ),
        output_schema=object_schema(["scores"]),
        auth_required=False,
        timeout_ms=10_000,
        retry_policy=DEFAULT_RETRY_POLICY,
        circuit_breaker_policy=DEFAULT_CIRCUIT_POLICY,
        allowed_callers=["workflow", "agent", "admin", "system"],
    ),
    MCPToolDefault(
        key="research.calculate_composite_score",
        server_key="research",
        display_name="Calculate composite score",
        description="Apply the PRD composite score formula to normalized component scores.",
        input_schema=numeric_input_schema(
            ["tier_score", "engagement_score", "freshness_score", "author_score"]
        ),
        output_schema=object_schema(["composite_score", "confidence_level", "explanation"]),
        auth_required=False,
        timeout_ms=10_000,
        retry_policy=DEFAULT_RETRY_POLICY,
        circuit_breaker_policy=DEFAULT_CIRCUIT_POLICY,
        allowed_callers=["workflow", "agent", "admin", "system"],
    ),
    MCPToolDefault(
        key="research.explain_score",
        server_key="research",
        display_name="Explain research score",
        description="Return human-readable and JSON score formula explanation.",
        input_schema=numeric_input_schema(
            ["tier_score", "engagement_score", "freshness_score", "author_score"]
        ),
        output_schema=object_schema(["formula", "composite_score", "confidence_level"]),
        auth_required=False,
        timeout_ms=10_000,
        retry_policy=DEFAULT_RETRY_POLICY,
        circuit_breaker_policy=DEFAULT_CIRCUIT_POLICY,
        allowed_callers=["workflow", "agent", "admin", "system"],
    ),
    MCPToolDefault(
        key="research.score_document",
        server_key="research",
        display_name="Score research document",
        description="Score one persisted research document and store its explanation.",
        input_schema=string_input_schema(["document_id"]),
        output_schema=object_schema(["document_id", "composite_score", "confidence_level"]),
        auth_required=False,
        timeout_ms=20_000,
        retry_policy=DEFAULT_RETRY_POLICY,
        circuit_breaker_policy=DEFAULT_CIRCUIT_POLICY,
        allowed_callers=["workflow", "agent", "admin", "system"],
    ),
    MCPToolDefault(
        key="research.score_run_documents",
        server_key="research",
        display_name="Score run documents",
        description="Score every document in a persisted research run.",
        input_schema=string_input_schema(["run_id"]),
        output_schema=object_schema(["success", "score_summary"]),
        auth_required=False,
        timeout_ms=45_000,
        retry_policy=DEFAULT_RETRY_POLICY,
        circuit_breaker_policy=DEFAULT_CIRCUIT_POLICY,
        allowed_callers=["workflow", "agent", "admin", "system"],
    ),
    MCPToolDefault(
        key="research.score_entity_evidence",
        server_key="research",
        display_name="Score entity evidence",
        description="Aggregate confidence from linked research documents for an entity.",
        input_schema=string_input_schema(["entity_type", "entity_id"]),
        output_schema=object_schema(["entity_type", "composite_score", "confidence_level"]),
        auth_required=False,
        timeout_ms=20_000,
        retry_policy=DEFAULT_RETRY_POLICY,
        circuit_breaker_policy=DEFAULT_CIRCUIT_POLICY,
        allowed_callers=["workflow", "agent", "admin", "system"],
    ),
    MCPToolDefault(
        key="research.extract_signals",
        server_key="research",
        display_name="Extract research signals",
        description="Extract evidence signals from fetched research content.",
        input_schema=string_input_schema(["content"]),
        output_schema=object_schema(["signals"]),
        auth_required=False,
        timeout_ms=30_000,
        retry_policy=DEFAULT_RETRY_POLICY,
        circuit_breaker_policy=DEFAULT_CIRCUIT_POLICY,
        allowed_callers=["workflow", "agent", "system"],
    ),
    MCPToolDefault(
        key="llm.generate_text",
        server_key="llm",
        display_name="Generate text",
        description="Generate structured text through the provider-agnostic LLM adapter.",
        input_schema=string_input_schema(["prompt"]),
        output_schema=object_schema(["text", "confidence"]),
        auth_required=False,
        is_critical=True,
        allowed_callers=["workflow", "agent", "system"],
    ),
    MCPToolDefault(
        key="llm.validate_output",
        server_key="llm",
        display_name="Validate output",
        description="Validate structured model output against quality checks.",
        input_schema=object_schema(["output"], {"output": {"type": "object"}}),
        output_schema=object_schema(["valid", "checks"]),
        auth_required=False,
        is_critical=True,
        allowed_callers=["workflow", "agent", "admin", "system"],
    ),
    MCPToolDefault(
        key="storage.upload_file",
        server_key="storage",
        display_name="Upload file",
        description="Store a file through the local storage adapter contract.",
        input_schema=string_input_schema(["path"]),
        output_schema=object_schema(["path", "stored"]),
        auth_required=False,
        is_critical=True,
        allowed_callers=["workflow", "system"],
    ),
    MCPToolDefault(
        key="storage.get_signed_url",
        server_key="storage",
        display_name="Get signed URL",
        description="Return a local signed URL for stored assets.",
        input_schema=string_input_schema(["path"]),
        output_schema=object_schema(["url", "expires_at"]),
        auth_required=False,
        is_critical=True,
        allowed_callers=["workflow", "admin", "system"],
    ),
    MCPToolDefault(
        key="storage.delete_file",
        server_key="storage",
        display_name="Delete file",
        description="Delete a file through the local storage adapter contract.",
        input_schema=string_input_schema(["path"]),
        output_schema=object_schema(["deleted"]),
        auth_required=False,
        is_critical=True,
        allowed_callers=["workflow", "system"],
    ),
]
