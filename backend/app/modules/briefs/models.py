from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import BriefKind, BriefStatus, BriefVersionSource
from app.modules.series.models import enum_values


class EpisodeBrief(Base):
    __tablename__ = "episode_briefs"
    __table_args__ = (
        UniqueConstraint("series_id", "episode_id", "kind", name="uq_episode_briefs_episode_kind"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    series_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("series.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    episode_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("episodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[BriefKind] = mapped_column(
        Enum(BriefKind, name="brief_kind", values_callable=enum_values),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    brief_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[BriefStatus] = mapped_column(
        Enum(BriefStatus, name="brief_status", values_callable=enum_values),
        nullable=False,
        default=BriefStatus.GENERATED,
        server_default=BriefStatus.GENERATED.value,
    )
    current_version_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("brief_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_version_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("brief_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_invalidated_at: Mapped[datetime | None] = mapped_column(
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


class BriefVersion(Base):
    __tablename__ = "brief_versions"
    __table_args__ = (
        UniqueConstraint("brief_id", "version_number", name="uq_brief_versions_brief_version"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    brief_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("episode_briefs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    series_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("series.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    episode_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("episodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outline_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("episode_outlines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outline_version_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("outline_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    brief_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[BriefVersionSource] = mapped_column(
        Enum(BriefVersionSource, name="brief_version_source", values_callable=enum_values),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
