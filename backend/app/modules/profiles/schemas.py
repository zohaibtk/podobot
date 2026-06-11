from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.types import ProfileKind
from app.schemas.pagination import OffsetPageResponse

RequiredText = Annotated[str, Field(min_length=1)]


class ProfileCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: RequiredText = Field(max_length=180)
    role_title: RequiredText = Field(max_length=180)
    kind: ProfileKind
    archetype: RequiredText = Field(max_length=240)
    bio: str | None = Field(default=None, max_length=1200)


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=180)
    role_title: str | None = Field(default=None, min_length=1, max_length=180)
    kind: ProfileKind | None = None
    archetype: str | None = Field(default=None, min_length=1, max_length=240)
    bio: str | None = Field(default=None, max_length=1200)


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    role_title: str
    kind: ProfileKind
    archetype: str
    bio: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProfileListResponse(OffsetPageResponse):
    items: list[ProfileResponse]


class ProfileRecommendationResponse(BaseModel):
    profile: ProfileResponse
    reason: str
    confidence_score: int


class ProfileRecommendationsResponse(BaseModel):
    items: list[ProfileRecommendationResponse]
