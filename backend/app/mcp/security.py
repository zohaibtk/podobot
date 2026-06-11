EXACT_SENSITIVE_KEYS = ("authorization", "brief", "transcript")
SENSITIVE_MARKERS = ("api_key", "apikey", "secret", "token", "password", "credential")


def is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return normalized in EXACT_SENSITIVE_KEYS or any(
        marker in normalized for marker in SENSITIVE_MARKERS
    )


def redact_sensitive(value: object) -> object:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if is_sensitive_key(str(key)) else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


def mask_secret(secret: str | None) -> str | None:
    if not secret:
        return None
    if len(secret) <= 8:
        return f"{secret[:2]}****{secret[-2:]}"
    return f"{secret[:4]}****{secret[-4:]}"
