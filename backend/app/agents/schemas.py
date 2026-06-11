from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from app.db.types import AgentOutputValidationStatus, AgentRunStatus, PromptVersionStatus
from app.schemas.pagination import CursorPageResponse


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    name: str
    responsibility: str
    tools: list[str]
    required_permission: str | None
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class PromptVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    prompt_template_id: UUID
    agent_id: UUID
    prompt_key: str
    agent_key: str
    version_number: int
    template_body: str
    input_schema: dict[str, object]
    output_schema: dict[str, object]
    status: PromptVersionStatus
    created_by: str
    created_at: datetime


class PromptTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    agent_id: UUID
    agent_key: str
    name: str
    description: str
    created_by: str
    active_version: PromptVersionResponse | None
    versions: list[PromptVersionResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PromptVersionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    template_body: str = Field(min_length=1, max_length=20000)
    input_schema: dict[str, object] = Field(default_factory=dict)
    output_schema: dict[str, object] = Field(default_factory=dict)
    status: PromptVersionStatus = PromptVersionStatus.DRAFT
    created_by: str = Field(default="system", min_length=1, max_length=120)


class AgentRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_payload: dict[str, object] = Field(default_factory=dict)
    entity_type: str | None = Field(default=None, min_length=1, max_length=80)
    entity_id: UUID | None = None
    workflow_stage: str | None = Field(default=None, min_length=1, max_length=80)
    trigger: str = Field(default="manual", min_length=1, max_length=80)
    regeneration_reason: str | None = Field(default=None, min_length=3, max_length=2000)

    @model_validator(mode="after")
    def require_regeneration_reason(self) -> "AgentRunRequest":
        if self.trigger == "regeneration" and not self.regeneration_reason:
            raise ValueError("Regeneration requires a reason")
        return self


class AgentRunRetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regeneration_reason: str | None = Field(default=None, min_length=3, max_length=2000)
    input_payload: dict[str, object] | None = None


class AgentAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    agent_id: UUID
    action: str
    actor_id: UUID | None
    message: str
    metadata: dict[str, object] = Field(
        validation_alias=AliasChoices("metadata_payload", "metadata"),
    )
    created_at: datetime


class AgentOutputValidationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    status: AgentOutputValidationStatus
    checks: list[dict[str, object]]
    errors: list[str]
    created_at: datetime


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    agent_key: str
    prompt_version_id: UUID | None
    prompt_key: str | None
    prompt_version_number: int | None
    status: AgentRunStatus
    entity_type: str | None
    entity_id: UUID | None
    workflow_stage: str | None
    trigger: str
    input_payload: dict[str, object]
    output_payload: dict[str, object] | None
    output_metadata: dict[str, object]
    validation_summary: dict[str, object]
    error_reason: str | None
    regeneration_reason: str | None
    retry_of_run_id: UUID | None
    attempt_number: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgentRunDetailResponse(AgentRunResponse):
    audit_logs: list[AgentAuditLogResponse] = Field(default_factory=list)
    validation_results: list[AgentOutputValidationResultResponse] = Field(default_factory=list)


class AgentListResponse(BaseModel):
    items: list[AgentResponse]


class PromptListResponse(BaseModel):
    items: list[PromptTemplateResponse]


class AgentRunListResponse(CursorPageResponse):
    items: list[AgentRunResponse]


AgentTokenStatsPeriod = Literal["day", "week", "month"]


class AgentTokenTotalsResponse(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    run_count: int = 0
    tokenized_run_count: int = 0
    average_tokens_per_run: int = 0


class AgentTokenUsageResponse(AgentTokenTotalsResponse):
    agent_id: UUID
    agent_key: str
    agent_name: str
    provider: str | None = None
    share_percentage: float = 0
    last_run_at: datetime | None = None


class AgentTokenTimelinePointResponse(BaseModel):
    label: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    run_count: int = 0


class AgentTokenRequestResponse(BaseModel):
    id: UUID
    agent_id: UUID
    agent_key: str
    agent_name: str
    provider: str | None = None
    status: AgentRunStatus
    trigger: str
    entity_type: str | None = None
    entity_id: UUID | None = None
    series_id: UUID | None = None
    series_name: str | None = None
    workflow_stage: str | None = None
    sequence_number: int
    label: str
    created_at: datetime
    completed_at: datetime | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    estimated_prompt_tokens: int = 0
    estimated_completion_tokens: int = 0
    estimated_total_tokens: int = 0
    display_prompt_tokens: int = 0
    display_completion_tokens: int = 0
    display_total_tokens: int = 0
    is_estimated: bool = False


class AgentTokenStatsResponse(BaseModel):
    period: AgentTokenStatsPeriod
    generated_at: datetime
    window_start: datetime
    window_end: datetime
    totals: AgentTokenTotalsResponse
    agents: list[AgentTokenUsageResponse]
    timeline: list[AgentTokenTimelinePointResponse]
    requests: list[AgentTokenRequestResponse] = Field(default_factory=list)
