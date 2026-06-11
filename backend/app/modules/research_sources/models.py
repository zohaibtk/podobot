from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import (
    ResearchSourceCategory,
    ResearchSourceProviderType,
    ResearchSourceStatus,
)
from app.modules.series.models import enum_values


class ResearchSource(Base):
    __tablename__ = "research_sources"
    __table_args__ = (
        UniqueConstraint("key", name="uq_research_sources_key"),
        CheckConstraint("priority >= 0", name="priority_non_negative"),
        CheckConstraint(
            "documents_fetched_today >= 0",
            name="documents_non_negative",
        ),
        CheckConstraint(
            "success_rate >= 0 AND success_rate <= 1",
            name="success_rate_range",
        ),
        CheckConstraint(
            "average_latency_ms >= 0",
            name="latency_non_negative",
        ),
        CheckConstraint(
            "recent_failure_count >= 0",
            name="failures_non_negative",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    provider_type: Mapped[ResearchSourceProviderType] = mapped_column(
        Enum(
            ResearchSourceProviderType,
            name="research_source_provider_type",
            values_callable=enum_values,
        ),
        nullable=False,
        index=True,
    )
    category: Mapped[ResearchSourceCategory] = mapped_column(
        Enum(
            ResearchSourceCategory,
            name="research_source_category",
            values_callable=enum_values,
        ),
        nullable=False,
        index=True,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    critical: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        server_default="100",
    )
    status: Mapped[ResearchSourceStatus] = mapped_column(
        Enum(
            ResearchSourceStatus,
            name="research_source_registry_status",
            values_callable=enum_values,
        ),
        nullable=False,
        default=ResearchSourceStatus.UNKNOWN,
        server_default=ResearchSourceStatus.UNKNOWN.value,
        index=True,
    )
    quota_status: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="unknown",
        server_default="unknown",
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    documents_fetched_today: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    success_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
        server_default="0",
    )
    average_latency_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    recent_failure_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    config_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
