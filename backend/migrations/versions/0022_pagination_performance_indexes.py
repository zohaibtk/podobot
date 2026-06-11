"""pagination performance indexes

Revision ID: 0022_pagination_indexes
Revises: 0021_ai_evaluation_platform
Create Date: 2026-06-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0022_pagination_indexes"
down_revision: str | None = "0021_ai_evaluation_platform"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


INDEX_STATEMENTS = [
    (
        "ix_series_updated_at_id",
        "CREATE INDEX IF NOT EXISTS ix_series_updated_at_id "
        "ON series (updated_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_series_updated_at_id",
    ),
    (
        "ix_series_created_at_id",
        "CREATE INDEX IF NOT EXISTS ix_series_created_at_id "
        "ON series (created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_series_created_at_id",
    ),
    (
        "ix_profiles_active_kind_name",
        "CREATE INDEX IF NOT EXISTS ix_profiles_active_kind_name "
        "ON profiles (is_active, kind, name)",
        "DROP INDEX IF EXISTS ix_profiles_active_kind_name",
    ),
    (
        "ix_profiles_updated_at_id",
        "CREATE INDEX IF NOT EXISTS ix_profiles_updated_at_id "
        "ON profiles (updated_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_profiles_updated_at_id",
    ),
    (
        "ix_permissions_module_action_key",
        "CREATE INDEX IF NOT EXISTS ix_permissions_module_action_key "
        "ON permissions (module, action, key)",
        "DROP INDEX IF EXISTS ix_permissions_module_action_key",
    ),
    (
        "ix_workspace_users_status_email",
        "CREATE INDEX IF NOT EXISTS ix_workspace_users_status_email "
        "ON workspace_users (status, email)",
        "DROP INDEX IF EXISTS ix_workspace_users_status_email",
    ),
    (
        "ix_agent_runs_created_at_id",
        "CREATE INDEX IF NOT EXISTS ix_agent_runs_created_at_id "
        "ON agent_runs (created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_agent_runs_created_at_id",
    ),
    (
        "ix_agent_runs_entity_created_at",
        "CREATE INDEX IF NOT EXISTS ix_agent_runs_entity_created_at "
        "ON agent_runs (entity_type, entity_id, created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_agent_runs_entity_created_at",
    ),
    (
        "ix_agent_runs_agent_created_at",
        "CREATE INDEX IF NOT EXISTS ix_agent_runs_agent_created_at "
        "ON agent_runs (agent_key, created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_agent_runs_agent_created_at",
    ),
    (
        "ix_mcp_tool_runs_created_at_id",
        "CREATE INDEX IF NOT EXISTS ix_mcp_tool_runs_created_at_id "
        "ON mcp_tool_runs (created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_mcp_tool_runs_created_at_id",
    ),
    (
        "ix_mcp_tool_runs_entity_created_at",
        "CREATE INDEX IF NOT EXISTS ix_mcp_tool_runs_entity_created_at "
        "ON mcp_tool_runs (entity_type, entity_id, created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_mcp_tool_runs_entity_created_at",
    ),
    (
        "ix_mcp_tool_runs_tool_created_at",
        "CREATE INDEX IF NOT EXISTS ix_mcp_tool_runs_tool_created_at "
        "ON mcp_tool_runs (tool_key, created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_mcp_tool_runs_tool_created_at",
    ),
    (
        "ix_media_assets_status_uploaded_id",
        "CREATE INDEX IF NOT EXISTS ix_media_assets_status_uploaded_id "
        "ON media_assets (status, uploaded_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_media_assets_status_uploaded_id",
    ),
    (
        "ix_media_assets_kind_uploaded_id",
        "CREATE INDEX IF NOT EXISTS ix_media_assets_kind_uploaded_id "
        "ON media_assets (kind, uploaded_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_media_assets_kind_uploaded_id",
    ),
    (
        "ix_media_audit_logs_asset_created_id",
        "CREATE INDEX IF NOT EXISTS ix_media_audit_logs_asset_created_id "
        "ON media_audit_logs (media_asset_id, created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_media_audit_logs_asset_created_id",
    ),
    (
        "ix_episode_video_platform_schedules_status_date_id",
        "CREATE INDEX IF NOT EXISTS ix_episode_video_platform_schedules_status_date_id "
        "ON episode_video_platform_schedules (status, scheduled_for, id)",
        "DROP INDEX IF EXISTS ix_episode_video_platform_schedules_status_date_id",
    ),
    (
        "ix_episode_video_platform_schedules_platform_date_id",
        "CREATE INDEX IF NOT EXISTS ix_episode_video_platform_schedules_platform_date_id "
        "ON episode_video_platform_schedules (platform, scheduled_for, id)",
        "DROP INDEX IF EXISTS ix_episode_video_platform_schedules_platform_date_id",
    ),
    (
        "ix_publishing_audit_logs_created_id",
        "CREATE INDEX IF NOT EXISTS ix_publishing_audit_logs_created_id "
        "ON publishing_audit_logs (created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_publishing_audit_logs_created_id",
    ),
    (
        "ix_publishing_audit_logs_schedule_created",
        "CREATE INDEX IF NOT EXISTS ix_publishing_audit_logs_schedule_created "
        "ON publishing_audit_logs (schedule_id, created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_publishing_audit_logs_schedule_created",
    ),
    (
        "ix_buffer_webhooks_received_id",
        "CREATE INDEX IF NOT EXISTS ix_buffer_webhooks_received_id "
        "ON buffer_webhooks (received_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_buffer_webhooks_received_id",
    ),
    (
        "ix_strategy_runs_created_id",
        "CREATE INDEX IF NOT EXISTS ix_strategy_runs_created_id "
        "ON strategy_runs (created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_strategy_runs_created_id",
    ),
    (
        "ix_strategy_ideas_status_created_id",
        "CREATE INDEX IF NOT EXISTS ix_strategy_ideas_status_created_id "
        "ON strategy_ideas (status, created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_strategy_ideas_status_created_id",
    ),
    (
        "ix_strategy_ideas_run_status_created_id",
        "CREATE INDEX IF NOT EXISTS ix_strategy_ideas_run_status_created_id "
        "ON strategy_ideas (run_id, status, created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_strategy_ideas_run_status_created_id",
    ),
    (
        "ix_evaluation_datasets_domain_updated_id",
        "CREATE INDEX IF NOT EXISTS ix_evaluation_datasets_domain_updated_id "
        "ON evaluation_datasets (domain, updated_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_evaluation_datasets_domain_updated_id",
    ),
    (
        "ix_prompt_benchmarks_domain_created_id",
        "CREATE INDEX IF NOT EXISTS ix_prompt_benchmarks_domain_created_id "
        "ON prompt_benchmarks (domain, created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_prompt_benchmarks_domain_created_id",
    ),
    (
        "ix_evaluation_runs_created_id",
        "CREATE INDEX IF NOT EXISTS ix_evaluation_runs_created_id "
        "ON evaluation_runs (created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_evaluation_runs_created_id",
    ),
    (
        "ix_evaluation_runs_domain_created_id",
        "CREATE INDEX IF NOT EXISTS ix_evaluation_runs_domain_created_id "
        "ON evaluation_runs (domain, created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_evaluation_runs_domain_created_id",
    ),
    (
        "ix_evaluation_results_run_created_id",
        "CREATE INDEX IF NOT EXISTS ix_evaluation_results_run_created_id "
        "ON evaluation_results (run_id, created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_evaluation_results_run_created_id",
    ),
    (
        "ix_evaluation_audit_logs_created_id",
        "CREATE INDEX IF NOT EXISTS ix_evaluation_audit_logs_created_id "
        "ON evaluation_audit_logs (created_at DESC, id DESC)",
        "DROP INDEX IF EXISTS ix_evaluation_audit_logs_created_id",
    ),
]


def upgrade() -> None:
    for _, create_statement, _ in INDEX_STATEMENTS:
        op.execute(create_statement)


def downgrade() -> None:
    for _, _, drop_statement in reversed(INDEX_STATEMENTS):
        op.execute(drop_statement)
