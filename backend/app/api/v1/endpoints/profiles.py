from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.db.types import ProfileKind
from app.modules.profiles.schemas import (
    ProfileCreateRequest,
    ProfileListResponse,
    ProfileRecommendationResponse,
    ProfileRecommendationsResponse,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.modules.profiles.service import ProfileService
from app.schemas.pagination import offset_meta
from app.security.auth import require_permission

router = APIRouter(prefix="/profiles", tags=["profiles"])


def get_profile_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProfileService:
    return ProfileService(session)


ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]
RequireSeriesView = Depends(require_permission("series.view"))
RequireSeriesEdit = Depends(require_permission("series.edit"))


@router.get("", response_model=ProfileListResponse)
async def list_profiles(
    service: ProfileServiceDep,
    _current_user=RequireSeriesView,
    kind: ProfileKind | None = None,
    search: str | None = Query(default=None, max_length=120),
    archetype: str | None = Query(default=None, max_length=240),
    include_inactive: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    sort: str = Query(default="name", max_length=40),
) -> ProfileListResponse:
    if hasattr(service, "list_profiles_page"):
        response = await service.list_profiles_page(
            kind=kind,
            search=search,
            archetype=archetype,
            include_inactive=include_inactive,
            page=page,
            page_size=page_size,
            sort=sort,
        )
    else:
        items = await service.list_profiles(
            kind=kind,
            search=search,
            archetype=archetype,
            include_inactive=include_inactive,
        )
        response = {
            "items": items,
            **offset_meta(total=len(items), page=page, page_size=page_size),
        }
    await service.session.commit()
    return ProfileListResponse(**response)


@router.get("/search", response_model=ProfileListResponse)
async def search_profiles(
    service: ProfileServiceDep,
    _current_user=RequireSeriesView,
    q: str | None = Query(default=None, max_length=120),
    kind: ProfileKind | None = None,
    archetype: str | None = Query(default=None, max_length=240),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    sort: str = Query(default="name", max_length=40),
) -> ProfileListResponse:
    if hasattr(service, "list_profiles_page"):
        response = await service.list_profiles_page(
            kind=kind,
            search=q,
            archetype=archetype,
            page=page,
            page_size=page_size,
            sort=sort,
        )
    else:
        items = await service.list_profiles(kind=kind, search=q, archetype=archetype)
        response = {
            "items": items,
            **offset_meta(total=len(items), page=page, page_size=page_size),
        }
    await service.session.commit()
    return ProfileListResponse(**response)


@router.get("/recommendations", response_model=ProfileRecommendationsResponse)
async def recommend_profiles(
    service: ProfileServiceDep,
    kind: ProfileKind,
    _current_user=RequireSeriesView,
    search: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=5, ge=1, le=12),
) -> ProfileRecommendationsResponse:
    items = await service.recommendations(kind=kind, search=search, limit=limit)
    await service.session.commit()
    return ProfileRecommendationsResponse(
        items=[ProfileRecommendationResponse(**item) for item in items]
    )


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: ProfileCreateRequest,
    service: ProfileServiceDep,
    _current_user=RequireSeriesEdit,
) -> ProfileResponse:
    return await service.create_profile(payload)


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: UUID,
    service: ProfileServiceDep,
    _current_user=RequireSeriesView,
) -> ProfileResponse:
    profile = await service.get_profile(profile_id)
    await service.session.commit()
    return profile


@router.patch("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: UUID,
    payload: ProfileUpdateRequest,
    service: ProfileServiceDep,
    _current_user=RequireSeriesEdit,
) -> ProfileResponse:
    return await service.update_profile(profile_id, payload)


@router.delete("/{profile_id}", response_model=ProfileResponse)
async def deactivate_profile(
    profile_id: UUID,
    service: ProfileServiceDep,
    _current_user=RequireSeriesEdit,
) -> ProfileResponse:
    return await service.deactivate_profile(profile_id)
