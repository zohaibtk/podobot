"""add openai llm provider

Revision ID: 0029_openai_llm_provider
Revises: 0028_groq_llm_provider
Create Date: 2026-06-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0029_openai_llm_provider"
down_revision: str | None = "0028_groq_llm_provider"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE research_source_provider_type ADD VALUE IF NOT EXISTS 'openai'")


def downgrade() -> None:
    op.execute("DELETE FROM research_sources WHERE key = 'openai'")
