"""prompt version template index

Revision ID: 0017_prompt_template_idx
Revises: 0016_mcp_integration_layer
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_prompt_template_idx"
down_revision: str | None = "0016_mcp_integration_layer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_prompt_versions_prompt_template_id "
            "ON prompt_versions (prompt_template_id)",
        ),
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_prompt_versions_prompt_template_id"))
