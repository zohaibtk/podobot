from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import app.files.storage as storage_module
import app.security.passwords as password_module
from app.core.config import settings
from app.db.session import engine
from app.db.types import ResearchSourceProviderType
from app.files.storage import LocalStorage
from app.modules.research.scoring import ResearchScoringService


class AsyncBytesReader:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.offset = 0

    async def read(self, size: int = -1) -> bytes:
        if self.offset >= len(self.payload):
            return b""
        end = len(self.payload) if size < 0 else self.offset + size
        chunk = self.payload[self.offset : end]
        self.offset += len(chunk)
        return chunk


def test_database_engine_uses_tuned_pool_settings() -> None:
    pool = engine.sync_engine.pool

    assert pool.size() == settings.database_pool_size
    assert pool._max_overflow == settings.database_max_overflow
    assert pool._timeout == settings.database_pool_timeout_seconds
    assert pool._recycle == settings.database_pool_recycle_seconds


async def test_password_hashing_helpers_run_in_threadpool(monkeypatch) -> None:
    calls = []

    async def fake_to_thread(function, *args):
        calls.append((function, args))
        return function(*args)

    monkeypatch.setattr(password_module.asyncio, "to_thread", fake_to_thread)

    encoded = await password_module.hash_password_async("producer")
    verified = await password_module.verify_password_async("producer", encoded)

    assert calls[0][0] is password_module.hash_password
    assert calls[1][0] is password_module.verify_password
    assert verified is True


async def test_local_storage_offloads_chunk_writes_to_threadpool(tmp_path, monkeypatch) -> None:
    writes: list[bytes] = []

    async def fake_to_thread(function, *args):
        writes.append(args[0])
        return function(*args)

    monkeypatch.setattr(storage_module.asyncio, "to_thread", fake_to_thread)
    local_storage = LocalStorage(str(tmp_path))

    stored = await local_storage.save_upload(
        "series/example/episode.mp4",
        AsyncBytesReader(b"video-bytes"),
        max_bytes=100,
        chunk_size=4,
    )

    assert stored.size_bytes == 11
    assert [len(chunk) for chunk in writes] == [4, 4, 3]
    assert local_storage.resolve(stored.relative_path).read_bytes() == b"video-bytes"


class FakePairsResult:
    def __init__(self, documents: list[SimpleNamespace], source: SimpleNamespace) -> None:
        self.documents = documents
        self.source = source

    def all(self):
        return [(document, self.source) for document in self.documents]


class FakeScalarResult:
    def __init__(self, documents: list[SimpleNamespace]) -> None:
        self.documents = documents

    def scalars(self):
        return self

    def all(self):
        return self.documents


class FakeScoringSession:
    def __init__(self, documents: list[SimpleNamespace], source: SimpleNamespace) -> None:
        self.documents = documents
        self.source = source
        self.execute_count = 0
        self.flush_count = 0
        self.commit_count = 0

    async def execute(self, _statement):
        self.execute_count += 1
        if self.execute_count == 1:
            return FakePairsResult(self.documents, self.source)
        return FakeScalarResult(self.documents)

    async def flush(self) -> None:
        self.flush_count += 1

    async def commit(self) -> None:
        self.commit_count += 1


def _document(run_id: UUID, title: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        research_run_id=run_id,
        title=title,
        provider_type=ResearchSourceProviderType.EXA,
        raw_metadata_json={"metadata": {"score": 0.8}},
        author="Research Desk",
        published_at=datetime.now(UTC),
        url="https://example.com/research",
        tier=None,
        tier_score=None,
        engagement_score=None,
        freshness_score=None,
        author_score=None,
        composite_score=None,
        trend_score=None,
        trend_available=None,
        trend_source=None,
        trend_failure_reason=None,
        confidence_level=None,
        score_explanation_json=None,
    )


async def test_score_run_documents_flushes_once_for_batch() -> None:
    run_id = uuid4()
    source = SimpleNamespace(
        provider_type=ResearchSourceProviderType.EXA,
        key="exa",
        name="Exa",
    )
    documents = [_document(run_id, "AI operations"), _document(run_id, "AI governance")]
    session = FakeScoringSession(documents, source)

    result = await ResearchScoringService(session).score_run_documents(run_id)

    assert result["success"] is True
    assert result["message"] == "Scored 2 research document(s)."
    assert session.flush_count == 1
    assert session.commit_count == 1
