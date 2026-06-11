import base64
import json
from dataclasses import dataclass
from datetime import datetime
from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 200


class OffsetPageResponse(BaseModel):
    total: int = 0
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    total_pages: int = 0
    has_next: bool = False
    has_previous: bool = False


class CursorPageResponse(BaseModel):
    page_size: int = DEFAULT_PAGE_SIZE
    next_cursor: str | None = None
    previous_cursor: str | None = None
    has_next: bool = False
    has_previous: bool = False


class PaginationFilters(BaseModel):
    search: str | None = Field(default=None, max_length=240)
    sort: str = Field(default="updated_at")


@dataclass(frozen=True)
class OffsetParams:
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(frozen=True)
class CursorToken:
    created_at: datetime
    id: UUID


def clamp_page_size(page_size: int, *, max_size: int = MAX_PAGE_SIZE) -> int:
    return max(1, min(page_size, max_size))


def offset_meta(*, total: int, page: int, page_size: int) -> dict[str, object]:
    page_size = clamp_page_size(page_size)
    total_pages = ceil(total / page_size) if total else 0
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1 and total_pages > 0,
    }


def cursor_meta(
    *,
    page_size: int,
    has_next: bool,
    next_cursor: str | None,
    previous_cursor: str | None = None,
) -> dict[str, object]:
    return {
        "page_size": clamp_page_size(page_size),
        "next_cursor": next_cursor,
        "previous_cursor": previous_cursor,
        "has_next": has_next,
        "has_previous": previous_cursor is not None,
    }


def encode_cursor(created_at: datetime, item_id: UUID) -> str:
    payload = {"created_at": created_at.isoformat(), "id": str(item_id)}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> CursorToken | None:
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        return CursorToken(
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            id=UUID(str(payload["id"])),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pagination cursor",
        ) from exc
