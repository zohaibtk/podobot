"""integrations management

Revision ID: 0012_integrations_management
Revises: 0011_strategy_module
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_integrations_management"
down_revision: str | None = "0011_strategy_module"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


integration_type = postgresql.ENUM(
    "buffer",
    "openai",
    "research_api",
    "transcription",
    name="integration_type",
    create_type=False,
)
integration_status = postgresql.ENUM(
    "healthy",
    "degraded",
    "broken",
    "not_configured",
    "disabled",
    name="integration_status",
    create_type=False,
)


def upgrade() -> None:
    integration_type.create(op.get_bind(), checkfirst=True)
    integration_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "integrations",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("type", integration_type, nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_critical", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("status", integration_status, server_default="not_configured", nullable=False),
        sa.Column("api_key_secret", sa.Text(), nullable=True),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quota", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("type", name="uq_integrations_type"),
    )
    op.create_index("ix_integrations_type", "integrations", ["type"])

    op.create_table(
        "integration_audit_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("integration_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("actor", sa.String(length=120), server_default="system", nullable=False),
        sa.Column("previous_status", integration_status, nullable=True),
        sa.Column("new_status", integration_status, nullable=True),
        sa.Column("redacted_changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["integration_id"], ["integrations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_integration_audit_logs_integration_id",
        "integration_audit_logs",
        ["integration_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_integration_audit_logs_integration_id",
        table_name="integration_audit_logs",
    )
    op.drop_table("integration_audit_logs")
    op.drop_index("ix_integrations_type", table_name="integrations")
    op.drop_table("integrations")

    integration_status.drop(op.get_bind(), checkfirst=True)
    integration_type.drop(op.get_bind(), checkfirst=True)
