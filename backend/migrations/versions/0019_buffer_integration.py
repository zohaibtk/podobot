"""production buffer integration

Revision ID: 0019_buffer_integration
Revises: 0018_media_pipeline
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019_buffer_integration"
down_revision: str | None = "0018_media_pipeline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


buffer_account_status = postgresql.ENUM(
    "disconnected",
    "oauth_pending",
    "connected",
    "expired",
    "revoked",
    name="buffer_account_status",
    create_type=False,
)
buffer_webhook_status = postgresql.ENUM(
    "received",
    "processed",
    "ignored",
    "failed",
    name="buffer_webhook_status",
    create_type=False,
)
publishing_audit_status = postgresql.ENUM(
    "succeeded",
    "failed",
    "rate_limited",
    "retry_scheduled",
    name="publishing_audit_status",
    create_type=False,
)
platform = postgresql.ENUM(
    "linkedin",
    "facebook",
    "youtube",
    "instagram",
    "tiktok",
    "x",
    name="platform",
    create_type=False,
)


def upgrade() -> None:
    buffer_account_status.create(op.get_bind(), checkfirst=True)
    buffer_webhook_status.create(op.get_bind(), checkfirst=True)
    publishing_audit_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "buffer_accounts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("integration_id", sa.UUID(), nullable=True),
        sa.Column("buffer_account_id", sa.String(length=180), nullable=True),
        sa.Column("organization_id", sa.String(length=180), nullable=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column(
            "status",
            buffer_account_status,
            server_default="disconnected",
            nullable=False,
        ),
        sa.Column("access_token_secret", sa.Text(), nullable=True),
        sa.Column("refresh_token_secret", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "scopes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("oauth_state", sa.String(length=180), nullable=True),
        sa.Column("pkce_verifier", sa.Text(), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "rate_limit",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
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
        sa.ForeignKeyConstraint(["integration_id"], ["integrations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_buffer_accounts_integration_id", "buffer_accounts", ["integration_id"])
    op.create_index("ix_buffer_accounts_oauth_state", "buffer_accounts", ["oauth_state"])
    op.create_index("ix_buffer_accounts_status", "buffer_accounts", ["status"])

    op.create_table(
        "buffer_channels",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("buffer_account_id", sa.UUID(), nullable=False),
        sa.Column("buffer_channel_id", sa.String(length=180), nullable=False),
        sa.Column("service", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("display_name", sa.String(length=180), nullable=False),
        sa.Column("avatar_url", sa.String(length=640), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("is_queue_paused", sa.Boolean(), nullable=False),
        sa.Column(
            "raw_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["buffer_account_id"], ["buffer_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "buffer_account_id",
            "buffer_channel_id",
            name="uq_buffer_channel",
        ),
    )
    op.create_index(
        "ix_buffer_channels_buffer_account_id",
        "buffer_channels",
        ["buffer_account_id"],
    )
    op.create_index("ix_buffer_channels_service", "buffer_channels", ["service"])

    op.create_table(
        "buffer_channel_mappings",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("platform", platform, nullable=False),
        sa.Column("buffer_channel_id", sa.UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.ForeignKeyConstraint(["buffer_channel_id"], ["buffer_channels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform", name="uq_buffer_channel_mappings_platform"),
    )
    op.create_index(
        "ix_buffer_channel_mappings_buffer_channel_id",
        "buffer_channel_mappings",
        ["buffer_channel_id"],
    )
    op.create_index(
        "ix_buffer_channel_mappings_platform",
        "buffer_channel_mappings",
        ["platform"],
    )

    op.add_column(
        "episode_video_platform_schedules",
        sa.Column("buffer_account_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "episode_video_platform_schedules",
        sa.Column("buffer_channel_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "episode_video_platform_schedules",
        sa.Column("idempotency_key", sa.String(length=220), nullable=True),
    )
    op.add_column(
        "episode_video_platform_schedules",
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "episode_video_platform_schedules",
        sa.Column("buffer_last_event_id", sa.String(length=180), nullable=True),
    )
    op.add_column(
        "episode_video_platform_schedules",
        sa.Column("rate_limit_reset_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_schedule_buffer_account",
        "episode_video_platform_schedules",
        "buffer_accounts",
        ["buffer_account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_schedule_buffer_channel",
        "episode_video_platform_schedules",
        "buffer_channels",
        ["buffer_channel_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_episode_video_platform_schedules_buffer_account_id",
        "episode_video_platform_schedules",
        ["buffer_account_id"],
    )
    op.create_index(
        "ix_episode_video_platform_schedules_buffer_channel_id",
        "episode_video_platform_schedules",
        ["buffer_channel_id"],
    )
    op.create_index(
        "ix_episode_video_platform_schedules_idempotency_key",
        "episode_video_platform_schedules",
        ["idempotency_key"],
    )

    op.create_table(
        "buffer_webhooks",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("event_id", sa.String(length=180), nullable=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("buffer_post_id", sa.String(length=180), nullable=True),
        sa.Column("schedule_id", sa.UUID(), nullable=True),
        sa.Column("status", buffer_webhook_status, server_default="received", nullable=False),
        sa.Column("signature_valid", sa.Boolean(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["schedule_id"],
            ["episode_video_platform_schedules.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_buffer_webhooks_event_id"),
    )
    op.create_index("ix_buffer_webhooks_buffer_post_id", "buffer_webhooks", ["buffer_post_id"])
    op.create_index("ix_buffer_webhooks_event_type", "buffer_webhooks", ["event_type"])
    op.create_index("ix_buffer_webhooks_schedule_id", "buffer_webhooks", ["schedule_id"])
    op.create_index("ix_buffer_webhooks_status", "buffer_webhooks", ["status"])

    op.create_table(
        "publishing_audit_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("schedule_id", sa.UUID(), nullable=True),
        sa.Column("buffer_account_id", sa.UUID(), nullable=True),
        sa.Column("buffer_channel_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("status", publishing_audit_status, nullable=False),
        sa.Column("idempotency_key", sa.String(length=220), nullable=True),
        sa.Column(
            "request_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "response_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["buffer_account_id"],
            ["buffer_accounts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["buffer_channel_id"],
            ["buffer_channels.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["schedule_id"],
            ["episode_video_platform_schedules.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_publishing_audit_logs_action", "publishing_audit_logs", ["action"])
    op.create_index(
        "ix_publishing_audit_logs_buffer_account_id",
        "publishing_audit_logs",
        ["buffer_account_id"],
    )
    op.create_index(
        "ix_publishing_audit_logs_buffer_channel_id",
        "publishing_audit_logs",
        ["buffer_channel_id"],
    )
    op.create_index(
        "ix_publishing_audit_logs_schedule_id",
        "publishing_audit_logs",
        ["schedule_id"],
    )
    op.create_index("ix_publishing_audit_logs_status", "publishing_audit_logs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_publishing_audit_logs_status", table_name="publishing_audit_logs")
    op.drop_index("ix_publishing_audit_logs_schedule_id", table_name="publishing_audit_logs")
    op.drop_index(
        "ix_publishing_audit_logs_buffer_channel_id",
        table_name="publishing_audit_logs",
    )
    op.drop_index(
        "ix_publishing_audit_logs_buffer_account_id",
        table_name="publishing_audit_logs",
    )
    op.drop_index("ix_publishing_audit_logs_action", table_name="publishing_audit_logs")
    op.drop_table("publishing_audit_logs")

    op.drop_index("ix_buffer_webhooks_status", table_name="buffer_webhooks")
    op.drop_index("ix_buffer_webhooks_schedule_id", table_name="buffer_webhooks")
    op.drop_index("ix_buffer_webhooks_event_type", table_name="buffer_webhooks")
    op.drop_index("ix_buffer_webhooks_buffer_post_id", table_name="buffer_webhooks")
    op.drop_table("buffer_webhooks")

    op.drop_index(
        "ix_episode_video_platform_schedules_idempotency_key",
        table_name="episode_video_platform_schedules",
    )
    op.drop_index(
        "ix_episode_video_platform_schedules_buffer_channel_id",
        table_name="episode_video_platform_schedules",
    )
    op.drop_index(
        "ix_episode_video_platform_schedules_buffer_account_id",
        table_name="episode_video_platform_schedules",
    )
    op.drop_constraint(
        "fk_schedule_buffer_channel",
        "episode_video_platform_schedules",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_schedule_buffer_account",
        "episode_video_platform_schedules",
        type_="foreignkey",
    )
    op.drop_column("episode_video_platform_schedules", "rate_limit_reset_at")
    op.drop_column("episode_video_platform_schedules", "buffer_last_event_id")
    op.drop_column("episode_video_platform_schedules", "next_retry_at")
    op.drop_column("episode_video_platform_schedules", "idempotency_key")
    op.drop_column("episode_video_platform_schedules", "buffer_channel_id")
    op.drop_column("episode_video_platform_schedules", "buffer_account_id")

    op.drop_index("ix_buffer_channel_mappings_platform", table_name="buffer_channel_mappings")
    op.drop_index(
        "ix_buffer_channel_mappings_buffer_channel_id",
        table_name="buffer_channel_mappings",
    )
    op.drop_table("buffer_channel_mappings")

    op.drop_index("ix_buffer_channels_service", table_name="buffer_channels")
    op.drop_index("ix_buffer_channels_buffer_account_id", table_name="buffer_channels")
    op.drop_table("buffer_channels")

    op.drop_index("ix_buffer_accounts_status", table_name="buffer_accounts")
    op.drop_index("ix_buffer_accounts_oauth_state", table_name="buffer_accounts")
    op.drop_index("ix_buffer_accounts_integration_id", table_name="buffer_accounts")
    op.drop_table("buffer_accounts")

    publishing_audit_status.drop(op.get_bind(), checkfirst=True)
    buffer_webhook_status.drop(op.get_bind(), checkfirst=True)
    buffer_account_status.drop(op.get_bind(), checkfirst=True)
