"""foundation extensions

Revision ID: 0001_foundation_extensions
Revises:
Create Date: 2026-06-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_foundation_extensions"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector') THEN
            CREATE EXTENSION IF NOT EXISTS "vector";
          ELSE
            RAISE NOTICE 'pgvector extension is not installed on this PostgreSQL host';
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute('DROP EXTENSION IF EXISTS "vector"')
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
