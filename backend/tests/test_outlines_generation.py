from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.types import EpisodeOutlineStatus, SeriesStage
from app.modules.outlines.service import OutlineService


def _service() -> OutlineService:
    return OutlineService(cast(AsyncSession, object()))


def test_regenerated_outlines_vary_by_version_seed() -> None:
    service = _service()
    series = SimpleNamespace(audience="Enterprise operators")
    episode = SimpleNamespace(
        title="A New Standard of Excellence",
        premise="Celebrate a milestone and translate it into practical leadership takeaways.",
    )

    second_version = service._generated_outline_markdown(
        series,
        episode,
        regenerated=True,
        variant_seed=2,
    )
    third_version = service._generated_outline_markdown(
        series,
        episode,
        regenerated=True,
        variant_seed=3,
    )

    assert second_version != third_version
    assert "### Producer beat map" in second_version
    assert "### Argument flow" in third_version


def test_regenerated_outline_includes_producer_instruction() -> None:
    service = _service()
    series = SimpleNamespace(audience="Enterprise operators")
    episode = SimpleNamespace(
        title="A New Standard of Excellence",
        premise="Celebrate a milestone and translate it into practical leadership takeaways.",
    )

    outline = service._generated_outline_markdown(
        series,
        episode,
        regenerated=True,
        instruction="Make the evidence more specific and practical.",
        variant_seed=2,
    )

    assert "- Producer direction: Make the evidence more specific and practical." in outline


@pytest.mark.anyio
async def test_outline_gate_advances_series_to_briefs_when_all_outlines_are_approved() -> None:
    service = OutlineService(cast(AsyncSession, FakeOutlineSession()))
    series = SimpleNamespace(id=uuid4(), current_stage=SeriesStage.OUTLINES)

    async def outlines(_series_id):
        return [SimpleNamespace(status=EpisodeOutlineStatus.APPROVED)]

    service._outlines = outlines  # type: ignore[method-assign]

    await service._refresh_series_outline_gate(series)

    assert series.current_stage == SeriesStage.BRIEFS


@pytest.mark.anyio
async def test_outline_gate_returns_series_to_outlines_when_approval_is_invalidated() -> None:
    service = OutlineService(cast(AsyncSession, FakeOutlineSession()))
    series = SimpleNamespace(id=uuid4(), current_stage=SeriesStage.BRIEFS)

    async def outlines(_series_id):
        return [SimpleNamespace(status=EpisodeOutlineStatus.DRAFT)]

    service._outlines = outlines  # type: ignore[method-assign]

    await service._refresh_series_outline_gate(series)

    assert series.current_stage == SeriesStage.OUTLINES


class FakeOutlineSession:
    async def flush(self) -> None:
        return None
