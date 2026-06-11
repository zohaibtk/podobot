from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import MCPServerStatus, MCPToolRunStatus, MCPToolStatus
from app.modules.series.models import enum_values


class MCPServer(Base):
    __tablename__ = "mcp_servers"
    __table_args__ = (UniqueConstraint("key", name="uq_mcp_servers_key"),)

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    adapter_type: Mapped[str] = mapped_column(String(80), nullable=False, default="unavailable")
    is_critical: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    status: Mapped[MCPServerStatus] = mapped_column(
        Enum(MCPServerStatus, name="mcp_server_status", values_callable=enum_values),
        nullable=False,
        default=MCPServerStatus.NOT_CONFIGURED,
        server_default=MCPServerStatus.NOT_CONFIGURED.value,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    circuit_open_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    settings: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class MCPTool(Base):
    __tablename__ = "mcp_tools"
    __table_args__ = (
        UniqueConstraint("key", name="uq_mcp_tools_key"),
        UniqueConstraint("server_id", "key", name="uq_mcp_tools_server_key"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    server_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("mcp_servers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    server_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    output_schema: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    auth_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=30_000)
    retry_policy: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    circuit_breaker_policy: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    is_critical: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    allowed_callers: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[MCPToolStatus] = mapped_column(
        Enum(MCPToolStatus, name="mcp_tool_status", values_callable=enum_values),
        nullable=False,
        default=MCPToolStatus.ENABLED,
        server_default=MCPToolStatus.ENABLED.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class MCPAuthConfig(Base):
    __tablename__ = "mcp_auth_configs"
    __table_args__ = (UniqueConstraint("server_id", name="uq_mcp_auth_configs_server_id"),)

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    server_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("mcp_servers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    auth_type: Mapped[str] = mapped_column(String(80), nullable=False, default="none")
    secret_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_secret: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    masked_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    settings: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class MCPToolRun(Base):
    __tablename__ = "mcp_tool_runs"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    server_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("mcp_servers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tool_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("mcp_tools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    server_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    tool_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    status: Mapped[MCPToolRunStatus] = mapped_column(
        Enum(MCPToolRunStatus, name="mcp_tool_run_status", values_callable=enum_values),
        nullable=False,
        default=MCPToolRunStatus.QUEUED,
        server_default=MCPToolRunStatus.QUEUED.value,
    )
    caller_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    caller_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    requested_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspace_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    entity_id: Mapped[UUID | None] = mapped_column(PostgresUUID(as_uuid=True), nullable=True)
    workflow_stage: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    input_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    output_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    output_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    error_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_of_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("mcp_tool_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    research_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class MCPToolAuditLog(Base):
    __tablename__ = "mcp_tool_audit_logs"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("mcp_tool_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    server_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("mcp_servers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tool_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("mcp_tools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_id: Mapped[UUID | None] = mapped_column(PostgresUUID(as_uuid=True), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_payload: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
