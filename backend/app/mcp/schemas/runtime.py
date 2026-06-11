from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.db.types import MCPServerStatus, MCPToolRunStatus, MCPToolStatus
from app.schemas.pagination import CursorPageResponse


class MCPAuthConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    server_id: UUID
    auth_type: str
    has_secret: bool
    masked_label: str | None
    settings: dict[str, object]
    created_at: datetime
    updated_at: datetime


class MCPServerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    name: str
    purpose: str
    adapter_type: str
    is_critical: bool
    status: MCPServerStatus
    failure_reason: str | None
    last_tested_at: datetime | None
    last_success_at: datetime | None
    failure_count: int
    circuit_open_until: datetime | None
    settings: dict[str, object]
    tool_count: int = 0
    auth_config: MCPAuthConfigResponse | None = None
    created_at: datetime
    updated_at: datetime


class MCPToolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    server_id: UUID
    server_key: str
    key: str
    display_name: str
    description: str
    input_schema: dict[str, object]
    output_schema: dict[str, object]
    auth_required: bool
    timeout_ms: int
    retry_policy: dict[str, object]
    circuit_breaker_policy: dict[str, object]
    is_critical: bool
    allowed_callers: list[str]
    status: MCPToolStatus
    created_at: datetime
    updated_at: datetime


class MCPToolRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_payload: dict[str, object] = Field(default_factory=dict)
    caller_type: str = Field(default="admin", pattern="^(workflow|agent|admin|system)$")
    caller_id: str | None = Field(default=None, max_length=160)
    entity_type: str | None = Field(default=None, max_length=80)
    entity_id: UUID | None = None
    workflow_stage: str | None = Field(default=None, max_length=80)


class MCPToolRunRetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_payload: dict[str, object] | None = None


class MCPToolRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    server_id: UUID
    tool_id: UUID
    server_key: str
    tool_key: str
    status: MCPToolRunStatus
    caller_type: str
    caller_id: str | None
    requested_by: UUID | None
    entity_type: str | None
    entity_id: UUID | None
    workflow_stage: str | None
    input_payload: dict[str, object]
    output_payload: dict[str, object] | None
    output_metadata: dict[str, object]
    error_reason: str | None
    retry_of_run_id: UUID | None
    research_run_id: UUID | None = None
    attempt_number: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MCPToolAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    server_id: UUID
    tool_id: UUID
    action: str
    actor_id: UUID | None
    message: str
    metadata: dict[str, object] = Field(
        validation_alias=AliasChoices("metadata_payload", "metadata"),
    )
    created_at: datetime


class MCPToolRunDetailResponse(MCPToolRunResponse):
    audit_logs: list[MCPToolAuditLogResponse] = Field(default_factory=list)


class MCPServerListResponse(BaseModel):
    items: list[MCPServerResponse]


class MCPToolListResponse(BaseModel):
    items: list[MCPToolResponse]


class MCPToolRunListResponse(CursorPageResponse):
    items: list[MCPToolRunResponse]


class MCPServerTestResponse(BaseModel):
    server: MCPServerResponse
    run: MCPToolRunResponse
    success: bool
    message: str
