import base64
import hashlib
import hmac
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.types import (
    BufferAccountStatus,
    BufferPostStatus,
    BufferWebhookStatus,
    IntegrationStatus,
    IntegrationType,
    Platform,
    PublishingAuditStatus,
    ScheduleStatus,
)
from app.modules.captions.models import EpisodeVideoPlatformCaption
from app.modules.integrations.models import Integration
from app.modules.schedules.models import (
    BufferAccount,
    BufferChannel,
    BufferChannelMapping,
    BufferWebhook,
    EpisodeVideoPlatformSchedule,
    PublishingAuditLog,
)

BUFFER_SCOPES = [
    "posts:write",
    "posts:read",
    "account:read",
    "offline_access",
]

PLATFORM_SERVICE_ALIASES: dict[Platform, set[str]] = {
    Platform.LINKEDIN: {"linkedin"},
    Platform.FACEBOOK: {"facebook", "facebook_pages"},
    Platform.YOUTUBE: {"youtube"},
    Platform.INSTAGRAM: {"instagram"},
    Platform.TIKTOK: {"tiktok"},
    Platform.X: {"x", "twitter"},
}


@dataclass(frozen=True)
class BufferPostResult:
    post_id: str
    status: BufferPostStatus
    failure_reason: str | None = None
    live_url: str | None = None
    rate_limit: dict[str, object] | None = None
    retry_after_seconds: int | None = None
    raw_response: dict[str, object] | None = None


@dataclass(frozen=True)
class BufferOAuthStart:
    authorization_url: str
    state: str
    is_configured: bool


