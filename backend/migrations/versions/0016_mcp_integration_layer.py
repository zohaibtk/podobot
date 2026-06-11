"""mcp integration layer

Revision ID: 0016_mcp_integration_layer
Revises: 0015_ai_orchestration_layer
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_mcp_integration_layer"
down_revision: str | None = "0015_ai_orchestration_layer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


mcp_server_status = postgresql.ENUM(
    "healthy",
    "degraded",
    "broken",
    "not_configured",
    "disabled",
    name="mcp_server_status",
    create_type=False,
)
mcp_tool_status = postgresql.ENUM(
    "enabled",
    "disabled",
    "deprecated",
    name="mcp_tool_status",
    create_type=False,
)
mcp_tool_run_status = postgresql.ENUM(
    "queued",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    name="mcp_tool_run_status",
    create_type=False,
)


def upgrade() -> None:
    mcp_server_status.create(op.get_bind(), checkfirst=True)
    mcp_tool_status.create(op.get_bind(), checkfirst=True)
    mcp_tool_run_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "mcp_servers",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("adapter_type", sa.String(length=80), nullable=False),
        sa.Column("is_critical", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("status", mcp_server_status, server_default="not_configured", nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("circuit_open_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index("ix_mcp_servers_key", "mcp_servers", ["key"])

    op.create_table(
        "mcp_tools",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("server_id", sa.UUID(), nullable=False),
        sa.Column("server_key", sa.String(length=80), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("display_name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("input_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("auth_required", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("timeout_ms", sa.Integer(), nullable=False),
        sa.Column("retry_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "circuit_breaker_policy",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("is_critical", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("allowed_callers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", mcp_tool_status, server_default="enabled", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["server_id"], ["mcp_servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
        sa.UniqueConstraint("server_id", "key", name="uq_mcp_tools_server_key"),
    )
    op.create_index("ix_mcp_tools_key", "mcp_tools", ["key"])
    op.create_index("ix_mcp_tools_server_id", "mcp_tools", ["server_id"])
    op.create_index("ix_mcp_tools_server_key", "mcp_tools", ["server_key"])

    op.create_table(
        "mcp_auth_configs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("server_id", sa.UUID(), nullable=False),
        sa.Column("auth_type", sa.String(length=80), nullable=False),
        sa.Column("secret_ref", sa.Text(), nullable=True),
        sa.Column("has_secret", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("masked_label", sa.String(length=120), nullable=True),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["server_id"], ["mcp_servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("server_id"),
    )
    op.create_index("ix_mcp_auth_configs_server_id", "mcp_auth_configs", ["server_id"])

    op.create_table(
        "mcp_tool_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("server_id", sa.UUID(), nullable=False),
        sa.Column("tool_id", sa.UUID(), nullable=False),
        sa.Column("server_key", sa.String(length=80), nullable=False),
        sa.Column("tool_key", sa.String(length=160), nullable=False),
        sa.Column("status", mcp_tool_run_status, server_default="queued", nullable=False),
        sa.Column("caller_type", sa.String(length=40), nullable=False),
        sa.Column("caller_id", sa.String(length=160), nullable=True),
        sa.Column("requested_by", sa.UUID(), nullable=True),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("workflow_stage", sa.String(length=80), nullable=True),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_reason", sa.Text(), nullable=True),
        sa.Column("retry_of_run_id", sa.UUID(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["requested_by"], ["workspace_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["retry_of_run_id"], ["mcp_tool_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["server_id"], ["mcp_servers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tool_id"], ["mcp_tools.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "server_id",
        "tool_id",
        "server_key",
        "tool_key",
        "caller_type",
        "requested_by",
        "entity_type",
        "workflow_stage",
        "retry_of_run_id",
    ):
        op.create_index(f"ix_mcp_tool_runs_{column}", "mcp_tool_runs", [column])

    op.create_table(
        "mcp_tool_audit_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("server_id", sa.UUID(), nullable=False),
        sa.Column("tool_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["mcp_tool_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["server_id"], ["mcp_servers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tool_id"], ["mcp_tools.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("run_id", "server_id", "tool_id", "action"):
        op.create_index(f"ix_mcp_tool_audit_logs_{column}", "mcp_tool_audit_logs", [column])


def downgrade() -> None:
    for column in ("run_id", "server_id", "tool_id", "action"):
        op.drop_index(f"ix_mcp_tool_audit_logs_{column}", table_name="mcp_tool_audit_logs")
    op.drop_table("mcp_tool_audit_logs")

    for column in (
        "server_id",
        "tool_id",
        "server_key",
        "tool_key",
        "caller_type",
        "requested_by",
        "entity_type",
        "workflow_stage",
        "retry_of_run_id",
    ):
        op.drop_index(f"ix_mcp_tool_runs_{column}", table_name="mcp_tool_runs")
    op.drop_table("mcp_tool_runs")

    op.drop_index("ix_mcp_auth_configs_server_id", table_name="mcp_auth_configs")
    op.drop_table("mcp_auth_configs")

    op.drop_index("ix_mcp_tools_server_key", table_name="mcp_tools")
    op.drop_index("ix_mcp_tools_server_id", table_name="mcp_tools")
    op.drop_index("ix_mcp_tools_key", table_name="mcp_tools")
    op.drop_table("mcp_tools")

    op.drop_index("ix_mcp_servers_key", table_name="mcp_servers")
    op.drop_table("mcp_servers")

    mcp_tool_run_status.drop(op.get_bind(), checkfirst=True)
    mcp_tool_status.drop(op.get_bind(), checkfirst=True)
    mcp_server_status.drop(op.get_bind(), checkfirst=True)
