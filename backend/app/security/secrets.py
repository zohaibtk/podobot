import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

SECRET_SCHEME = "fernet:v1"
SECRET_PREFIX = f"{SECRET_SCHEME}:"


class SecretDecryptionError(ValueError):
    """Raised when an encrypted secret cannot be decrypted."""


def encrypt_secret(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Secret value is required")
    token = _fernet().encrypt(cleaned.encode("utf-8")).decode("ascii")
    return f"{SECRET_PREFIX}{token}"


def decrypt_secret(value: str) -> str:
    if not is_encrypted_secret(value):
        raise SecretDecryptionError("Secret is not encrypted")
    token = value.removeprefix(SECRET_PREFIX).encode("ascii")
    try:
        return _fernet().decrypt(token).decode("utf-8")
    except InvalidToken as exc:
        raise SecretDecryptionError("Secret could not be decrypted") from exc


def is_encrypted_secret(value: object) -> bool:
    return isinstance(value, str) and value.startswith(SECRET_PREFIX)


def mask_secret(secret: str | None) -> str | None:
    if not secret:
        return None
    if len(secret) <= 8:
        return f"{secret[:2]}****{secret[-2:]}"
    return f"{secret[:4]}****{secret[-4:]}"


def _fernet() -> Fernet:
    secret = settings.secrets_encryption_key or settings.auth_jwt_secret
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)
