from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import ProfileKind
from app.modules.series.models import enum_values


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        UniqueConstraint("kind", "name", name="uq_profiles_kind_name"),
        Index("ix_profiles_kind", "kind"),
        Index("ix_profiles_kind_archetype", "kind", "archetype"),
        Index("ix_profiles_name", "name"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    role_title: Mapped[str] = mapped_column(String(180), nullable=False)
    kind: Mapped[ProfileKind] = mapped_column(
        Enum(ProfileKind, name="profile_kind", values_callable=enum_values),
        nullable=False,
    )
    archetype: Mapped[str] = mapped_column(String(240), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
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
