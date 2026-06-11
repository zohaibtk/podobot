from app.mcp.security import is_sensitive_key, redact_sensitive
from app.security.redaction import redact_mapping


def test_shared_redaction_recurses_into_nested_payloads() -> None:
    redacted = redact_sensitive(
        {
            "api_key": "raw-key",
            "nested": {
                "access_token": "raw-token",
                "safe": "visible",
                "items": [{"password": "raw-password"}],
            },
        }
    )

    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["access_token"] == "[REDACTED]"
    assert redacted["nested"]["safe"] == "visible"
    assert redacted["nested"]["items"][0]["password"] == "[REDACTED]"


def test_legacy_redact_mapping_uses_shared_recursive_redaction() -> None:
    redacted = redact_mapping(
        {
            "Authorization": "Bearer raw-token",
            "data": {"client_secret": "raw-secret", "safe": "visible"},
        }
    )

    assert redacted["Authorization"] == "[REDACTED]"
    assert redacted["data"]["client_secret"] == "[REDACTED]"
    assert redacted["data"]["safe"] == "visible"


def test_redaction_does_not_mask_safe_resource_identifiers() -> None:
    assert is_sensitive_key("brief") is True
    assert is_sensitive_key("transcript") is True
    assert is_sensitive_key("brief_id") is False
    assert is_sensitive_key("transcript_status") is False
