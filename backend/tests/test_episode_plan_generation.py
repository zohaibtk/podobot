from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.modules.episodes.generation import LLMEpisodePlanGenerator


class FakeEpisodePlanProvider:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.prompt = ""

    async def generate_json(self, prompt: str) -> dict[str, object]:
        self.prompt = prompt
        return self.response


def _series() -> SimpleNamespace:
    return SimpleNamespace(
        name="Founder Signal Lab",
        audience="seed-stage investors",
        description="A show about early market signals and founder psychology.",
        guest_name="Avery Stone",
    )


def _narrative() -> SimpleNamespace:
    return SimpleNamespace(
        title="Signals before consensus",
        thesis="Early-stage investors win by reading quiet signal patterns before markets agree.",
        summary="A narrative about combining research, field evidence, and founder behavior.",
        confidence_score=82,
        supporting_signals=[
            {
                "source_name": "Exa",
                "signal_title": "Signal-based investing is gaining traction",
                "confidence_score": 82,
            }
        ],
    )


def _profiles() -> tuple[list[SimpleNamespace], list[SimpleNamespace]]:
    return (
        [
            SimpleNamespace(
                name="Maya Chen",
                role_title="Executive Podcast Host",
                archetype="Calm operator",
                bio="Turns complex topics into crisp executive narratives.",
            )
        ],
        [
            SimpleNamespace(
                name="Avery Stone",
                role_title="AI Strategy Advisor",
                archetype="Market expert",
                bio="Brings evidence-based AI strategy perspective.",
            )
        ],
    )


def _episodes() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            episode_number=1,
            title="The signal map",
            premise="Define the weak signals investors should track.",
        ),
        SimpleNamespace(
            episode_number=2,
            title="Decision ritual",
            premise="Close with a repeatable review process.",
        ),
    ]


@pytest.mark.anyio
async def test_llm_episode_plan_uses_model_decided_episode_count() -> None:
    provider = FakeEpisodePlanProvider(
        {
            "episodes": [
                {
                    "title": "The signal map",
                    "premise": "Define the weak signals investors should track.",
                },
                {
                    "title": "Founder psychology under pressure",
                    "premise": "Explore behavioral patterns that reveal market readiness.",
                },
                {
                    "title": "From noise to conviction",
                    "premise": "Show how teams turn messy evidence into a thesis.",
                },
            ]
        }
    )

    drafts = await LLMEpisodePlanGenerator(provider).generate(_series(), _narrative())

    assert len(drafts) == 3
    assert drafts[0].title == "The signal map"
    assert "Do not target a preset episode count" in provider.prompt


@pytest.mark.anyio
async def test_llm_episode_plan_accepts_exact_profile_suggestions() -> None:
    hosts, guests = _profiles()
    provider = FakeEpisodePlanProvider(
        {
            "episodes": [
                {
                    "title": "The signal map",
                    "premise": "Define the weak signals investors should track.",
                    "host_name": "Maya Chen",
                    "guest_name": "Avery Stone",
                }
            ]
        }
    )

    drafts = await LLMEpisodePlanGenerator(provider).generate(
        _series(),
        _narrative(),
        host_profiles=hosts,
        guest_profiles=guests,
    )

    assert drafts[0].host_name == "Maya Chen"
    assert drafts[0].guest_name == "Avery Stone"
    assert "Do not invent hosts or guests" in provider.prompt


@pytest.mark.anyio
async def test_llm_episode_plan_rejects_invalid_profile_suggestion() -> None:
    hosts, guests = _profiles()
    provider = FakeEpisodePlanProvider(
        {
            "episodes": [
                {
                    "title": "The signal map",
                    "premise": "Define the weak signals investors should track.",
                    "host_name": "Invented Host",
                    "guest_name": "Avery Stone",
                }
            ]
        }
    )

    with pytest.raises(HTTPException) as exc:
        await LLMEpisodePlanGenerator(provider).generate(
            _series(),
            _narrative(),
            host_profiles=hosts,
            guest_profiles=guests,
        )

    assert exc.value.status_code == 502


@pytest.mark.anyio
async def test_llm_episode_profile_suggestions_require_every_episode() -> None:
    hosts, guests = _profiles()
    provider = FakeEpisodePlanProvider(
        {
            "episodes": [
                {"episode_number": 1, "host_name": "Maya Chen", "guest_name": "Avery Stone"},
                {"episode_number": 2, "host_name": "Maya Chen", "guest_name": "Avery Stone"},
            ]
        }
    )

    suggestions = await LLMEpisodePlanGenerator(provider).suggest_profiles(
        _series(),
        _narrative(),
        _episodes(),
        host_profiles=hosts,
        guest_profiles=guests,
    )

    assert [suggestion.episode_number for suggestion in suggestions] == [1, 2]
    assert suggestions[0].host_name == "Maya Chen"
    assert "Keep the existing episode count" in provider.prompt


@pytest.mark.anyio
async def test_llm_episode_draft_generation_uses_producer_instruction() -> None:
    provider = FakeEpisodePlanProvider(
        {
            "title": "The sharper signal map",
            "premise": "Reframe the episode around investor action and clearer market evidence.",
        }
    )

    draft = await LLMEpisodePlanGenerator(provider).generate_episode_draft(
        _series(),
        _narrative(),
        instruction="Make it more action-oriented for investors.",
        current_title="The signal map",
        current_premise="Define the weak signals investors should track.",
        episodes=_episodes(),
    )

    assert draft.title == "The sharper signal map"
    assert "producer_instruction" in provider.prompt
    assert "Return exactly one episode draft" in provider.prompt


@pytest.mark.anyio
async def test_llm_episode_plan_rejects_missing_episode_payload() -> None:
    provider = FakeEpisodePlanProvider({"summary": "No episodes today."})

    with pytest.raises(HTTPException) as exc:
        await LLMEpisodePlanGenerator(provider).generate(_series(), _narrative())

    assert exc.value.status_code == 502


@pytest.mark.anyio
async def test_llm_episode_draft_rejects_missing_title_or_premise() -> None:
    provider = FakeEpisodePlanProvider({"title": "Only a title"})

    with pytest.raises(HTTPException) as exc:
        await LLMEpisodePlanGenerator(provider).generate_episode_draft(
            _series(),
            _narrative(),
            instruction="Refresh this episode.",
        )

    assert exc.value.status_code == 502


@pytest.mark.anyio
async def test_llm_episode_plan_deduplicates_episode_titles() -> None:
    provider = FakeEpisodePlanProvider(
        {
            "episodes": [
                {"title": "Signal map", "premise": "Open the editorial arc."},
                {"title": "Signal map", "premise": "Duplicate item."},
                {"title": "Decision ritual", "premise": "Close with a repeatable review process."},
            ]
        }
    )

    drafts = await LLMEpisodePlanGenerator(provider).generate(_series(), _narrative())

    assert [draft.title for draft in drafts] == ["Signal map", "Decision ritual"]
