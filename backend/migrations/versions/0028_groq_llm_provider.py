"""add groq llm provider

Revision ID: 0028_groq_llm_provider
Revises: 0027_strategy_opportunity
Create Date: 2026-06-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0028_groq_llm_provider"
down_revision: str | None = "0027_strategy_opportunity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE research_source_provider_type ADD VALUE IF NOT EXISTS 'groq'")


def downgrade() -> None:
    op.execute("DELETE FROM research_sources WHERE key = 'groq'")
