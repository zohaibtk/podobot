"""settings module

Revision ID: 0013_settings_module
Revises: 0012_integrations_management
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_settings_module"
down_revision: str | None = "0012_integrations_management"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


workspace_user_status = postgresql.ENUM(
    "active",
    "invited",
    "suspended",
    name="workspace_user_status",
    create_type=False,
)
user_invitation_status = postgresql.ENUM(
    "pending",
    "accepted",
    "revoked",
    "expired",
    name="user_invitation_status",
    create_type=False,
)


def upgrade() -> None:
    workspace_user_status.create(op.get_bind(), checkfirst=True)
    user_invitation_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "workspace_settings",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_name", sa.String(length=180), nullable=False),
        sa.Column("workspace_slug", sa.String(length=120), nullable=False),
        sa.Column("contact_email", sa.String(length=240), nullable=False),
        sa.Column("default_timezone", sa.String(length=80), nullable=False),
        sa.Column("content_language", sa.String(length=40), nullable=False),
        sa.Column("brand_voice", sa.Text(), nullable=False),
        sa.Column("data_retention_days", sa.Integer(), nullable=False),
        sa.Column(
            "sensitive_settings_secret",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
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
        sa.UniqueConstraint("workspace_slug", name="uq_workspace_settings_workspace_slug"),
    )

    op.create_table(
        "roles",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_assignable", sa.Boolean(), server_default="true", nullable=False),
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
        sa.UniqueConstraint("key", name="uq_roles_key"),
    )
    op.create_index("ix_roles_key", "roles", ["key"])

    op.create_table(
        "permissions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("module", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("module", "action", name="uq_permissions_module_action"),
    )
    op.create_index("ix_permissions_module", "permissions", ["module"])

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("permission_id", sa.UUID(), nullable=False),
        sa.Column("is_allowed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permissions_role_permission",
        ),
    )
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])

    op.create_table(
        "workspace_users",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(length=240), nullable=False),
        sa.Column("full_name", sa.String(length=180), nullable=True),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("status", workspace_user_status, server_default="active", nullable=False),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_workspace_users_email"),
    )
    op.create_index("ix_workspace_users_email", "workspace_users", ["email"])
    op.create_index("ix_workspace_users_role_id", "workspace_users", ["role_id"])

    op.create_table(
        "user_invitations",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(length=240), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("status", user_invitation_status, server_default="pending", nullable=False),
        sa.Column("invited_by", sa.String(length=120), nullable=False),
        sa.Column("token_digest", sa.String(length=180), nullable=False),
        sa.Column("created_user_id", sa.UUID(), nullable=True),
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
        sa.ForeignKeyConstraint(["created_user_id"], ["workspace_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_invitations_created_user_id", "user_invitations", ["created_user_id"])
    op.create_index("ix_user_invitations_email", "user_invitations", ["email"])
    op.create_index("ix_user_invitations_role_id", "user_invitations", ["role_id"])

    op.create_table(
        "settings_audit_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("redacted_changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_settings_audit_logs_action", "settings_audit_logs", ["action"])


def downgrade() -> None:
    op.drop_index("ix_settings_audit_logs_action", table_name="settings_audit_logs")
    op.drop_table("settings_audit_logs")

    op.drop_index("ix_user_invitations_role_id", table_name="user_invitations")
    op.drop_index("ix_user_invitations_email", table_name="user_invitations")
    op.drop_index("ix_user_invitations_created_user_id", table_name="user_invitations")
    op.drop_table("user_invitations")

    op.drop_index("ix_workspace_users_role_id", table_name="workspace_users")
    op.drop_index("ix_workspace_users_email", table_name="workspace_users")
    op.drop_table("workspace_users")

    op.drop_index("ix_role_permissions_role_id", table_name="role_permissions")
    op.drop_index("ix_role_permissions_permission_id", table_name="role_permissions")
    op.drop_table("role_permissions")

    op.drop_index("ix_permissions_module", table_name="permissions")
    op.drop_table("permissions")

    op.drop_index("ix_roles_key", table_name="roles")
    op.drop_table("roles")

    op.drop_table("workspace_settings")

    user_invitation_status.drop(op.get_bind(), checkfirst=True)
    workspace_user_status.drop(op.get_bind(), checkfirst=True)
