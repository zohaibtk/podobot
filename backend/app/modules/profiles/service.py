from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.types import ProfileKind
from app.modules.profiles.models import Profile
from app.modules.profiles.schemas import ProfileCreateRequest, ProfileUpdateRequest
from app.schemas.pagination import OffsetParams, offset_meta


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_profiles(
        self,
        kind: ProfileKind | None = None,
        search: str | None = None,
        archetype: str | None = None,
        include_inactive: bool = False,
    ) -> list[Profile]:
        statement = select(Profile)
        if not include_inactive:
            statement = statement.where(Profile.is_active.is_(True))
        if kind is not None:
            statement = statement.where(Profile.kind == kind)
        if archetype:
            statement = statement.where(Profile.archetype.ilike(f"%{archetype}%"))
        if search:
            query = f"%{search}%"
            statement = statement.where(
                or_(
                    Profile.name.ilike(query),
                    Profile.role_title.ilike(query),
                    Profile.archetype.ilike(query),
                    Profile.bio.ilike(query),
                )
            )

        result = await self.session.execute(
            statement.order_by(Profile.kind.asc(), Profile.name.asc())
        )
        return list(result.scalars().all())

    async def list_profiles_page(
        self,
        *,
        kind: ProfileKind | None = None,
        search: str | None = None,
        archetype: str | None = None,
        include_inactive: bool = False,
        page: int = 1,
        page_size: int = 20,
        sort: str = "name",
    ) -> dict[str, object]:
        pagination = OffsetParams(page=page, page_size=page_size)
        statement = select(Profile)
        if not include_inactive:
            statement = statement.where(Profile.is_active.is_(True))
        if kind is not None:
            statement = statement.where(Profile.kind == kind)
        if archetype:
            statement = statement.where(Profile.archetype.ilike(f"%{archetype}%"))
        if search:
            query = f"%{search}%"
            statement = statement.where(
                or_(
                    Profile.name.ilike(query),
                    Profile.role_title.ilike(query),
                    Profile.archetype.ilike(query),
                    Profile.bio.ilike(query),
                )
            )
        total = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(statement.subquery())
                )
            ).scalar_one()
            or 0
        )
        order_by = {
            "name": (Profile.kind.asc(), Profile.name.asc()),
            "-name": (Profile.kind.asc(), Profile.name.desc()),
            "updated_at": (Profile.updated_at.desc(), Profile.name.asc()),
            "-updated_at": (Profile.updated_at.desc(), Profile.name.asc()),
            "created_at": (Profile.created_at.desc(), Profile.name.asc()),
            "-created_at": (Profile.created_at.desc(), Profile.name.asc()),
        }.get(sort, (Profile.kind.asc(), Profile.name.asc()))
        result = await self.session.execute(
            statement.order_by(*order_by).offset(pagination.offset).limit(pagination.page_size)
        )
        return {
            "items": list(result.scalars().all()),
            **offset_meta(total=total, page=page, page_size=page_size),
        }

    async def get_profile(
        self,
        profile_id: UUID,
        expected_kind: ProfileKind | None = None,
    ) -> Profile:
        profile = await self.session.get(Profile, profile_id)
        if profile is None or not profile.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
        if expected_kind is not None and profile.kind != expected_kind:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Profile must be a {expected_kind.value}",
            )
        return profile

    async def create_profile(self, payload: ProfileCreateRequest) -> Profile:
        await self._assert_unique_name(payload.kind, payload.name)

        profile = Profile(**payload.model_dump())
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def update_profile(self, profile_id: UUID, payload: ProfileUpdateRequest) -> Profile:
        profile = await self.get_profile(profile_id)
        updates = payload.model_dump(exclude_unset=True)
        next_kind = updates.get("kind", profile.kind)
        next_name = updates.get("name", profile.name)
        if "kind" in updates or "name" in updates:
            await self._assert_unique_name(next_kind, next_name, exclude_profile_id=profile.id)

        for field, value in updates.items():
            setattr(profile, field, value)

        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def deactivate_profile(self, profile_id: UUID) -> Profile:
        profile = await self.get_profile(profile_id)
        profile.is_active = False
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def recommendations(
        self,
        kind: ProfileKind,
        search: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, object]]:
        profiles = await self.list_profiles(kind=kind, search=search)
        ranked = sorted(
            profiles,
            key=lambda profile: (
                0 if self._is_high_signal_profile(profile) else 1,
                profile.name,
            ),
        )[:limit]
        return [
            {
                "profile": profile,
                "reason": self._recommendation_reason(profile),
                "confidence_score": self._recommendation_score(profile),
            }
            for profile in ranked
        ]

    async def _assert_unique_name(
        self,
        kind: ProfileKind,
        name: str,
        exclude_profile_id: UUID | None = None,
    ) -> None:
        statement = select(Profile).where(Profile.kind == kind, Profile.name == name)
        if exclude_profile_id is not None:
            statement = statement.where(Profile.id != exclude_profile_id)
        result = await self.session.execute(statement)
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A profile with this name and kind already exists",
            )

    def _is_high_signal_profile(self, profile: Profile) -> bool:
        keywords = ("operator", "moderator", "expert", "voice")
        return any(keyword in profile.archetype.lower() for keyword in keywords)

    def _recommendation_reason(self, profile: Profile) -> str:
        if profile.kind == ProfileKind.HOST:
            return "Matches the host lane for structured editorial guidance."
        return "Matches the guest lane for external signal and audience pressure-testing."

    def _recommendation_score(self, profile: Profile) -> int:
        return 92 if self._is_high_signal_profile(profile) else 84
