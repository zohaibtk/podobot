from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import DiscoveryStatus, SeriesStage, SeriesStatus


def enum_values(enum_type):
    return [item.value for item in enum_type]


class Series(Base):
    __tablename__ = "series"
    __table_args__ = (
        Index("ix_series_status_updated_at", "status", "updated_at"),
        Index("ix_series_discovery_status_updated_at", "discovery_status", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    audience: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    guest_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    status: Mapped[SeriesStatus] = mapped_column(
        Enum(SeriesStatus, name="series_status", values_callable=enum_values),
        nullable=False,
        default=SeriesStatus.RESEARCHING,
        server_default=SeriesStatus.RESEARCHING.value,
    )
    discovery_status: Mapped[DiscoveryStatus] = mapped_column(
        Enum(DiscoveryStatus, name="discovery_status", values_callable=enum_values),
        nullable=False,
        default=DiscoveryStatus.RUNNING,
        server_default=DiscoveryStatus.RUNNING.value,
    )
    current_stage: Mapped[SeriesStage] = mapped_column(
        Enum(SeriesStage, name="series_stage", values_callable=enum_values),
        nullable=False,
        default=SeriesStage.DISCOVERY,
        server_default=SeriesStage.DISCOVERY.value,
    )
    episode_plan_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    plan_locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    briefs_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    captions_unlocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scheduling_unlocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
