from dataclasses import dataclass
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.db.types import (
    ClipSuggestionStatus,
)
from app.files.signed_urls import SignedURLService
from app.files.storage import EmptyUploadError, LocalStorage, UploadTooLargeError
from app.modules.episodes.models import Episode
from app.modules.recordings.media_services import (
    TranscriptParserService,
    UploadValidationRule,
    UploadValidationService,
)
from app.modules.recordings.models import ClipSuggestion
from app.modules.recordings.service import RecordingService


class AsyncBytesReader:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.offset = 0

    async def read(self, size: int = -1) -> bytes:
        if self.offset >= len(self.payload):
            return b""
        if size < 0:
            size = len(self.payload) - self.offset
        chunk = self.payload[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


@dataclass
class UploadStub:
    filename: str
    content_type: str


def test_upload_validation_rejects_unsupported_media_format() -> None:
    validator = UploadValidationService()
    rule = UploadValidationRule(
        asset_kind="video",
        allowed_content_types={"video/mp4"},
        allowed_extensions={".mp4"},
        max_bytes=100,
    )

    with pytest.raises(HTTPException) as exc_info:
        validator.validate(UploadStub("episode.exe", "application/octet-stream"), rule)  # type: ignore[arg-type]

    assert exc_info.value.status_code == 400
    assert "Unsupported video file type" in exc_info.value.detail


@pytest.mark.asyncio
async def test_local_storage_streams_upload_and_returns_checksum(tmp_path) -> None:
    local_storage = LocalStorage(str(tmp_path))

    stored = await local_storage.save_upload(
        "series/example/episode.mp4",
        AsyncBytesReader(b"video-bytes"),
        max_bytes=100,
        chunk_size=4,
    )

    assert stored.size_bytes == 11
    assert len(stored.checksum_sha256) == 64
    assert local_storage.resolve(stored.relative_path).read_bytes() == b"video-bytes"


@pytest.mark.asyncio
async def test_local_storage_rejects_empty_and_oversized_uploads(tmp_path) -> None:
    local_storage = LocalStorage(str(tmp_path))

    with pytest.raises(EmptyUploadError):
        await local_storage.save_upload(
            "series/example/empty.mp4",
            AsyncBytesReader(b""),
            max_bytes=100,
            chunk_size=4,
        )

    with pytest.raises(UploadTooLargeError):
        await local_storage.save_upload(
            "series/example/large.mp4",
            AsyncBytesReader(b"too-large"),
            max_bytes=3,
            chunk_size=4,
        )


def test_transcript_parser_extracts_srt_cues_and_duration() -> None:
    parser = TranscriptParserService()

    parsed = parser.parse(
        b"1\n00:00:01,000 --> 00:00:05,500\nOpening line\n\n"
        b"2\n00:00:07,000 --> 00:00:08,000\nSecond line\n",
        file_name="show.srt",
        content_type="application/x-subrip",
    )

    assert parsed["duration_seconds"] == 8
    assert parsed["transcript_cue_count"] == 2
    assert parsed["metadata"]["format"] == "srt"
    assert "Opening line" in parsed["metadata"]["text_preview"]


def test_transcript_parser_preview_keeps_enough_text_for_review_card() -> None:
    parser = TranscriptParserService()
    parsed = parser.parse(
        "\n".join(f"Preview sentence {index}." for index in range(1, 10)).encode(),
        file_name="show.txt",
        content_type="text/plain",
    )

    assert "Preview sentence 8." in str(parsed["metadata"]["text_preview"])
    assert "Preview sentence 9." not in str(parsed["metadata"]["text_preview"])


def test_clip_suggestion_payloads_are_generated_from_transcript_text() -> None:
    service = RecordingService(session=None)  # type: ignore[arg-type]
    episode = Episode(
        series_id=uuid4(),
        episode_number=1,
        title="Founder Signals",
        premise="A producer finds the strongest startup signals.",
    )

    payloads = service._clip_suggestion_payloads(
        episode,
        "WEBVTT\n\n"
        "00:00:10 --> 00:00:40\n"
        "Founders describe how weak signals become early conviction.\n\n"
        "00:01:10 --> 00:01:40\n"
        "Investors compare evidence quality before selecting a narrative.\n\n"
        "00:02:10 --> 00:02:40\n"
        "The producer explains how publication decisions become repeatable.\n",
    )

    assert len(payloads) == 3
    assert payloads[0]["slot_number"] == 1
    assert payloads[0]["start_timecode"] == "00:00:10"
    assert "Transcript-backed moment" in str(payloads[0]["rationale"])


def test_clip_media_progress_counts_suggested_clip_uploads() -> None:
    service = RecordingService(session=None)  # type: ignore[arg-type]
    series_id = uuid4()
    episode_id = uuid4()
    missing_clip = ClipSuggestion(
        series_id=series_id,
        episode_id=episode_id,
        slot_number=1,
        title="Opening hook",
        rationale="Good short-form moment.",
        start_timecode="00:00:10",
        end_timecode="00:00:40",
        status=ClipSuggestionStatus.SUGGESTED,
    )
    uploaded_clip = ClipSuggestion(
        series_id=series_id,
        episode_id=episode_id,
        slot_number=2,
        title="Middle hook",
        rationale="Another good short-form moment.",
        start_timecode="00:01:10",
        end_timecode="00:01:40",
        clip_file_path="series/example/short-clips/clip-2.mp4",
        status=ClipSuggestionStatus.SUGGESTED,
    )
    rejected_clip = ClipSuggestion(
        series_id=series_id,
        episode_id=episode_id,
        slot_number=3,
        title="Rejected hook",
        rationale="Not needed.",
        start_timecode="00:02:10",
        end_timecode="00:02:40",
        status=ClipSuggestionStatus.REJECTED,
    )

    assert service._clip_media_progress([missing_clip, uploaded_clip, rejected_clip]) == (
        2,
        1,
    )


def test_signed_url_service_rejects_expired_tokens() -> None:
    service = SignedURLService(secret="test-secret")
    signed = service.create("series/example/episode.mp4", expires_in_seconds=-1)
    token = signed.url.rsplit("/", 1)[-1]

    with pytest.raises(HTTPException) as exc_info:
        service.verify(token)

    assert exc_info.value.status_code == 403
    assert "expired" in exc_info.value.detail
