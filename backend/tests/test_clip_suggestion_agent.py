from uuid import uuid4

import pytest

from app.agents.clip_suggestions import ClipSuggestionAgent, EvidenceSignal
from app.agents.defaults import DEFAULT_AGENTS
from app.modules.episodes.models import Episode
from app.modules.narratives.models import Narrative
from app.modules.series.models import Series


class FakeClipProvider:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.prompt = ""

    async def generate_json(self, prompt: str) -> dict[str, object]:
        self.prompt = prompt
        return self.response


def _series() -> Series:
    return Series(
        name="Founder Signals",
        audience="Investors",
        description="Analyze startup trend signals for early investing conviction.",
    )


def _episode() -> Episode:
    return Episode(
        series_id=uuid4(),
        episode_number=1,
        title="The Signal Hunt",
        premise="Identify early signals before market consensus forms.",
    )


def _narrative() -> Narrative:
    return Narrative(
        series_id=uuid4(),
        title="Evidence to conviction",
        thesis="Investors need a repeatable path from evidence to thesis.",
        summary="A producer-led workflow for turning weak signals into narrative conviction.",
        confidence_score=82,
        supporting_signals=[{"title": "Source concentration", "confidence": 80}],
    )


def _evidence() -> list[EvidenceSignal]:
    return [
        EvidenceSignal(
            source_name="Exa",
            provider_type="exa",
            title="Founder-market fit signal",
            summary="Evidence that founder-market fit can precede product-market fit.",
            composite_score=84,
            confidence_level="Medium",
            trend_score=72,
            trend_available=True,
        )
    ]


@pytest.mark.asyncio
async def test_clip_suggestion_agent_uses_transcript_narrative_and_research_context() -> None:
    provider = FakeClipProvider(
        {
            "clips": [
                {
                    "slot_number": 1,
                    "title": "Opening signal",
                    "rationale": "Connects transcript moment to the selected evidence arc.",
                    "start_timecode": "00:00:10",
                    "end_timecode": "00:00:40",
                },
                {
                    "slot_number": 2,
                    "title": "Evidence quality",
                    "rationale": "Shows how the guest evaluates source quality.",
                    "start_timecode": "00:01:10",
                    "end_timecode": "00:01:40",
                },
                {
                    "slot_number": 3,
                    "title": "Trend signal",
                    "rationale": "Ties the clip to current trend evidence.",
                    "start_timecode": "00:02:10",
                    "end_timecode": "00:02:40",
                },
            ]
        }
    )
    agent = ClipSuggestionAgent(provider)

    suggestions = await agent.suggest(
        series=_series(),
        episode=_episode(),
        transcript_text=(
            "00:00:10 --> 00:00:40\n"
            "The first useful signal is usually small but repeatable."
        ),
        narrative=_narrative(),
        evidence_signals=_evidence(),
    )

    assert len(suggestions) == 3
    assert suggestions[0].title == "Opening signal"
    assert "Clip Suggestion Agent" in provider.prompt
    assert "research_and_trend_signals" in provider.prompt
    assert "Founder-market fit signal" in provider.prompt
    assert "Evidence to conviction" in provider.prompt


@pytest.mark.asyncio
async def test_clip_suggestion_agent_rejects_incomplete_provider_output() -> None:
    agent = ClipSuggestionAgent(FakeClipProvider({"clips": [{"slot_number": 1}]}))

    with pytest.raises(ValueError):
        await agent.suggest(
            series=_series(),
            episode=_episode(),
            transcript_text="00:00:10 --> 00:00:40\nUseful moment.",
            narrative=None,
            evidence_signals=[],
        )


def test_default_agent_registry_includes_clip_suggestion_agent() -> None:
    agents = {agent.key: agent for agent in DEFAULT_AGENTS}

    assert agents["clip_suggestion"].name == "Clip Suggestion Agent"
    assert agents["clip_suggestion"].required_permission == "recording.upload"
