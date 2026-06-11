from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.types import (
    ResearchSourceCategory,
    ResearchSourceProviderType,
    ResearchSourceStatus,
)
from app.schemas.pagination import OffsetPageResponse


class ResearchSourceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    critical: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=1000)
    quota_status: str | None = Field(default=None, min_length=1, max_length=120)
    config_json: dict[str, object] | None = None
    api_key: str | None = Field(default=None, min_length=1, max_length=4000)
    clear_api_key: bool = False

    @model_validator(mode="after")
    def require_change(self) -> "ResearchSourceUpdateRequest":
        if (
            self.critical is None
            and self.priority is None
            and self.quota_status is None
            and self.config_json is None
            and self.api_key is None
            and self.clear_api_key is False
        ):
            raise ValueError("At least one source setting is required")
        return self


class ResearchSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    name: str
    provider_type: ResearchSourceProviderType
    category: ResearchSourceCategory
    enabled: bool
    critical: bool
    priority: int
    status: ResearchSourceStatus
    quota_status: str
    last_checked_at: datetime | None = None
    last_failure_reason: str | None = None
    documents_fetched_today: int
    success_rate: float
    average_latency_ms: int
    recent_failure_count: int
    config_json: dict[str, object]
    provider_mode: str
    missing_configuration: bool
    configuration_status: str
    connection_status: str
    last_test_result: str | None = None
    trend_provider_status: str | None = None
    total_runs: int = 0
    last_run_at: datetime | None = None
    documents_collected: int = 0
    average_composite_score: int = 0
    average_trend_score: int = 0
    confidence_distribution: dict[str, int] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ResearchSourceListResponse(OffsetPageResponse):
    items: list[ResearchSourceResponse]


class ResearchSourceTestResponse(BaseModel):
    source: ResearchSourceResponse
    success: bool
    message: str


class ResearchSourceFilters(BaseModel):
    category: ResearchSourceCategory | None = None
    status: ResearchSourceStatus | None = None
    enabled: bool | None = None
    search: Annotated[str | None, Field(max_length=240)] = None
    sort: Annotated[str, Field(max_length=40)] = "priority"
