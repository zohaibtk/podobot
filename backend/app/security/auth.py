import base64
import hashlib
import hmac
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session
from app.db.types import WorkspaceUserStatus
from app.modules.settings.service import DEFAULT_PERMISSION_KEYS, AuthorizationService

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class TokenResult:
    token: str
    expires_at: datetime


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    email: str
    full_name: str | None
    status: WorkspaceUserStatus
    role_keys: frozenset[str]
    permissions: frozenset[str]

    def has_permission(self, permission: str) -> bool:
        return "*" in self.permissions or permission in self.permissions

    def has_role(self, role_key: str) -> bool:
        return role_key in self.role_keys

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "CurrentUser":
        return cls(
            id=UUID(str(payload["id"])),
            email=str(payload["email"]),
            full_name=payload.get("full_name"),
            status=WorkspaceUserStatus(str(payload["status"])),
            role_keys=frozenset(_role_key(role) for role in payload["roles"]),
            permissions=frozenset(str(permission) for permission in payload["permissions"]),
        )

    @classmethod
    def development_admin(cls) -> "CurrentUser":
        return cls(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            email="admin@podobot.com",
            full_name="PodoBot Admin",
            status=WorkspaceUserStatus.ACTIVE,
            role_keys=frozenset({"admin"}),
            permissions=frozenset(DEFAULT_PERMISSION_KEYS),
        )


def create_access_token(user_id: UUID) -> TokenResult:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.auth_access_token_minutes)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": int(expires_at.timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
    }
    return TokenResult(token=_encode_jwt(payload), expires_at=expires_at)


def decode_access_token(token: str) -> dict[str, object]:
    try:
        header_raw, payload_raw, signature_raw = token.split(".", 2)
    except ValueError as exc:
        raise _unauthorized("Invalid access token") from exc

    expected = _sign(f"{header_raw}.{payload_raw}".encode("ascii"))
    actual = _b64url_decode(signature_raw)
    if not hmac.compare_digest(actual, expected):
        raise _unauthorized("Invalid access token")

    payload = json.loads(_b64url_decode(payload_raw))
    if payload.get("type") != "access":
        raise _unauthorized("Invalid access token")
    if int(payload.get("exp", 0)) < int(datetime.now(UTC).timestamp()):
        raise _unauthorized("Access token expired")
    return payload


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CurrentUser:
    if credentials is None:
        if settings.environment == "development" and settings.auth_dev_auto_login:
            return CurrentUser.development_admin()
        raise _unauthorized("Authentication required")

    payload = decode_access_token(credentials.credentials)
    try:
        user_id = UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise _unauthorized("Invalid access token") from exc
    user_payload = await AuthorizationService(session).current_user_payload(user_id)
    return CurrentUser.from_payload(user_payload)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_permission(permission: str) -> Callable[[CurrentUserDep], CurrentUser]:
    async def dependency(current_user: CurrentUserDep) -> CurrentUser:
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}",
            )
        return current_user

    return dependency


def require_role(role_key: str) -> Callable[[CurrentUserDep], CurrentUser]:
    async def dependency(current_user: CurrentUserDep) -> CurrentUser:
        if not current_user.has_role(role_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role_key}",
            )
        return current_user

    return dependency


def current_user_response(user: CurrentUser) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.full_name or user.email,
        "full_name": user.full_name,
        "status": user.status,
        "roles": [
            {
                "id": user.id,
                "key": role_key,
                "name": role_key.replace("_", " ").title(),
                "description": "Current user role.",
                "is_system": role_key == "admin",
                "is_assignable": True,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
            for role_key in sorted(user.role_keys)
        ],
        "permissions": sorted(user.permissions),
    }


def _role_key(role: object) -> str:
    if isinstance(role, dict):
        return str(role["key"])
    return str(role.key)


def _encode_jwt(payload: dict[str, object]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_raw = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_raw = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _b64url_encode(_sign(f"{header_raw}.{payload_raw}".encode("ascii")))
    return f"{header_raw}.{payload_raw}.{signature}"


def _sign(data: bytes) -> bytes:
    return hmac.new(
        settings.auth_jwt_secret.encode("utf-8"),
        data,
        hashlib.sha256,
    ).digest()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
