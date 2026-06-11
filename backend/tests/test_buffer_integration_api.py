from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.endpoints.buffer import get_buffer_service
from app.db.types import BufferAccountStatus, BufferWebhookStatus, Platform, PublishingAuditStatus
from app.main import create_app


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _channel(channel_id: str | None = None, *, service: str = "linkedin") -> dict[str, object]:
    now = _timestamp()
    return {
        "id": channel_id or str(uuid4()),
        "buffer_account_id": str(uuid4()),
        "buffer_channel_id": f"buf-{service}",
        "service": service,
        "name": f"PodoBot {service}",
        "display_name": f"PodoBot {service.title()}",
        "avatar_url": None,
        "is_enabled": True,
        "is_queue_paused": False,
        "raw_payload": {},
        "last_synced_at": now,
        "created_at": now,
        "updated_at": now,
    }


def _workspace(channel_id: str | None = None) -> dict[str, object]:
    now = _timestamp()
    channel = _channel(channel_id)
    return {
        "account": {
            "id": str(uuid4()),
            "integration_id": str(uuid4()),
            "buffer_account_id": "buf-account",
            "organization_id": "buf-org",
            "name": "PodoBot Buffer",
            "status": BufferAccountStatus.CONNECTED.value,
            "scopes": ["posts:write", "posts:read"],
            "token_expires_at": None,
            "connected_at": now,
            "last_synced_at": now,
            "rate_limit": {},
            "created_at": now,
            "updated_at": now,
        },
        "channels": [channel],
        "mappings": [
            {
                "id": str(uuid4()),
                "platform": Platform.LINKEDIN.value,
                "buffer_channel_id": channel["id"],
                "is_active": True,
                "channel": channel,
                "created_at": now,
                "updated_at": now,
            }
        ],
        "audit_logs": [
            {
                "id": str(uuid4()),
                "schedule_id": None,
                "buffer_account_id": None,
                "buffer_channel_id": None,
                "action": "buffer.post.create",
                "status": PublishingAuditStatus.SUCCEEDED.value,
                "idempotency_key": "idem",
                "request_payload": {},
                "response_payload": {},
                "error_message": None,
                "created_at": now,
            }
        ],
        "webhooks": [],
        "required": True,
        "warnings": [],
    }


class FakeBufferService:
    def __init__(self) -> None:
        self.channel_id = str(uuid4())
        self.mapped: tuple[Platform, str] | None = None

    async def workspace(self):
        return _workspace(self.channel_id)

    async def start_oauth(self):
        return {
            "authorization_url": "https://auth.buffer.com/auth?state=test",
            "state": "test",
            "is_configured": True,
        }

    async def complete_oauth(self, *, code: str, state: str):
        return {"success": bool(code and state), "message": "Connected Buffer OAuth account."}

    async def sync_channels(self):
        return _workspace(self.channel_id)

    async def map_channel(self, platform: Platform, channel_id):
        self.mapped = (platform, str(channel_id))
        return _workspace(str(channel_id))

    async def handle_webhook(self, payload, *, signature, raw_body):
        now = _timestamp()
        return {
            "id": str(uuid4()),
            "event_id": payload["event_id"],
            "event_type": payload["event_type"],
            "buffer_post_id": payload["post_id"],
            "schedule_id": str(uuid4()),
            "status": BufferWebhookStatus.PROCESSED.value,
            "signature_valid": signature is not None or bool(raw_body),
            "payload": payload,
            "received_at": now,
            "processed_at": now,
            "created_at": now,
        }


def _client(service: FakeBufferService | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_buffer_service] = lambda: service or FakeBufferService()
    return TestClient(app)


def test_buffer_workspace_returns_connection_state() -> None:
    response = _client().get("/api/v1/buffer/workspace")

    assert response.status_code == 200
    body = response.json()
    assert body["required"] is True
    assert body["account"]["status"] == "connected"
    assert body["mappings"][0]["channel"]["display_name"] == "PodoBot Linkedin"


def test_buffer_oauth_start_returns_authorization_url() -> None:
    response = _client().post("/api/v1/buffer/oauth/start")

    assert response.status_code == 200
    body = response.json()
    assert body["authorization_url"].startswith("https://auth.buffer.com/auth")
    assert body["is_configured"] is True


def test_buffer_channel_mapping_updates_platform_channel() -> None:
    service = FakeBufferService()
    channel_id = str(uuid4())

    response = _client(service).patch(
        "/api/v1/buffer/channel-mappings/linkedin",
        json={"channel_id": channel_id},
    )

    assert response.status_code == 200
    assert service.mapped == (Platform.LINKEDIN, channel_id)
    assert response.json()["mappings"][0]["buffer_channel_id"] == channel_id


def test_buffer_webhook_returns_processed_event() -> None:
    response = _client().post(
        "/api/v1/buffer/webhooks",
        headers={"X-Buffer-Signature": "sha256=test"},
        json={
            "event_id": "evt_123",
            "event_type": "post.published",
            "post_id": "buf_post_123",
            "status": "published",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processed"
    assert body["buffer_post_id"] == "buf_post_123"
