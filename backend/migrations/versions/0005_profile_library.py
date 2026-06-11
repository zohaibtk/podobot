"""profile library

Revision ID: 0005_profile_library
Revises: 0004_episode_plan
Create Date: 2026-06-06
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0005_profile_library"
down_revision: str | None = "0004_episode_plan"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("bio", sa.Text(), nullable=True))
    op.create_index("ix_profiles_kind_archetype", "profiles", ["kind", "archetype"])
    op.create_index("ix_profiles_name", "profiles", ["name"])


def downgrade() -> None:
    op.drop_index("ix_profiles_name", table_name="profiles")
    op.drop_index("ix_profiles_kind_archetype", table_name="profiles")
    op.drop_column("profiles", "bio")
