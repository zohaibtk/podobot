import asyncio
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from app.core.config import settings


class StorageError(Exception):
    """Base class for storage-layer failures."""


class EmptyUploadError(StorageError):
    """Raised when an upload stream has no bytes."""


class UploadTooLargeError(StorageError):
    """Raised when an upload stream exceeds the configured limit."""


@dataclass(frozen=True)
class StoredObject:
    relative_path: str
    size_bytes: int
    checksum_sha256: str


class UploadReader(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


class StorageBackend(Protocol):
    def resolve(self, relative_path: str) -> Path: ...
    def ensure_parent(self, relative_path: str) -> Path: ...
    async def save_upload(
        self,
        relative_path: str,
        upload: UploadReader,
        *,
        max_bytes: int,
        chunk_size: int,
    ) -> StoredObject: ...
    def write_bytes(self, relative_path: str, payload: bytes) -> StoredObject: ...
    def delete(self, relative_path: str) -> None: ...


class LocalStorage:
    def __init__(self, root: str, fallback_roots: list[str] | None = None) -> None:
        self.root = Path(root).resolve()
        self.fallback_roots = [
            Path(fallback_root).resolve()
            for fallback_root in fallback_roots or []
            if Path(fallback_root).resolve() != self.root
        ]
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str) -> Path:
        normalized = self._normalize_relative_path(relative_path)
        candidate = self._candidate(self.root, normalized)
        if candidate.exists():
            return candidate
        for fallback_root in self.fallback_roots:
            fallback_candidate = self._candidate(fallback_root, normalized)
            if fallback_candidate.exists():
                return fallback_candidate
        return candidate

    def ensure_parent(self, relative_path: str) -> Path:
        destination = self.resolve(relative_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        return destination

    async def save_upload(
        self,
        relative_path: str,
        upload: UploadReader,
        *,
        max_bytes: int,
        chunk_size: int,
    ) -> StoredObject:
        destination = self.ensure_parent(relative_path)
        digest = sha256()
        bytes_written = 0
        try:
            with destination.open("wb") as output:
                while chunk := await upload.read(chunk_size):
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        output.close()
                        destination.unlink(missing_ok=True)
                        raise UploadTooLargeError
                    digest.update(chunk)
                    await asyncio.to_thread(output.write, chunk)
        except StorageError:
            raise
        except OSError as exc:
            destination.unlink(missing_ok=True)
            raise StorageError("Could not store upload") from exc

        if bytes_written == 0:
            destination.unlink(missing_ok=True)
            raise EmptyUploadError

        return StoredObject(
            relative_path=relative_path,
            size_bytes=bytes_written,
            checksum_sha256=digest.hexdigest(),
        )

    def write_bytes(self, relative_path: str, payload: bytes) -> StoredObject:
        destination = self.ensure_parent(relative_path)
        try:
            destination.write_bytes(payload)
        except OSError as exc:
            destination.unlink(missing_ok=True)
            raise StorageError("Could not store bytes") from exc

        return StoredObject(
            relative_path=relative_path,
            size_bytes=len(payload),
            checksum_sha256=sha256(payload).hexdigest(),
        )

    def delete(self, relative_path: str) -> None:
        self.resolve(relative_path).unlink(missing_ok=True)

    def _normalize_relative_path(self, relative_path: str) -> Path:
        if not relative_path or relative_path.strip() == "":
            raise ValueError("Path is required")

        path = Path(relative_path)
        if path.is_absolute():
            raise ValueError("Absolute paths are not allowed")

        if any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError("Unsafe relative path")

        return path

    def _candidate(self, root: Path, normalized: Path) -> Path:
        candidate = (root / normalized).resolve()
        if root not in candidate.parents and candidate != root:
            raise ValueError("Path escapes configured storage root")
        return candidate


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
storage = LocalStorage(
    settings.local_storage_root,
    fallback_roots=[str(REPOSITORY_ROOT / "backend/.local/storage")],
)
