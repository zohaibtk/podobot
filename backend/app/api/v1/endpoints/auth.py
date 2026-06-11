from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session
from app.modules.settings.schemas import (
    AuthTokenResponse,
    CurrentUserResponse,
    LoginRequest,
    LogoutResponse,
)
from app.modules.settings.service import AuthService
from app.security.auth import (
    CurrentUserDep,
    create_access_token,
    current_user_response,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthService:
    return AuthService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/login", response_model=AuthTokenResponse)
async def login(payload: LoginRequest, service: AuthServiceDep):
    user_payload = await service.login(payload.email, payload.password)
    token = create_access_token(user_payload["id"])
    return {
        "access_token": token.token,
        "expires_at": token.expires_at,
        "refresh_token_placeholder": _refresh_strategy(),
        "user": user_payload,
    }


@router.post("/dev-login", response_model=AuthTokenResponse)
async def dev_login(service: AuthServiceDep):
    if settings.environment != "development" or not settings.auth_dev_auto_login:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Development login is unavailable",
        )
    user_payload = await service.dev_login()
    token = create_access_token(user_payload["id"])
    return {
        "access_token": token.token,
        "expires_at": token.expires_at,
        "refresh_token_placeholder": _refresh_strategy(),
        "user": user_payload,
    }


@router.post("/logout", response_model=LogoutResponse)
async def logout():
    return {"success": True}


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(current_user: CurrentUserDep, service: AuthServiceDep):
    if str(current_user.id) != "00000000-0000-0000-0000-000000000001":
        return await service.current_user_payload(current_user.id)
    return current_user_response(current_user)


def _refresh_strategy() -> str:
    expires_at = datetime.now(UTC) + timedelta(days=settings.auth_refresh_token_days)
    return (
        "Refresh token rotation is reserved for the production identity provider. "
        f"Prototype access expires by {expires_at.isoformat()}."
    )
