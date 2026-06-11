"""auth rbac foundation

Revision ID: 0014_auth_rbac_foundation
Revises: 0013_settings_module
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_auth_rbac_foundation"
down_revision: str | None = "0013_settings_module"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("permissions", sa.Column("key", sa.String(length=160), nullable=True))
    op.execute("UPDATE permissions SET key = module || '.' || action WHERE key IS NULL")
    op.alter_column("permissions", "key", nullable=False)
    op.add_column(
        "permissions",
        sa.Column("is_system", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "permissions",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_permissions_key", "permissions", ["key"])
    op.create_unique_constraint("uq_permissions_key", "permissions", ["key"])

    op.add_column(
        "workspace_users",
        sa.Column("password_hash", sa.String(length=240), nullable=True),
    )
    op.add_column(
        "workspace_users",
        sa.Column("auth_token_version", sa.Integer(), server_default="0", nullable=False),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["workspace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.execute(
        """
        INSERT INTO user_roles (user_id, role_id, is_primary)
        SELECT id, role_id, true
        FROM workspace_users
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_user_roles_user_id", table_name="user_roles")
    op.drop_index("ix_user_roles_role_id", table_name="user_roles")
    op.drop_table("user_roles")

    op.drop_column("workspace_users", "auth_token_version")
    op.drop_column("workspace_users", "password_hash")

    op.drop_constraint("uq_permissions_key", "permissions", type_="unique")
    op.drop_index("ix_permissions_key", table_name="permissions")
    op.drop_column("permissions", "updated_at")
    op.drop_column("permissions", "is_system")
    op.drop_column("permissions", "key")
