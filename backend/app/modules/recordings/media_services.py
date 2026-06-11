import re
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


@dataclass(frozen=True)
class UploadValidationRule:
    asset_kind: str
    allowed_content_types: set[str]
    allowed_extensions: set[str]
    max_bytes: int


@dataclass(frozen=True)
class UploadValidationResult:
    file_name: str
    extension: str
    content_type: str
    max_bytes: int


class UploadValidationService:
    def validate(self, file: UploadFile, rule: UploadValidationRule) -> UploadValidationResult:
        file_name = self.safe_filename(file.filename)
        extension = Path(file_name).suffix.lower()
        content_type = file.content_type or "application/octet-stream"
        content_type_allowed = content_type in rule.allowed_content_types
        extension_allowed = extension in rule.allowed_extensions
        if not content_type_allowed and not extension_allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported {rule.asset_kind} file type",
            )

        return UploadValidationResult(
            file_name=file_name,
            extension=extension,
            content_type=content_type,
            max_bytes=rule.max_bytes,
        )

    def safe_filename(self, raw_filename: str | None) -> str:
        filename = Path(raw_filename or "upload").name.strip()
        filename = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip(".-")
        if not filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file name is required",
            )
        return filename[:180]


class TranscriptParserService:
    _timecode_pattern = re.compile(
        r"(?:(?P<hours>\d{1,2}):)?(?P<minutes>\d{2}):(?P<seconds>\d{2})"
        r"(?P<millis>[,.]\d{1,3})?"
    )

    def parse(self, content: bytes, *, file_name: str, content_type: str) -> dict[str, object]:
        text = content.decode("utf-8-sig", errors="replace")
        extension = Path(file_name).suffix.lower()
        timecodes = [self._seconds(match) for match in self._timecode_pattern.finditer(text)]
        cue_count = (
            text.count("-->")
            if extension in {".srt", ".vtt"}
            else len([line for line in text.splitlines() if line.strip()])
        )
        duration_seconds = int(max(timecodes)) if timecodes else None
        transcript_format = (
            "vtt" if extension == ".vtt" else "srt" if extension == ".srt" else "text"
        )
        return {
            "duration_seconds": duration_seconds,
            "transcript_cue_count": cue_count,
            "transcript_language": "und",
            "metadata": {
                "format": transcript_format,
                "content_type": content_type,
                "line_count": len(text.splitlines()),
                "text_preview": self._preview(text),
            },
        }

    def _seconds(self, match: re.Match[str]) -> float:
        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes"))
        seconds = int(match.group("seconds"))
        millis_raw = match.group("millis") or ""
        millis = float(f"0{millis_raw.replace(',', '.')}") if millis_raw else 0
        return hours * 3600 + minutes * 60 + seconds + millis

    def _preview(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip() and "-->" not in line]
        return " ".join(lines[:8])[:720]


class MediaMetadataExtractionService:
    def extract(
        self,
        *,
        file_name: str,
        content_type: str,
        file_size_bytes: int,
        checksum_sha256: str,
    ) -> dict[str, object]:
        extension = Path(file_name).suffix.lower().lstrip(".") or "unknown"
        return {
            "duration_seconds": None,
            "width": None,
            "height": None,
            "frame_rate": None,
            "codec": "unverified",
            "metadata": {
                "container": extension,
                "content_type": content_type,
                "file_size_bytes": file_size_bytes,
                "checksum_sha256": checksum_sha256,
                "extraction_mode": "server_side_manifest",
            },
        }


def upload_rule(
    asset_kind: str,
    content_types: set[str],
    extensions: set[str],
    max_bytes: int,
) -> UploadValidationRule:
    return UploadValidationRule(
        asset_kind=asset_kind,
        allowed_content_types=content_types,
        allowed_extensions=extensions,
        max_bytes=min(settings.max_upload_bytes, max_bytes),
    )
