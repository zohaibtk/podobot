import pytest

from app.modules.series.schemas import SeriesCreateRequest
from app.modules.series.service import SeriesService


class FakeSession:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


class FakeRepository:
    def __init__(self) -> None:
        self.created = None

    async def create(self, payload):
        self.created = payload
        return {"name": payload.name}


def _payload() -> SeriesCreateRequest:
    return SeriesCreateRequest(
        name="AI Operators",
        audience="Technology executives",
        description="A focused series on executive AI operations.",
    )


@pytest.mark.anyio
async def test_series_create_persists_without_legacy_integration_gate() -> None:
    session = FakeSession()
    service = SeriesService(session)
    repository = FakeRepository()
    service.repository = repository

    result = await service.create_series(_payload())

    assert result["name"] == "AI Operators"
    assert repository.created is not None
    assert session.committed is True
