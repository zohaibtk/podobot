"""ai orchestration layer

Revision ID: 0015_ai_orchestration_layer
Revises: 0014_auth_rbac_foundation
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_ai_orchestration_layer"
down_revision: str | None = "0014_auth_rbac_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    prompt_version_status = postgresql.ENUM(
        "draft",
        "active",
        "archived",
        name="prompt_version_status",
    )
    validation_status = postgresql.ENUM(
        "passed",
        "warning",
        "failed",
        name="agent_output_validation_status",
    )
    prompt_version_status.create(op.get_bind(), checkfirst=True)
    validation_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "agents",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("responsibility", sa.Text(), nullable=False),
        sa.Column("tools", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("required_permission", sa.String(length=160), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default="true", nullable=False),
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
    op.create_index("ix_agents_key", "agents", ["key"])

    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
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
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index("ix_prompt_templates_agent_id", "prompt_templates", ["agent_id"])
    op.create_index("ix_prompt_templates_key", "prompt_templates", ["key"])

    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("prompt_template_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("prompt_key", sa.String(length=120), nullable=False),
        sa.Column("agent_key", sa.String(length=80), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("template_body", sa.Text(), nullable=False),
        sa.Column("input_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "active",
                "archived",
                name="prompt_version_status",
                create_type=False,
            ),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["prompt_template_id"],
            ["prompt_templates.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "prompt_template_id",
            "version_number",
            name="uq_prompt_versions_number",
        ),
    )
    op.create_index("ix_prompt_versions_agent_id", "prompt_versions", ["agent_id"])
    op.create_index("ix_prompt_versions_agent_key", "prompt_versions", ["agent_key"])
    op.create_index("ix_prompt_versions_prompt_key", "prompt_versions", ["prompt_key"])
    op.create_index(
        "uq_prompt_versions_active_key",
        "prompt_versions",
        ["prompt_key"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("agent_key", sa.String(length=80), nullable=False),
        sa.Column("prompt_version_id", sa.UUID(), nullable=True),
        sa.Column("prompt_key", sa.String(length=120), nullable=True),
        sa.Column("prompt_version_number", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "queued",
                "running",
                "succeeded",
                "failed",
                "cancelled",
                "requires_human",
                name="agent_run_status",
                create_type=False,
            ),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("workflow_stage", sa.String(length=80), nullable=True),
        sa.Column("trigger", sa.String(length=80), nullable=False),
        sa.Column("requested_by", sa.UUID(), nullable=True),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("validation_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_reason", sa.Text(), nullable=True),
        sa.Column("regeneration_reason", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["prompt_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by"], ["workspace_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["retry_of_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "agent_id",
        "agent_key",
        "prompt_version_id",
        "prompt_key",
        "entity_type",
        "workflow_stage",
        "requested_by",
        "retry_of_run_id",
    ):
        op.create_index(f"ix_agent_runs_{column}", "agent_runs", [column])

    op.create_table(
        "agent_audit_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
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
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_audit_logs_action", "agent_audit_logs", ["action"])
    op.create_index("ix_agent_audit_logs_agent_id", "agent_audit_logs", ["agent_id"])
    op.create_index("ix_agent_audit_logs_run_id", "agent_audit_logs", ["run_id"])

    op.create_table(
        "agent_output_validation_results",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "passed",
                "warning",
                "failed",
                name="agent_output_validation_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("errors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_output_validation_results_run_id",
        "agent_output_validation_results",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_output_validation_results_run_id",
        table_name="agent_output_validation_results",
    )
    op.drop_table("agent_output_validation_results")
    op.drop_index("ix_agent_audit_logs_run_id", table_name="agent_audit_logs")
    op.drop_index("ix_agent_audit_logs_agent_id", table_name="agent_audit_logs")
    op.drop_index("ix_agent_audit_logs_action", table_name="agent_audit_logs")
    op.drop_table("agent_audit_logs")
    for column in (
        "retry_of_run_id",
        "requested_by",
        "workflow_stage",
        "entity_type",
        "prompt_key",
        "prompt_version_id",
        "agent_key",
        "agent_id",
    ):
        op.drop_index(f"ix_agent_runs_{column}", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index("uq_prompt_versions_active_key", table_name="prompt_versions")
    op.drop_index("ix_prompt_versions_prompt_key", table_name="prompt_versions")
    op.drop_index("ix_prompt_versions_agent_key", table_name="prompt_versions")
    op.drop_index("ix_prompt_versions_agent_id", table_name="prompt_versions")
    op.drop_table("prompt_versions")
    op.drop_index("ix_prompt_templates_key", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_agent_id", table_name="prompt_templates")
    op.drop_table("prompt_templates")
    op.drop_index("ix_agents_key", table_name="agents")
    op.drop_table("agents")
    postgresql.ENUM(name="agent_output_validation_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="prompt_version_status").drop(op.get_bind(), checkfirst=True)
