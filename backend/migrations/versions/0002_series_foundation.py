"""series foundation

Revision ID: 0002_series_foundation
Revises: 0001_foundation_extensions
Create Date: 2026-06-06
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_series_foundation"
down_revision: str | None = "0001_foundation_extensions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


series_status = postgresql.ENUM(
    "researching",
    "planning",
    "in_production",
    "partially_published",
    "complete",
    "archived",
    name="series_status",
    create_type=False,
)
discovery_status = postgresql.ENUM(
    "pending",
    "running",
    "complete",
    "failed",
    name="discovery_status",
    create_type=False,
)
series_stage = postgresql.ENUM(
    "discovery",
    "narrative",
    "plan",
    "outlines",
    "briefs",
    "recordings",
    "captions",
    "schedule",
    name="series_stage",
    create_type=False,
)


def upgrade() -> None:
    series_status.create(op.get_bind(), checkfirst=True)
    discovery_status.create(op.get_bind(), checkfirst=True)
    series_stage.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "series",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("audience", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("guest_name", sa.String(length=180), nullable=True),
        sa.Column("status", series_status, server_default="researching", nullable=False),
        sa.Column("discovery_status", discovery_status, server_default="running", nullable=False),
        sa.Column("current_stage", series_stage, server_default="discovery", nullable=False),
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
    )
    op.create_index("ix_series_status_updated_at", "series", ["status", "updated_at"])
    op.create_index(
        "ix_series_discovery_status_updated_at",
        "series",
        ["discovery_status", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_series_discovery_status_updated_at", table_name="series")
    op.drop_index("ix_series_status_updated_at", table_name="series")
    op.drop_table("series")
    series_stage.drop(op.get_bind(), checkfirst=True)
    discovery_status.drop(op.get_bind(), checkfirst=True)
    series_status.drop(op.get_bind(), checkfirst=True)
