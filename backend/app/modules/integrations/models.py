from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
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
from app.db.types import IntegrationStatus, IntegrationType
from app.modules.series.models import enum_values


class Integration(Base):
    __tablename__ = "integrations"
    __table_args__ = (UniqueConstraint("type", name="uq_integrations_type"),)

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    type: Mapped[IntegrationType] = mapped_column(
        Enum(IntegrationType, name="integration_type", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    is_critical: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    status: Mapped[IntegrationStatus] = mapped_column(
        Enum(IntegrationStatus, name="integration_status", values_callable=enum_values),
        nullable=False,
        default=IntegrationStatus.NOT_CONFIGURED,
        server_default=IntegrationStatus.NOT_CONFIGURED.value,
    )
    api_key_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    quota: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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


class IntegrationAuditLog(Base):
    __tablename__ = "integration_audit_logs"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    integration_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    actor: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="system",
        server_default="system",
    )
    previous_status: Mapped[IntegrationStatus | None] = mapped_column(
        Enum(IntegrationStatus, name="integration_status", values_callable=enum_values),
        nullable=True,
    )
    new_status: Mapped[IntegrationStatus | None] = mapped_column(
        Enum(IntegrationStatus, name="integration_status", values_callable=enum_values),
        nullable=True,
    )
    redacted_changes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
