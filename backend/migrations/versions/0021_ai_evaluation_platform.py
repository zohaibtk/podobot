"""ai evaluation platform

Revision ID: 0021_ai_evaluation_platform
Revises: 0020_media_asset_library
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021_ai_evaluation_platform"
down_revision: str | None = "0020_media_asset_library"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    evaluation_domain = postgresql.ENUM(
        "narrative_quality",
        "episode_planning_quality",
        "outline_quality",
        "brief_quality",
        "caption_quality",
        "research_quality",
        name="evaluation_domain",
    )
    evaluation_run_status = postgresql.ENUM(
        "queued",
        "running",
        "completed",
        "failed",
        "needs_review",
        name="evaluation_run_status",
    )
    evaluation_result_status = postgresql.ENUM(
        "passed",
        "warning",
        "failed",
        "regression",
        "needs_review",
        name="evaluation_result_status",
    )
    evaluation_review_status = postgresql.ENUM(
        "not_required",
        "pending",
        "reviewed",
        name="evaluation_review_status",
    )
    evaluation_domain.create(op.get_bind(), checkfirst=True)
    evaluation_run_status.create(op.get_bind(), checkfirst=True)
    evaluation_result_status.create(op.get_bind(), checkfirst=True)
    evaluation_review_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "evaluation_datasets",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column(
            "domain",
            postgresql.ENUM(
                "narrative_quality",
                "episode_planning_quality",
                "outline_quality",
                "brief_quality",
                "caption_quality",
                "research_quality",
                name="evaluation_domain",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "cases",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "expected_outputs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_golden", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by", sa.String(length=160), nullable=False),
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
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain", "name", name="uq_evaluation_datasets_domain_name"),
    )
    op.create_index("ix_evaluation_datasets_domain", "evaluation_datasets", ["domain"])

    op.create_table(
        "prompt_benchmarks",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "domain",
            postgresql.ENUM(
                "narrative_quality",
                "episode_planning_quality",
                "outline_quality",
                "brief_quality",
                "caption_quality",
                "research_quality",
                name="evaluation_domain",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("dataset_id", sa.UUID(), nullable=True),
        sa.Column("agent_key", sa.String(length=80), nullable=False),
        sa.Column("prompt_key", sa.String(length=120), nullable=False),
        sa.Column("baseline_prompt_version_id", sa.UUID(), nullable=True),
        sa.Column("threshold_score", sa.Float(), nullable=False),
        sa.Column("regression_tolerance", sa.Float(), nullable=False),
        sa.Column("baseline_score", sa.Float(), nullable=True),
        sa.Column(
            "quality_bands",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by", sa.String(length=160), nullable=False),
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
            ["baseline_prompt_version_id"], ["prompt_versions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["evaluation_datasets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("agent_key", "baseline_prompt_version_id", "dataset_id", "domain", "prompt_key"):
        op.create_index(f"ix_prompt_benchmarks_{column}", "prompt_benchmarks", [column])
    op.create_index(
        "ix_prompt_benchmarks_domain_prompt",
        "prompt_benchmarks",
        ["domain", "prompt_key"],
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_type", sa.String(length=80), nullable=False),
        sa.Column(
            "domain",
            postgresql.ENUM(
                "narrative_quality",
                "episode_planning_quality",
                "outline_quality",
                "brief_quality",
                "caption_quality",
                "research_quality",
                name="evaluation_domain",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column("benchmark_id", sa.UUID(), nullable=True),
        sa.Column("agent_key", sa.String(length=80), nullable=False),
        sa.Column("prompt_key", sa.String(length=120), nullable=False),
        sa.Column("baseline_prompt_version_id", sa.UUID(), nullable=True),
        sa.Column("candidate_prompt_version_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "queued",
                "running",
                "completed",
                "failed",
                "needs_review",
                name="evaluation_run_status",
                create_type=False,
            ),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("requested_by", sa.UUID(), nullable=True),
        sa.Column("requested_by_email", sa.String(length=160), nullable=True),
        sa.Column("aggregate_score", sa.Float(), nullable=True),
        sa.Column("baseline_score", sa.Float(), nullable=True),
        sa.Column("candidate_score", sa.Float(), nullable=True),
        sa.Column("regression_delta", sa.Float(), nullable=True),
        sa.Column("threshold_score", sa.Float(), nullable=False),
        sa.Column("regression_tolerance", sa.Float(), nullable=False),
        sa.Column("regression_detected", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("human_review_required", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            ["baseline_prompt_version_id"], ["prompt_versions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["benchmark_id"], ["prompt_benchmarks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["candidate_prompt_version_id"], ["prompt_versions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["evaluation_datasets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "agent_key",
        "baseline_prompt_version_id",
        "benchmark_id",
        "candidate_prompt_version_id",
        "dataset_id",
        "domain",
        "human_review_required",
        "prompt_key",
        "regression_detected",
        "status",
    ):
        op.create_index(f"ix_evaluation_runs_{column}", "evaluation_runs", [column])

    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.String(length=120), nullable=False),
        sa.Column("case_name", sa.String(length=220), nullable=False),
        sa.Column(
            "domain",
            postgresql.ENUM(
                "narrative_quality",
                "episode_planning_quality",
                "outline_quality",
                "brief_quality",
                "caption_quality",
                "research_quality",
                name="evaluation_domain",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("agent_key", sa.String(length=80), nullable=False),
        sa.Column("prompt_key", sa.String(length=120), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("baseline_score", sa.Float(), nullable=True),
        sa.Column("candidate_score", sa.Float(), nullable=True),
        sa.Column("threshold_score", sa.Float(), nullable=False),
        sa.Column("regression_delta", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("regression_detected", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "passed",
                "warning",
                "failed",
                "regression",
                "needs_review",
                name="evaluation_result_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "review_status",
            postgresql.ENUM(
                "not_required",
                "pending",
                "reviewed",
                name="evaluation_review_status",
                create_type=False,
            ),
            server_default="not_required",
            nullable=False,
        ),
        sa.Column(
            "input_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "expected_output",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "actual_output",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("reviewer_score", sa.Float(), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("reviewed_by_email", sa.String(length=160), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["evaluation_datasets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "agent_key",
        "case_id",
        "dataset_id",
        "domain",
        "prompt_key",
        "regression_detected",
        "review_status",
        "run_id",
        "status",
    ):
        op.create_index(f"ix_evaluation_results_{column}", "evaluation_results", [column])

    op.create_table(
        "agent_scorecards",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("agent_key", sa.String(length=80), nullable=False),
        sa.Column(
            "domain",
            postgresql.ENUM(
                "narrative_quality",
                "episode_planning_quality",
                "outline_quality",
                "brief_quality",
                "caption_quality",
                "research_quality",
                name="evaluation_domain",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("evaluation_run_id", sa.UUID(), nullable=True),
        sa.Column("latest_score", sa.Float(), nullable=False),
        sa.Column("threshold_score", sa.Float(), nullable=False),
        sa.Column("pass_rate", sa.Float(), nullable=False),
        sa.Column("regression_count", sa.Integer(), nullable=False),
        sa.Column("review_queue_count", sa.Integer(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("trend", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["evaluation_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_scorecards_agent_key", "agent_scorecards", ["agent_key"])
    op.create_index("ix_agent_scorecards_domain", "agent_scorecards", ["domain"])
    op.create_index(
        "ix_agent_scorecards_agent_domain",
        "agent_scorecards",
        ["agent_key", "domain"],
    )
    op.create_index(
        "ix_agent_scorecards_evaluation_run_id",
        "agent_scorecards",
        ["evaluation_run_id"],
    )

    op.create_table(
        "evaluation_audit_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=True),
        sa.Column("result_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("actor_email", sa.String(length=160), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
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
        sa.ForeignKeyConstraint(["result_id"], ["evaluation_results.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evaluation_audit_logs_action", "evaluation_audit_logs", ["action"])
    op.create_index("ix_evaluation_audit_logs_result_id", "evaluation_audit_logs", ["result_id"])
    op.create_index("ix_evaluation_audit_logs_run_id", "evaluation_audit_logs", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_evaluation_audit_logs_run_id", table_name="evaluation_audit_logs")
    op.drop_index("ix_evaluation_audit_logs_result_id", table_name="evaluation_audit_logs")
    op.drop_index("ix_evaluation_audit_logs_action", table_name="evaluation_audit_logs")
    op.drop_table("evaluation_audit_logs")

    op.drop_index("ix_agent_scorecards_evaluation_run_id", table_name="agent_scorecards")
    op.drop_index("ix_agent_scorecards_agent_domain", table_name="agent_scorecards")
    op.drop_index("ix_agent_scorecards_domain", table_name="agent_scorecards")
    op.drop_index("ix_agent_scorecards_agent_key", table_name="agent_scorecards")
    op.drop_table("agent_scorecards")

    for column in (
        "agent_key",
        "case_id",
        "dataset_id",
        "domain",
        "prompt_key",
        "regression_detected",
        "review_status",
        "run_id",
        "status",
    ):
        op.drop_index(f"ix_evaluation_results_{column}", table_name="evaluation_results")
    op.drop_table("evaluation_results")

    for column in (
        "agent_key",
        "baseline_prompt_version_id",
        "benchmark_id",
        "candidate_prompt_version_id",
        "dataset_id",
        "domain",
        "human_review_required",
        "prompt_key",
        "regression_detected",
        "status",
    ):
        op.drop_index(f"ix_evaluation_runs_{column}", table_name="evaluation_runs")
    op.drop_table("evaluation_runs")

    op.drop_index("ix_prompt_benchmarks_domain_prompt", table_name="prompt_benchmarks")
    for column in ("agent_key", "baseline_prompt_version_id", "dataset_id", "domain", "prompt_key"):
        op.drop_index(f"ix_prompt_benchmarks_{column}", table_name="prompt_benchmarks")
    op.drop_table("prompt_benchmarks")

    op.drop_index("ix_evaluation_datasets_domain", table_name="evaluation_datasets")
    op.drop_table("evaluation_datasets")

    postgresql.ENUM(name="evaluation_review_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="evaluation_result_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="evaluation_run_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="evaluation_domain").drop(op.get_bind(), checkfirst=True)