class BufferRateLimitError(Exception):
    def __init__(
        self,
        message: str,
        *,
        retry_after_seconds: int | None = None,
        rate_limit: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
        self.rate_limit = rate_limit or {}


class BufferGraphQLClient:
    def request(
        self,
        access_token: str,
        query: str,
        variables: dict[str, object],
    ) -> dict[str, Any]:
        payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        request = urllib.request.Request(
            settings.buffer_api_base_url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=settings.buffer_request_timeout_seconds,
            ) as response:
                body = response.read()
                rate_limit = self._rate_limit_from_headers(response.headers)
        except urllib.error.HTTPError as exc:
            rate_limit = self._rate_limit_from_headers(exc.headers)
            body = exc.read()
            if exc.code == 429:
                retry_after = self._retry_after(body, exc.headers)
                raise BufferRateLimitError(
                    "Buffer rate limit exceeded",
                    retry_after_seconds=retry_after,
                    rate_limit=rate_limit,
                ) from exc
            raise RuntimeError(f"Buffer API HTTP {exc.code}") from exc
        result = json.loads(body.decode("utf-8"))
        if result.get("errors"):
            error = result["errors"][0]
            code = (error.get("extensions") or {}).get("code")
            if code == "RATE_LIMIT_EXCEEDED":
                retry_after = (error.get("extensions") or {}).get("retryAfter")
                raise BufferRateLimitError(
                    str(error.get("message") or "Buffer rate limit exceeded"),
                    retry_after_seconds=int(retry_after) if retry_after is not None else None,
                    rate_limit=rate_limit,
                )
            raise RuntimeError(f"Buffer API error ({code}): {error.get('message')}")
        result["_rate_limit"] = rate_limit
        return result

    def _rate_limit_from_headers(self, headers) -> dict[str, object]:
        return {
            "limit": headers.get("RateLimit-Limit"),
            "remaining": headers.get("RateLimit-Remaining"),
            "reset": headers.get("RateLimit-Reset"),
        }

    def _retry_after(self, body: bytes, headers) -> int | None:
        retry_after = headers.get("Retry-After")
        if retry_after:
            return int(retry_after)
        try:
            error = json.loads(body.decode("utf-8"))["errors"][0]
            value = (error.get("extensions") or {}).get("retryAfter")
            return int(value) if value is not None else None
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            return None


class BufferPublishingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.graphql = BufferGraphQLClient()

    async def workspace(self) -> dict[str, object]:
        await self._ensure_buffer_integration()
        account = await self._active_account()
        channels = await self._channels(account.id) if account is not None else []
        mappings = await self._mappings()
        return {
            "account": account,
            "channels": channels,
            "mappings": [self._mapping_payload(mapping, channels) for mapping in mappings],
            "audit_logs": await self._recent_audit_logs(),
            "webhooks": await self._recent_webhooks(),
            "required": True,
            "warnings": self._workspace_warnings(account, channels, mappings),
        }

    async def start_oauth(self) -> BufferOAuthStart:
        integration = await self._ensure_buffer_integration()
        account = await self._ensure_account(integration)
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(48)
        challenge = self._code_challenge(verifier)
        account.oauth_state = state
        account.pkce_verifier = verifier
        account.status = BufferAccountStatus.OAUTH_PENDING

        is_configured = bool(settings.buffer_client_id)
        if not is_configured:
            await self._connect_development_account(account)
            await self.session.commit()
            return BufferOAuthStart(authorization_url="", state=state, is_configured=False)

        await self.session.commit()
        query = {
            "client_id": settings.buffer_client_id or "development-client",
            "redirect_uri": settings.buffer_redirect_uri,
            "response_type": "code",
            "scope": " ".join(BUFFER_SCOPES),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "prompt": "consent",
        }
        return BufferOAuthStart(
            authorization_url=f"{settings.buffer_auth_url}?{urllib.parse.urlencode(query)}",
            state=state,
            is_configured=is_configured,
        )

    async def complete_oauth(self, *, code: str, state: str) -> dict[str, object]:
        account = await self._pending_oauth_account(state)
        if not settings.buffer_client_id:
            await self._connect_development_account(account)
            await self.session.commit()
            return {"success": True, "message": "Connected Buffer in development mode."}

        token_payload = await self._exchange_oauth_code(account, code)
        now = datetime.now(UTC)
        account.status = BufferAccountStatus.CONNECTED
        account.access_token_secret = str(token_payload["access_token"])
        account.refresh_token_secret = (
            str(token_payload["refresh_token"])
            if token_payload.get("refresh_token") is not None
            else account.refresh_token_secret
        )
        account.token_expires_at = now + timedelta(
            seconds=int(token_payload.get("expires_in") or 3600)
        )
        account.scopes = str(token_payload.get("scope") or " ".join(BUFFER_SCOPES)).split()
        account.connected_at = now
        account.oauth_state = None
        account.pkce_verifier = None
        self._refresh_account_context(account)
        await self.sync_channels()
        await self.session.commit()
        return {"success": True, "message": "Connected Buffer OAuth account."}

    async def sync_channels(self) -> dict[str, object]:
        account = await self._require_connected_account()
        if self._is_development_account(account):
            channels = await self._upsert_development_channels(account)
        else:
            if not account.organization_id:
                self._refresh_account_context(account)
            channels = await self._fetch_live_channels(account)
        account.last_synced_at = datetime.now(UTC)
        await self._ensure_default_mappings(channels)
        await self.session.commit()
        return await self.workspace()

    async def map_channel(self, platform: Platform, channel_id: UUID) -> dict[str, object]:
        channel = await self.session.get(BufferChannel, channel_id)
        if channel is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Buffer channel not found",
            )
        self._validate_channel_mapping(platform, channel)
        result = await self.session.execute(
            select(BufferChannelMapping).where(BufferChannelMapping.platform == platform)
        )
        mapping = result.scalar_one_or_none()
        if mapping is None:
            mapping = BufferChannelMapping(platform=platform, buffer_channel_id=channel.id)
            self.session.add(mapping)
        else:
            mapping.buffer_channel_id = channel.id
            mapping.is_active = True
        await self.session.commit()
        return await self.workspace()

    async def create_post(
        self,
        caption: EpisodeVideoPlatformCaption,
        scheduled_for: datetime,
        text: str,
        *,
        idempotency_key: str,
    ) -> tuple[BufferPostResult, BufferAccount, BufferChannel]:
        account, channel = await self._publishing_target(caption.platform)
        existing = await self._schedule_by_idempotency_key(idempotency_key)
        if existing is not None and existing.buffer_post_id:
            return (
                BufferPostResult(
                    post_id=existing.buffer_post_id,
                    status=existing.buffer_status,
                    failure_reason=existing.failure_reason,
                    live_url=existing.live_url,
                    raw_response={"idempotent_replay": True},
                ),
                account,
                channel,
            )
        try:
            result = await self._create_post_with_adapter(
                account,
                channel,
                scheduled_for,
                text,
                idempotency_key,
            )
            self._audit(
                "buffer.post.create",
                PublishingAuditStatus.SUCCEEDED
                if result.status != BufferPostStatus.FAILED
                else PublishingAuditStatus.FAILED,
                account=account,
                channel=channel,
                idempotency_key=idempotency_key,
                request_payload=self._post_payload(channel, scheduled_for, text),
                response_payload=result.raw_response or {},
                error_message=result.failure_reason,
            )
            return result, account, channel
        except BufferRateLimitError as exc:
            result = BufferPostResult(
                post_id=self._fallback_post_id(idempotency_key),
                status=BufferPostStatus.FAILED,
                failure_reason="Buffer rate limit exceeded; retry later.",
                retry_after_seconds=exc.retry_after_seconds,
                rate_limit=exc.rate_limit,
                raw_response={"rate_limit": exc.rate_limit},
            )
            self._audit(
                "buffer.post.create",
                PublishingAuditStatus.RATE_LIMITED,
                account=account,
                channel=channel,
                idempotency_key=idempotency_key,
                request_payload=self._post_payload(channel, scheduled_for, text),
                response_payload=result.raw_response or {},
                error_message=result.failure_reason,
            )
            return result, account, channel
        except RuntimeError as exc:
            result = BufferPostResult(
                post_id=self._fallback_post_id(idempotency_key),
                status=BufferPostStatus.FAILED,
                failure_reason=str(exc),
                raw_response={"error": str(exc)},
            )
            self._audit(
                "buffer.post.create",
                PublishingAuditStatus.FAILED,
                account=account,
                channel=channel,
                idempotency_key=idempotency_key,
                request_payload=self._post_payload(channel, scheduled_for, text),
                response_payload=result.raw_response or {},
                error_message=result.failure_reason,
            )
            return result, account, channel

    async def update_post(
        self,
        schedule: EpisodeVideoPlatformSchedule,
        text: str,
    ) -> BufferPostResult:
        account, channel = await self._schedule_target(schedule)
        if account is not None and not self._is_development_account(account):
            result = self._live_update_result(account, schedule, text)
        else:
            result = self._development_update_result(schedule, text)
        self._audit_for_schedule(
            schedule,
            "buffer.post.update",
            PublishingAuditStatus.SUCCEEDED
            if result.status != BufferPostStatus.FAILED
            else PublishingAuditStatus.FAILED,
            request_payload={"text": text, "post_id": schedule.buffer_post_id},
            response_payload=result.raw_response or {},
            error_message=result.failure_reason,
            account=account,
            channel=channel,
        )
        return result

    async def cancel_post(self, schedule: EpisodeVideoPlatformSchedule) -> BufferPostResult:
        account, channel = await self._schedule_target(schedule)
        if account is not None and not self._is_development_account(account):
            result = self._live_cancel_result(account, schedule)
        else:
            result = BufferPostResult(
                post_id=schedule.buffer_post_id or self._fallback_post_id(schedule.id.hex),
                status=BufferPostStatus.CANCELLED,
                raw_response={"cancelled": True},
            )
        self._audit_for_schedule(
            schedule,
            "buffer.post.cancel",
            PublishingAuditStatus.SUCCEEDED
            if result.status != BufferPostStatus.FAILED
            else PublishingAuditStatus.FAILED,
            request_payload={"post_id": result.post_id},
            response_payload=result.raw_response or {},
            error_message=result.failure_reason,
            account=account,
            channel=channel,
        )
        return result

    async def sync_post(
        self,
        schedule: EpisodeVideoPlatformSchedule,
        now: datetime,
    ) -> BufferPostResult:
        account, channel = await self._schedule_target(schedule)
        if account is None:
            result = BufferPostResult(
                post_id=schedule.buffer_post_id or self._fallback_post_id(schedule.id.hex),
                status=BufferPostStatus.FAILED,
                failure_reason=(
                    "Buffer is not connected. Connect a real Buffer account and reschedule "
                    "this post."
                ),
                raw_response={"missing_buffer_account": True},
            )
        elif not self._is_development_account(account):
            result = self._live_sync_result(account, schedule)
            result = self._fail_overdue_queue(schedule, result, now)
        elif schedule.scheduled_for <= now:
            result = BufferPostResult(
                post_id=schedule.buffer_post_id or self._fallback_post_id(schedule.id.hex),
                status=BufferPostStatus.FAILED,
                failure_reason=(
                    "This post was queued in the development Buffer connector, so it was not "
                    "published to LinkedIn or Facebook. Configure Buffer OAuth, connect a real "
                    "Buffer account, then reschedule this post."
                ),
                raw_response={"synced": True, "status": "development_queue_due"},
            )
        else:
            result = BufferPostResult(
                post_id=schedule.buffer_post_id or self._fallback_post_id(schedule.id.hex),
                status=BufferPostStatus.QUEUED,
                raw_response={"synced": True, "status": "scheduled"},
            )
        self._audit_for_schedule(
            schedule,
            "buffer.post.sync",
            PublishingAuditStatus.SUCCEEDED
            if result.status != BufferPostStatus.FAILED
            else PublishingAuditStatus.FAILED,
            request_payload={"post_id": result.post_id},
            response_payload=result.raw_response or {},
            error_message=result.failure_reason,
            account=account,
            channel=channel,
        )
        return result

    async def retry_due_posts(self, *, limit: int = 25) -> dict[str, int]:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(EpisodeVideoPlatformSchedule)
            .where(
                EpisodeVideoPlatformSchedule.status == ScheduleStatus.FAILED,
                EpisodeVideoPlatformSchedule.next_retry_at.is_not(None),
                EpisodeVideoPlatformSchedule.next_retry_at <= now,
                EpisodeVideoPlatformSchedule.retry_count < settings.buffer_max_publish_retries,
            )
            .order_by(EpisodeVideoPlatformSchedule.next_retry_at.asc())
            .limit(limit)
        )
        schedules = list(result.scalars().all())
        retried_count = 0
        failed_count = 0
        for schedule in schedules:
            caption = await self.session.get(EpisodeVideoPlatformCaption, schedule.caption_id)
            if caption is None:
                continue
            schedule.retry_count += 1
            idempotency_key = schedule.idempotency_key or self.idempotency_key(
                caption,
                schedule.scheduled_for,
                schedule.scheduled_caption_text,
            )
            post_result, account, channel = await self.create_post(
                caption,
                schedule.scheduled_for,
                schedule.scheduled_caption_text,
                idempotency_key=idempotency_key,
            )
            schedule.buffer_account_id = account.id
            schedule.buffer_channel_id = channel.id
            schedule.idempotency_key = idempotency_key
            self.apply_result(schedule, post_result, schedule.scheduled_for)
            self._audit_for_schedule(
                schedule,
                "buffer.post.retry",
                PublishingAuditStatus.RETRY_SCHEDULED
                if post_result.status != BufferPostStatus.FAILED
                else PublishingAuditStatus.FAILED,
                response_payload=post_result.raw_response or {},
                error_message=post_result.failure_reason,
                account=account,
                channel=channel,
            )
            retried_count += 1
            if schedule.status == ScheduleStatus.FAILED:
                failed_count += 1
        await self.session.commit()
        return {"retried_count": retried_count, "failed_count": failed_count}

    async def handle_webhook(
        self,
        payload: dict[str, object],
        *,
        signature: str | None,
        raw_body: bytes,
    ) -> BufferWebhook:
        now = datetime.now(UTC)
        signature_valid = self._verify_webhook_signature(raw_body, signature)
        event_id = str(payload.get("event_id") or payload.get("id") or "") or None
        event_type = str(payload.get("event_type") or payload.get("type") or "unknown")
        post_id = str(payload.get("post_id") or payload.get("postId") or "") or None
        existing = None
        if event_id:
            result = await self.session.execute(
                select(BufferWebhook).where(BufferWebhook.event_id == event_id)
            )
            existing = result.scalar_one_or_none()
        if existing is not None:
            return existing

        schedule = await self._schedule_by_buffer_post_id(post_id) if post_id else None
        webhook = BufferWebhook(
            event_id=event_id,
            event_type=event_type,
            buffer_post_id=post_id,
            schedule_id=schedule.id if schedule else None,
            status=BufferWebhookStatus.RECEIVED,
            signature_valid=signature_valid,
            payload=payload,
            received_at=now,
        )
        self.session.add(webhook)
        if not signature_valid:
            webhook.status = BufferWebhookStatus.FAILED
            webhook.processed_at = now
        elif schedule is None:
            webhook.status = BufferWebhookStatus.IGNORED
            webhook.processed_at = now
        else:
            result = self._result_from_webhook(schedule, payload)
            self.apply_result(schedule, result, schedule.scheduled_for)
            schedule.buffer_last_event_id = event_id
            webhook.status = BufferWebhookStatus.PROCESSED
            webhook.processed_at = now
            self._audit_for_schedule(
                schedule,
                "buffer.webhook.processed",
                PublishingAuditStatus.SUCCEEDED
                if result.status != BufferPostStatus.FAILED
                else PublishingAuditStatus.FAILED,
                request_payload=payload,
                response_payload=result.raw_response or {},
                error_message=result.failure_reason,
            )
        await self.session.commit()
        return webhook

    def apply_result(
        self,
        schedule: EpisodeVideoPlatformSchedule,
        result: BufferPostResult,
        scheduled_for: datetime,
    ) -> None:
        now = datetime.now(UTC)
        schedule.buffer_post_id = result.post_id
        schedule.buffer_status = result.status
        schedule.scheduled_for = scheduled_for
        schedule.last_synced_at = now
        schedule.live_url = result.live_url
        schedule.rate_limit_reset_at = self._rate_limit_reset_at(result.rate_limit)
        if result.retry_after_seconds:
            schedule.next_retry_at = now + timedelta(seconds=result.retry_after_seconds)
        if result.status == BufferPostStatus.FAILED:
            schedule.status = ScheduleStatus.FAILED
            schedule.failure_reason = result.failure_reason or "Buffer publishing failed."
            schedule.published_at = None
            schedule.cancelled_at = None
        elif result.status == BufferPostStatus.PUBLISHED:
            schedule.status = ScheduleStatus.PUBLISHED
            schedule.failure_reason = None
            schedule.next_retry_at = None
            schedule.published_at = now
            schedule.cancelled_at = None
        elif result.status == BufferPostStatus.CANCELLED:
            schedule.status = ScheduleStatus.CANCELLED
            schedule.failure_reason = None
            schedule.next_retry_at = None
            schedule.cancelled_at = now
        else:
            schedule.status = ScheduleStatus.SCHEDULED
            schedule.failure_reason = None
            schedule.next_retry_at = None
            schedule.scheduled_at = now
            schedule.published_at = None
            schedule.cancelled_at = None

    async def _create_post_with_adapter(
        self,
        account: BufferAccount,
        channel: BufferChannel,
        scheduled_for: datetime,
        text: str,
        idempotency_key: str,
    ) -> BufferPostResult:
        if self._is_development_account(account):
            return self._development_create_result(channel, scheduled_for, text, idempotency_key)

        data = self.graphql.request(
            str(account.access_token_secret),
            """
            mutation CreatePost($input: CreatePostInput!) {
              createPost(input: $input) {
                ... on PostActionSuccess {
                  post { id dueAt status channelId }
                }
                ... on MutationError { message }
              }
            }
            """,
            {"input": self._post_payload(channel, scheduled_for, text)},
        )
        account.rate_limit = data.get("_rate_limit") or {}
        create_post = data.get("data", {}).get("createPost", {})
        if create_post.get("message"):
            return BufferPostResult(
                post_id=self._fallback_post_id(idempotency_key),
                status=BufferPostStatus.FAILED,
                failure_reason=str(create_post["message"]),
                raw_response=create_post,
            )
        post = create_post.get("post") or {}
        return BufferPostResult(
            post_id=str(post.get("id") or self._fallback_post_id(idempotency_key)),
            status=self._post_status(str(post.get("status") or "scheduled")),
            raw_response=create_post,
        )

    def _development_create_result(
        self,
        channel: BufferChannel,
        scheduled_for: datetime,
        text: str,
        idempotency_key: str,
    ) -> BufferPostResult:
        if channel.is_queue_paused:
            return BufferPostResult(
                post_id=self._fallback_post_id(idempotency_key),
                status=BufferPostStatus.FAILED,
                failure_reason="Mapped Buffer channel queue is paused.",
                raw_response={"channel_paused": True},
            )
        if channel.service == "x" and len(text) > 280:
            return BufferPostResult(
                post_id=self._fallback_post_id(idempotency_key),
                status=BufferPostStatus.FAILED,
                failure_reason="Buffer rejected X copy above 280 characters.",
                raw_response={"validation": "x_character_limit"},
            )
        return BufferPostResult(
            post_id=f"buf_{idempotency_key[:18]}",
            status=BufferPostStatus.QUEUED,
            raw_response={
                "post": {
                    "id": f"buf_{idempotency_key[:18]}",
                    "dueAt": scheduled_for.isoformat(),
                    "channelId": channel.buffer_channel_id,
                }
            },
        )

    def _development_update_result(
        self,
        schedule: EpisodeVideoPlatformSchedule,
        text: str,
    ) -> BufferPostResult:
        if schedule.platform == Platform.X and len(text) > 280:
            return BufferPostResult(
                post_id=schedule.buffer_post_id or self._fallback_post_id(schedule.id.hex),
                status=BufferPostStatus.FAILED,
                failure_reason="Buffer rejected X copy above 280 characters.",
                raw_response={"validation": "x_character_limit"},
            )
        return BufferPostResult(
            post_id=schedule.buffer_post_id or self._fallback_post_id(schedule.id.hex),
            status=BufferPostStatus.QUEUED,
            raw_response={"updated": True},
        )

    def _live_update_result(
        self,
        account: BufferAccount,
        schedule: EpisodeVideoPlatformSchedule,
        text: str,
    ) -> BufferPostResult:
        if not schedule.buffer_post_id:
            return BufferPostResult(
                post_id=self._fallback_post_id(schedule.id.hex),
                status=BufferPostStatus.FAILED,
                failure_reason="Buffer post ID is missing.",
                raw_response={"missing_post_id": True},
            )
        try:
            data = self.graphql.request(
                str(account.access_token_secret),
                """
                mutation EditPost($input: EditPostInput!) {
                  editPost(input: $input) {
                    ... on PostActionSuccess {
                      post { id dueAt status externalLink }
                    }
                    ... on MutationError { message }
                  }
                }
                """,
                {
                    "input": {
                        "id": schedule.buffer_post_id,
                        "text": text,
                        "dueAt": schedule.scheduled_for.astimezone(UTC).isoformat(),
                    }
                },
            )
            account.rate_limit = data.get("_rate_limit") or {}
            return self._post_action_result(
                "editPost",
                data,
                fallback_id=schedule.buffer_post_id,
            )
        except BufferRateLimitError as exc:
            return self._rate_limited_result(schedule, exc)
        except RuntimeError as exc:
            return BufferPostResult(
                post_id=schedule.buffer_post_id,
                status=BufferPostStatus.FAILED,
                failure_reason=str(exc),
                raw_response={"error": str(exc)},
            )

    def _live_cancel_result(
        self,
        account: BufferAccount,
        schedule: EpisodeVideoPlatformSchedule,
    ) -> BufferPostResult:
        if not schedule.buffer_post_id:
            return BufferPostResult(
                post_id=self._fallback_post_id(schedule.id.hex),
                status=BufferPostStatus.FAILED,
                failure_reason="Buffer post ID is missing.",
                raw_response={"missing_post_id": True},
            )
        try:
            data = self.graphql.request(
                str(account.access_token_secret),
                """
                mutation DeletePost($input: DeletePostInput!) {
                  deletePost(input: $input) {
                    ... on DeletePostSuccess { id }
                    ... on MutationError { message }
                  }
                }
                """,
                {"input": {"id": schedule.buffer_post_id}},
            )
            account.rate_limit = data.get("_rate_limit") or {}
            delete_post = data.get("data", {}).get("deletePost", {})
            if delete_post.get("message"):
                return BufferPostResult(
                    post_id=schedule.buffer_post_id,
                    status=BufferPostStatus.FAILED,
                    failure_reason=str(delete_post["message"]),
                    raw_response=delete_post,
                )
            return BufferPostResult(
                post_id=str(delete_post.get("id") or schedule.buffer_post_id),
                status=BufferPostStatus.CANCELLED,
                raw_response=delete_post,
            )
        except BufferRateLimitError as exc:
            return self._rate_limited_result(schedule, exc)
        except RuntimeError as exc:
            return BufferPostResult(
                post_id=schedule.buffer_post_id,
                status=BufferPostStatus.FAILED,
                failure_reason=str(exc),
                raw_response={"error": str(exc)},
            )

    def _live_sync_result(
        self,
        account: BufferAccount,
        schedule: EpisodeVideoPlatformSchedule,
    ) -> BufferPostResult:
        if not schedule.buffer_post_id:
            return BufferPostResult(
                post_id=self._fallback_post_id(schedule.id.hex),
                status=BufferPostStatus.FAILED,
                failure_reason="Buffer post ID is missing.",
                raw_response={"missing_post_id": True},
            )
        try:
            data = self.graphql.request(
                str(account.access_token_secret),
                """
                query GetPost($input: PostInput!) {
                  post(input: $input) {
                    id
                    status
                    dueAt
                    sentAt
                    externalLink
                    error { message }
                  }
                }
                """,
                {
                    "input": {
                        "id": schedule.buffer_post_id,
                        "organizationId": account.organization_id or "",
                    }
                },
            )
            account.rate_limit = data.get("_rate_limit") or {}
            post = data.get("data", {}).get("post")
            if not isinstance(post, dict) or not post:
                return BufferPostResult(
                    post_id=schedule.buffer_post_id,
                    status=BufferPostStatus.FAILED,
                    failure_reason=(
                        "Buffer did not return this queued post. It may have been deleted, "
                        "unavailable, or published outside the connected workspace."
                    ),
                    raw_response={"post": post},
                )
            error = post.get("error") or {}
            return BufferPostResult(
                post_id=str(post.get("id") or schedule.buffer_post_id),
                status=self._post_status(str(post.get("status") or "scheduled")),
                failure_reason=str(error.get("message")) if error.get("message") else None,
                live_url=str(post.get("externalLink")) if post.get("externalLink") else None,
                raw_response=post,
            )
        except BufferRateLimitError as exc:
            return self._rate_limited_result(schedule, exc)
        except RuntimeError as exc:
            return BufferPostResult(
                post_id=schedule.buffer_post_id,
                status=BufferPostStatus.FAILED,
                failure_reason=str(exc),
                raw_response={"error": str(exc)},
            )

    async def _fetch_live_channels(self, account: BufferAccount) -> list[BufferChannel]:
        data = self.graphql.request(
            str(account.access_token_secret),
            """
            query GetChannels($organizationId: String!) {
              channels(input: { organizationId: $organizationId }) {
                id
                name
                displayName
                service
                avatar
                isQueuePaused
              }
            }
            """,
            {"organizationId": account.organization_id or ""},
        )
        account.rate_limit = data.get("_rate_limit") or {}
        channels = data.get("data", {}).get("channels") or []
        return await self._upsert_channels(account, channels)

    def _refresh_account_context(self, account: BufferAccount) -> None:
        data = self.graphql.request(
            str(account.access_token_secret),
            """
            query CurrentBufferAccount {
              account {
                id
                name
                email
                organizations { id name }
              }
            }
            """,
            {},
        )
        account.rate_limit = data.get("_rate_limit") or {}
        payload = data.get("data", {}).get("account", {})
        if not isinstance(payload, dict):
            raise RuntimeError("Buffer account lookup returned an unexpected response.")
        organizations = payload.get("organizations") or []
        organization = organizations[0] if isinstance(organizations, list) and organizations else {}
        if not isinstance(organization, dict):
            organization = {}
        account.buffer_account_id = str(payload.get("id") or account.buffer_account_id or "")
        account.name = str(payload.get("name") or payload.get("email") or account.name)
        account.organization_id = str(organization.get("id") or account.organization_id or "")

    async def _upsert_development_channels(self, account: BufferAccount) -> list[BufferChannel]:
        channels = [
            {
                "id": "dev-linkedin",
                "name": "PodoBot LinkedIn",
                "displayName": "PodoBot LinkedIn",
                "service": "linkedin",
                "avatar": None,
                "isQueuePaused": False,
            },
            {
                "id": "dev-facebook",
                "name": "PodoBot Facebook",
                "displayName": "PodoBot Facebook",
                "service": "facebook",
                "avatar": None,
                "isQueuePaused": False,
            },
            {
                "id": "dev-youtube",
                "name": "PodoBot YouTube",
                "displayName": "PodoBot YouTube",
                "service": "youtube",
                "avatar": None,
                "isQueuePaused": False,
            },
            {
                "id": "dev-instagram",
                "name": "PodoBot Instagram",
                "displayName": "PodoBot Instagram",
                "service": "instagram",
                "avatar": None,
                "isQueuePaused": False,
            },
            {
                "id": "dev-tiktok",
                "name": "PodoBot TikTok",
                "displayName": "PodoBot TikTok",
                "service": "tiktok",
                "avatar": None,
                "isQueuePaused": False,
            },
            {
                "id": "dev-x",
                "name": "PodoBot X",
                "displayName": "PodoBot X",
                "service": "x",
                "avatar": None,
                "isQueuePaused": False,
            },
        ]
        return await self._upsert_channels(account, channels)

    async def _upsert_channels(
        self,
        account: BufferAccount,
        channels: list[dict[str, object]],
    ) -> list[BufferChannel]:
        now = datetime.now(UTC)
        existing = {
            channel.buffer_channel_id: channel for channel in await self._channels(account.id)
        }
        upserted = []
        for payload in channels:
            channel_id = str(payload["id"])
            channel = existing.get(channel_id)
            if channel is None:
                channel = BufferChannel(
                    buffer_account_id=account.id,
                    buffer_channel_id=channel_id,
                    service=str(payload.get("service") or "").lower(),
                    name=str(payload.get("name") or payload.get("displayName") or channel_id),
                    display_name=str(
                        payload.get("displayName") or payload.get("name") or channel_id
                    ),
                    avatar_url=payload.get("avatar"),  # type: ignore[arg-type]
                    is_queue_paused=bool(payload.get("isQueuePaused") or False),
                    raw_payload=payload,
                    last_synced_at=now,
                )
                self.session.add(channel)
            else:
                channel.service = str(payload.get("service") or channel.service).lower()
                channel.name = str(payload.get("name") or channel.name)
                channel.display_name = str(payload.get("displayName") or channel.display_name)
                channel.avatar_url = payload.get("avatar")  # type: ignore[assignment]
                channel.is_queue_paused = bool(payload.get("isQueuePaused") or False)
                channel.raw_payload = payload
                channel.last_synced_at = now
            upserted.append(channel)
        await self.session.flush()
        return upserted

    async def _ensure_default_mappings(self, channels: list[BufferChannel]) -> None:
        existing = {mapping.platform for mapping in await self._mappings()}
        for platform in Platform:
            if platform in existing:
                continue
            match = next(
                (
                    channel
                    for channel in channels
                    if self._channel_matches_platform(platform, channel)
                ),
                None,
            )
            if match is not None:
                self.session.add(
                    BufferChannelMapping(platform=platform, buffer_channel_id=match.id)
                )

    async def _publishing_target(self, platform: Platform) -> tuple[BufferAccount, BufferChannel]:
        account = await self._require_connected_account()
        result = await self.session.execute(
            select(BufferChannelMapping).where(
                BufferChannelMapping.platform == platform,
                BufferChannelMapping.is_active.is_(True),
            )
        )
        mapping = result.scalar_one_or_none()
        if mapping is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Map a Buffer channel for {platform.value} before scheduling.",
            )
        channel = await self.session.get(BufferChannel, mapping.buffer_channel_id)
        if channel is None or channel.buffer_account_id != account.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Mapped Buffer channel for {platform.value} is unavailable.",
            )
        self._validate_channel_mapping(platform, channel)
        return account, channel

    async def _schedule_target(
        self,
        schedule: EpisodeVideoPlatformSchedule,
    ) -> tuple[BufferAccount | None, BufferChannel | None]:
        account = (
            await self.session.get(BufferAccount, schedule.buffer_account_id)
            if schedule.buffer_account_id
            else await self._active_account()
        )
        channel = (
            await self.session.get(BufferChannel, schedule.buffer_channel_id)
            if schedule.buffer_channel_id
            else None
        )
        return account, channel

    def _validate_channel_mapping(self, platform: Platform, channel: BufferChannel) -> None:
        if not self._channel_matches_platform(platform, channel):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"{channel.display_name} is not a valid Buffer channel for {platform.value}."
                ),
            )
        if not channel.is_enabled:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{channel.display_name} is disabled in Buffer.",
            )

    def _channel_matches_platform(self, platform: Platform, channel: BufferChannel) -> bool:
        return channel.service.lower() in PLATFORM_SERVICE_ALIASES[platform]

    async def _ensure_buffer_integration(self) -> Integration:
        result = await self.session.execute(
            select(Integration).where(Integration.type == IntegrationType.BUFFER)
        )
        integration = result.scalar_one_or_none()
        if integration is None:
            integration = Integration(
                type=IntegrationType.BUFFER,
                name="Buffer",
                description="Publishing connection used by scheduling.",
                is_enabled=True,
                is_critical=True,
                status=IntegrationStatus.HEALTHY,
                settings={},
                quota={"status": "unknown"},
            )
            self.session.add(integration)
            await self.session.flush()
        if integration.status != IntegrationStatus.HEALTHY:
            integration.status = IntegrationStatus.HEALTHY
            integration.failure_reason = None
        return integration

    async def _ensure_account(self, integration: Integration) -> BufferAccount:
        account = await self._active_account(include_pending=True)
        if account is not None:
            account.integration_id = integration.id
            return account
        account = BufferAccount(
            integration_id=integration.id,
            name="Buffer account",
            status=BufferAccountStatus.DISCONNECTED,
            scopes=[],
            rate_limit={},
        )
        self.session.add(account)
        await self.session.flush()
        return account

    async def _active_account(self, include_pending: bool = False) -> BufferAccount | None:
        statuses = [BufferAccountStatus.CONNECTED]
        if include_pending:
            statuses.extend([BufferAccountStatus.OAUTH_PENDING, BufferAccountStatus.DISCONNECTED])
        result = await self.session.execute(
            select(BufferAccount)
            .where(BufferAccount.status.in_(statuses))
            .order_by(BufferAccount.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _require_connected_account(self) -> BufferAccount:
        account = await self._active_account()
        if account is None:
            await self.start_oauth()
            account = await self._active_account(include_pending=True)
            if account is not None and not settings.buffer_client_id:
                await self._connect_development_account(account)
                await self.session.flush()
                return account
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Connect Buffer before scheduling posts.",
            )
        if not self._is_development_account(account) and self._token_needs_refresh(account):
            await self._refresh_access_token(account)
        return account

    async def _pending_oauth_account(self, state: str) -> BufferAccount:
        result = await self.session.execute(
            select(BufferAccount).where(BufferAccount.oauth_state == state)
        )
        account = result.scalar_one_or_none()
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OAuth state.",
            )
        return account

    async def _connect_development_account(self, account: BufferAccount) -> None:
        now = datetime.now(UTC)
        account.status = BufferAccountStatus.CONNECTED
        account.buffer_account_id = account.buffer_account_id or "dev-buffer-account"
        account.organization_id = account.organization_id or "dev-buffer-organization"
        account.name = "PodoBot Buffer"
        account.access_token_secret = account.access_token_secret or "dev-buffer-access-token"
        account.refresh_token_secret = account.refresh_token_secret or "dev-buffer-refresh-token"
        account.scopes = BUFFER_SCOPES
        account.connected_at = account.connected_at or now
        account.oauth_state = None
        account.pkce_verifier = None
        channels = await self._upsert_development_channels(account)
        await self._ensure_default_mappings(channels)

    async def _exchange_oauth_code(
        self,
        account: BufferAccount,
        code: str,
    ) -> dict[str, object]:
        payload = {
            "grant_type": "authorization_code",
            "client_id": settings.buffer_client_id,
            "redirect_uri": settings.buffer_redirect_uri,
            "code": code,
            "code_verifier": account.pkce_verifier,
        }
        if settings.buffer_client_secret:
            payload["client_secret"] = settings.buffer_client_secret
        body = urllib.parse.urlencode(payload).encode("utf-8")
        request = urllib.request.Request(
            settings.buffer_token_url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=settings.buffer_request_timeout_seconds,
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Buffer OAuth token exchange failed.",
            ) from exc

    async def _refresh_access_token(self, account: BufferAccount) -> None:
        if not account.refresh_token_secret:
            account.status = BufferAccountStatus.EXPIRED
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Reconnect Buffer; the access token expired.",
            )
        payload = {
            "grant_type": "refresh_token",
            "client_id": settings.buffer_client_id,
            "refresh_token": account.refresh_token_secret,
        }
        if settings.buffer_client_secret:
            payload["client_secret"] = settings.buffer_client_secret
        body = urllib.parse.urlencode(payload).encode("utf-8")
        request = urllib.request.Request(
            settings.buffer_token_url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=settings.buffer_request_timeout_seconds,
            ) as response:
                token_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            account.status = BufferAccountStatus.EXPIRED
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Buffer OAuth token refresh failed.",
            ) from exc

        account.access_token_secret = str(token_payload["access_token"])
        if token_payload.get("refresh_token") is not None:
            account.refresh_token_secret = str(token_payload["refresh_token"])
        account.token_expires_at = datetime.now(UTC) + timedelta(
            seconds=int(token_payload.get("expires_in") or 3600)
        )
        if token_payload.get("scope") is not None:
            account.scopes = str(token_payload["scope"]).split()
        account.status = BufferAccountStatus.CONNECTED

    def _token_needs_refresh(self, account: BufferAccount) -> bool:
        if account.token_expires_at is None:
            return False
        return account.token_expires_at <= datetime.now(UTC) + timedelta(minutes=5)

    async def _channels(self, account_id: UUID) -> list[BufferChannel]:
        result = await self.session.execute(
            select(BufferChannel)
            .where(BufferChannel.buffer_account_id == account_id)
            .order_by(BufferChannel.service.asc(), BufferChannel.display_name.asc())
        )
        return list(result.scalars().all())

    async def _mappings(self) -> list[BufferChannelMapping]:
        result = await self.session.execute(
            select(BufferChannelMapping).order_by(BufferChannelMapping.platform.asc())
        )
        return list(result.scalars().all())

    async def _schedule_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> EpisodeVideoPlatformSchedule | None:
        result = await self.session.execute(
            select(EpisodeVideoPlatformSchedule).where(
                EpisodeVideoPlatformSchedule.idempotency_key == idempotency_key
            )
        )
        return result.scalar_one_or_none()

    async def _schedule_by_buffer_post_id(
        self,
        post_id: str | None,
    ) -> EpisodeVideoPlatformSchedule | None:
        if not post_id:
            return None
        result = await self.session.execute(
            select(EpisodeVideoPlatformSchedule).where(
                EpisodeVideoPlatformSchedule.buffer_post_id == post_id
            )
        )
        return result.scalar_one_or_none()

    async def _recent_audit_logs(
        self,
        schedule_id: UUID | None = None,
        limit: int = 12,
    ) -> list[PublishingAuditLog]:
        statement = (
            select(PublishingAuditLog).order_by(PublishingAuditLog.created_at.desc()).limit(limit)
        )
        if schedule_id is not None:
            statement = statement.where(PublishingAuditLog.schedule_id == schedule_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def _recent_webhooks(self, limit: int = 12) -> list[BufferWebhook]:
        result = await self.session.execute(
            select(BufferWebhook).order_by(BufferWebhook.received_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def schedule_context(
        self,
        schedules: list[EpisodeVideoPlatformSchedule],
    ) -> dict[str, dict[UUID, object]]:
        channel_ids = {
            schedule.buffer_channel_id for schedule in schedules if schedule.buffer_channel_id
        }
        channels = []
        if channel_ids:
            result = await self.session.execute(
                select(BufferChannel).where(BufferChannel.id.in_(channel_ids))
            )
            channels = list(result.scalars().all())
        audits_by_schedule: dict[UUID, list[PublishingAuditLog]] = {}
        schedule_ids = {schedule.id for schedule in schedules}
        if schedule_ids:
            result = await self.session.execute(
                select(PublishingAuditLog)
                .where(PublishingAuditLog.schedule_id.in_(schedule_ids))
                .order_by(PublishingAuditLog.created_at.desc())
            )
            for audit in result.scalars().all():
                audits_by_schedule.setdefault(audit.schedule_id, []).append(audit)  # type: ignore[arg-type]
        return {
            "channels": {channel.id: channel for channel in channels},
            "audits": audits_by_schedule,
        }

    def schedule_payload(
        self,
        schedule: EpisodeVideoPlatformSchedule,
        context: dict[str, dict[UUID, object]],
    ) -> dict[str, object]:
        payload = {
            column.name: getattr(schedule, column.key) for column in schedule.__table__.columns
        }
        payload["channel"] = (
            context["channels"].get(schedule.buffer_channel_id)
            if schedule.buffer_channel_id
            else None
        )
        payload["audit_logs"] = context["audits"].get(schedule.id, [])
        return payload

    def idempotency_key(
        self,
        caption: EpisodeVideoPlatformCaption,
        scheduled_for: datetime,
        text: str,
    ) -> str:
        raw = "|".join(
            [
                str(caption.id),
                caption.platform.value,
                scheduled_for.isoformat(),
                hashlib.sha256(text.encode("utf-8")).hexdigest(),
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _mapping_payload(
        self,
        mapping: BufferChannelMapping,
        channels: list[BufferChannel],
    ) -> dict[str, object]:
        channel_by_id = {channel.id: channel for channel in channels}
        return {
            "id": mapping.id,
            "platform": mapping.platform,
            "buffer_channel_id": mapping.buffer_channel_id,
            "is_active": mapping.is_active,
            "channel": channel_by_id.get(mapping.buffer_channel_id),
            "created_at": mapping.created_at,
            "updated_at": mapping.updated_at,
        }

    def _workspace_warnings(
        self,
        account: BufferAccount | None,
        channels: list[BufferChannel],
        mappings: list[BufferChannelMapping],
    ) -> list[str]:
        warnings = []
        if account is None or account.status != BufferAccountStatus.CONNECTED:
            warnings.append("Buffer is required before publishing schedules.")
        if account is not None and self._is_development_account(account):
            warnings.append(
                "Buffer is connected in development mode. Queued posts are simulated and will "
                "not publish to social channels until real Buffer OAuth credentials are "
                "configured and connected."
            )
        if account is not None and not channels:
            warnings.append("Sync Buffer channels before scheduling production posts.")
        mapped_platforms = {mapping.platform for mapping in mappings if mapping.is_active}
        for platform in Platform:
            if platform not in mapped_platforms:
                warnings.append(f"Map a Buffer channel for {platform.value}.")
        return warnings

    def _post_payload(
        self,
        channel: BufferChannel,
        scheduled_for: datetime,
        text: str,
    ) -> dict[str, object]:
        return {
            "text": text,
            "channelId": channel.buffer_channel_id,
            "schedulingType": "automatic",
            "mode": "customScheduled",
            "dueAt": scheduled_for.astimezone(UTC).isoformat(),
        }

    def _post_action_result(
        self,
        key: str,
        data: dict[str, object],
        *,
        fallback_id: str,
    ) -> BufferPostResult:
        action = data.get("data", {}).get(key, {})  # type: ignore[union-attr]
        if not isinstance(action, dict):
            return BufferPostResult(
                post_id=fallback_id,
                status=BufferPostStatus.FAILED,
                failure_reason="Buffer returned an unexpected response.",
                raw_response={"response": action},
            )
        if action.get("message"):
            return BufferPostResult(
                post_id=fallback_id,
                status=BufferPostStatus.FAILED,
                failure_reason=str(action["message"]),
                raw_response=action,
            )
        post = action.get("post") or {}
        if not isinstance(post, dict):
            post = {}
        return BufferPostResult(
            post_id=str(post.get("id") or fallback_id),
            status=self._post_status(str(post.get("status") or "scheduled")),
            live_url=str(post.get("externalLink")) if post.get("externalLink") else None,
            raw_response=action,
        )

    def _rate_limited_result(
        self,
        schedule: EpisodeVideoPlatformSchedule,
        exc: BufferRateLimitError,
    ) -> BufferPostResult:
        return BufferPostResult(
            post_id=schedule.buffer_post_id or self._fallback_post_id(schedule.id.hex),
            status=BufferPostStatus.FAILED,
            failure_reason="Buffer rate limit exceeded; retry later.",
            retry_after_seconds=exc.retry_after_seconds,
            rate_limit=exc.rate_limit,
            raw_response={"rate_limit": exc.rate_limit},
        )

    def _post_status(self, value: str) -> BufferPostStatus:
        normalized = value.lower()
        if normalized in {"sent", "published"}:
            return BufferPostStatus.PUBLISHED
        if normalized in {"error", "failed"}:
            return BufferPostStatus.FAILED
        if normalized in {"cancelled", "canceled"}:
            return BufferPostStatus.CANCELLED
        return BufferPostStatus.QUEUED

    def _fail_overdue_queue(
        self,
        schedule: EpisodeVideoPlatformSchedule,
        result: BufferPostResult,
        now: datetime,
    ) -> BufferPostResult:
        if result.status != BufferPostStatus.QUEUED:
            return result
        if schedule.scheduled_for > now - timedelta(minutes=2):
            return result
        raw_response = result.raw_response or {}
        return BufferPostResult(
            post_id=result.post_id,
            status=BufferPostStatus.FAILED,
            failure_reason=(
                "Buffer still reports this post as queued after the scheduled publish time. "
                "Check the Buffer queue, then reschedule or sync again."
            ),
            live_url=result.live_url,
            rate_limit=result.rate_limit,
            retry_after_seconds=result.retry_after_seconds,
            raw_response={**raw_response, "overdue_queue": True},
        )

    def _result_from_webhook(
        self,
        schedule: EpisodeVideoPlatformSchedule,
        payload: dict[str, object],
    ) -> BufferPostResult:
        status_value = str(payload.get("status") or payload.get("post_status") or "scheduled")
        buffer_status = self._post_status(status_value)
        return BufferPostResult(
            post_id=schedule.buffer_post_id or str(payload.get("post_id") or ""),
            status=buffer_status,
            failure_reason=str(payload.get("message")) if payload.get("message") else None,
            live_url=str(payload.get("live_url")) if payload.get("live_url") else None,
            raw_response=payload,
        )

    def _audit(
        self,
        action: str,
        audit_status: PublishingAuditStatus,
        *,
        account: BufferAccount | None = None,
        channel: BufferChannel | None = None,
        schedule: EpisodeVideoPlatformSchedule | None = None,
        idempotency_key: str | None = None,
        request_payload: dict[str, object] | None = None,
        response_payload: dict[str, object] | None = None,
        error_message: str | None = None,
    ) -> None:
        self.session.add(
            PublishingAuditLog(
                schedule_id=schedule.id if schedule else None,
                buffer_account_id=account.id if account else None,
                buffer_channel_id=channel.id if channel else None,
                action=action,
                status=audit_status,
                idempotency_key=idempotency_key,
                request_payload=request_payload or {},
                response_payload=response_payload or {},
                error_message=error_message,
            )
        )

    def _audit_for_schedule(
        self,
        schedule: EpisodeVideoPlatformSchedule,
        action: str,
        audit_status: PublishingAuditStatus,
        *,
        request_payload: dict[str, object] | None = None,
        response_payload: dict[str, object] | None = None,
        error_message: str | None = None,
        account: BufferAccount | None = None,
        channel: BufferChannel | None = None,
    ) -> None:
        self._audit(
            action,
            audit_status,
            account=account,
            channel=channel,
            schedule=schedule,
            idempotency_key=schedule.idempotency_key,
            request_payload=request_payload,
            response_payload=response_payload,
            error_message=error_message,
        )

    def _fallback_post_id(self, value: str) -> str:
        return f"buf_{value[:18]}"

    def _is_development_account(self, account: BufferAccount) -> bool:
        return str(account.access_token_secret or "").startswith("dev-buffer")

    def _code_challenge(self, verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    def _verify_webhook_signature(self, raw_body: bytes, signature: str | None) -> bool:
        if not signature:
            return settings.environment == "development"
        expected = hmac.new(
            settings.buffer_webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        normalized = signature.removeprefix("sha256=")
        return hmac.compare_digest(expected, normalized)

    def _rate_limit_reset_at(self, rate_limit: dict[str, object] | None) -> datetime | None:
        if not rate_limit:
            return None
        reset = rate_limit.get("reset")
        if not isinstance(reset, str) or not reset:
            return None
        try:
            return datetime.fromisoformat(reset.replace("Z", "+00:00"))
        except ValueError:
            return None
