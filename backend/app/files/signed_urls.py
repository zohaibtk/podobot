import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from app.core.config import settings


@dataclass(frozen=True)
class SignedMediaURL:
    url: str
    expires_at: datetime


class SignedURLService:
    def __init__(self, secret: str | None = None) -> None:
        self.secret = (secret or settings.auth_jwt_secret).encode("utf-8")

    def create(self, storage_key: str, *, expires_in_seconds: int | None = None) -> SignedMediaURL:
        expires_at = datetime.now(UTC) + timedelta(
            seconds=expires_in_seconds or settings.media_signed_url_seconds
        )
        payload = {
            "key": storage_key,
            "exp": int(expires_at.timestamp()),
        }
        encoded_payload = self._b64encode(json.dumps(payload, separators=(",", ":")).encode())
        signature = self._sign(encoded_payload)
        token = f"{encoded_payload}.{signature}"
        return SignedMediaURL(url=f"/api/v1/media/signed/{token}", expires_at=expires_at)

    def verify(self, token: str) -> str:
        try:
            encoded_payload, provided_signature = token.split(".", 1)
        except ValueError as exc:
            raise self._invalid_token() from exc

        expected_signature = self._sign(encoded_payload)
        if not hmac.compare_digest(provided_signature, expected_signature):
            raise self._invalid_token()

        try:
            payload = json.loads(self._b64decode(encoded_payload))
            storage_key = str(payload["key"])
            expires_at = int(payload["exp"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise self._invalid_token() from exc

        if datetime.now(UTC).timestamp() > expires_at:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Signed media URL has expired",
            )
        return storage_key

    def _sign(self, encoded_payload: str) -> str:
        digest = hmac.new(
            self.secret,
            encoded_payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return self._b64encode(digest)

    def _b64encode(self, payload: bytes) -> str:
        return base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")

    def _b64decode(self, payload: str) -> str:
        padding = "=" * (-len(payload) % 4)
        return base64.urlsafe_b64decode(f"{payload}{padding}").decode("utf-8")

    def _invalid_token(self) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid signed media URL",
        )
