from typing import cast

from app.mcp.security import redact_sensitive


def redact_mapping(payload: dict[str, object]) -> dict[str, object]:
    return cast(dict[str, object], redact_sensitive(payload))
