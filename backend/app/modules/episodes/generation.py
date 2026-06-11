import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from fastapi import HTTPException, status

from app.agents.llm.gemini import GeminiLLMProvider
from app.modules.episodes.models import Episode
from app.modules.narratives.models import Narrative
from app.modules.profiles.models import Profile
from app.modules.series.models import Series

MAX_REASONABLE_EPISODES = 50


class EpisodePlanProvider(Protocol):
    async def generate_json(self, prompt: str) -> dict[str, object]:
        ...


@dataclass(frozen=True)
class EpisodePlanDraft:
    title: str
    premise: str
    host_name: str | None = None
    guest_name: str | None = None


@dataclass(frozen=True)
class EpisodeProfileSuggestion:
    episode_number: int
    host_name: str
    guest_name: str


class LLMEpisodePlanGenerator:
    def __init__(self, provider: EpisodePlanProvider | None = None) -> None:
        self.provider = provider or GeminiLLMProvider()

    async def generate(
        self,
        series: Series,
        narrative: Narrative,
        *,
        host_profiles: list[Profile] | None = None,
        guest_profiles: list[Profile] | None = None,
    ) -> list[EpisodePlanDraft]:
        host_profiles = host_profiles or []
        guest_profiles = guest_profiles or []
        try:
            response = await self.provider.generate_json(
                self._prompt(series, narrative, host_profiles, guest_profiles)
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Episode plan generation failed: {exc}",
            ) from exc

        return self._validated_episode_plan(response, host_profiles, guest_profiles)

    async def suggest_profiles(
        self,
        series: Series,
        narrative: Narrative,
        episodes: list[Episode],
        *,
        host_profiles: list[Profile],
        guest_profiles: list[Profile],
    ) -> list[EpisodeProfileSuggestion]:
        if not episodes or not host_profiles or not guest_profiles:
            return []
        try:
            response = await self.provider.generate_json(
                self._profile_prompt(series, narrative, episodes, host_profiles, guest_profiles)
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Episode profile suggestion failed: {exc}",
            ) from exc

        return self._validated_profile_suggestions(
            response,
            episodes,
            host_profiles,
            guest_profiles,
        )

    async def generate_episode_draft(
        self,
        series: Series,
        narrative: Narrative,
        *,
        instruction: str,
        current_title: str | None = None,
        current_premise: str | None = None,
        episodes: list[Episode] | None = None,
    ) -> EpisodePlanDraft:
        try:
            response = await self.provider.generate_json(
                self._draft_prompt(
                    series,
                    narrative,
                    instruction=instruction,
                    current_title=current_title,
                    current_premise=current_premise,
                    episodes=episodes or [],
                )
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Episode draft generation failed: {exc}",
            ) from exc

        return self._validated_episode_draft(response)

    def _validated_episode_plan(
        self,
        response: dict[str, object],
        host_profiles: list[Profile],
        guest_profiles: list[Profile],
    ) -> list[EpisodePlanDraft]:
        raw_episodes = response.get("episodes")
        if not isinstance(raw_episodes, list) or not raw_episodes:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini did not return a usable episode plan.",
            )

        if len(raw_episodes) > MAX_REASONABLE_EPISODES:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini returned an unusually large episode plan. Please try again.",
            )

        drafts: list[EpisodePlanDraft] = []
        seen_titles: set[str] = set()
        host_names = {self._profile_key(profile.name): profile.name for profile in host_profiles}
        guest_names = {self._profile_key(profile.name): profile.name for profile in guest_profiles}
        for item in raw_episodes:
            if not isinstance(item, dict):
                continue
            title = self._clean_text(item.get("title"), max_length=220)
            premise = self._clean_text(item.get("premise"), max_length=2000)
            if not title or not premise:
                continue
            normalized_title = re.sub(r"\W+", "", title).lower()
            if normalized_title in seen_titles:
                continue
            seen_titles.add(normalized_title)
            host_name = self._matched_profile_name(item.get("host_name"), host_names)
            guest_name = self._matched_profile_name(item.get("guest_name"), guest_names)
            if host_names and not host_name:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Gemini episode plan did not include a valid host suggestion.",
                )
            if guest_names and not guest_name:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Gemini episode plan did not include a valid guest suggestion.",
                )
            drafts.append(
                EpisodePlanDraft(
                    title=title,
                    premise=premise,
                    host_name=host_name,
                    guest_name=guest_name,
                )
            )

        if not drafts:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini episode plan did not include valid episode titles and premises.",
            )
        return drafts

    def _prompt(
        self,
        series: Series,
        narrative: Narrative,
        host_profiles: list[Profile],
        guest_profiles: list[Profile],
    ) -> str:
        context = {
            "series": {
                "name": series.name,
                "audience": series.audience,
                "description": series.description,
            },
            "selected_narrative": {
                "title": narrative.title,
                "thesis": narrative.thesis,
                "summary": narrative.summary,
                "confidence_score": narrative.confidence_score,
                "supporting_signals": narrative.supporting_signals,
            },
            "available_host_profiles": [
                self._profile_payload(profile) for profile in host_profiles
            ],
            "available_guest_profiles": [
                self._profile_payload(profile) for profile in guest_profiles
            ],
        }
        return (
            "You are PodoBot's episode planning agent. Build an editorial episode plan "
            "for the selected podcast narrative.\n\n"
            "Important rules:\n"
            "- Decide the number of episodes yourself based on the narrative and evidence.\n"
            "- Do not target a preset episode count and do not pad the plan.\n"
            "- Each episode must advance the chosen narrative arc.\n"
            "- For every episode, choose one host_name from available_host_profiles.\n"
            "- For every episode, choose one guest_name from available_guest_profiles.\n"
            "- host_name and guest_name must use exact profile names from the provided lists.\n"
            "- Do not invent hosts or guests.\n"
            "- Use concrete, production-ready titles and premises.\n"
            "- Return JSON only with this exact shape: "
            '{"episodes":[{"title":"...","premise":"...","host_name":"...","guest_name":"..."}]}.\n\n'
            f"Context JSON:\n{json.dumps(context, default=self._json_default)}"
        )

    def _profile_prompt(
        self,
        series: Series,
        narrative: Narrative,
        episodes: list[Episode],
        host_profiles: list[Profile],
        guest_profiles: list[Profile],
    ) -> str:
        context = {
            "series": {
                "name": series.name,
                "audience": series.audience,
                "description": series.description,
            },
            "selected_narrative": {
                "title": narrative.title,
                "thesis": narrative.thesis,
                "summary": narrative.summary,
            },
            "episodes": [
                {
                    "episode_number": episode.episode_number,
                    "title": episode.title,
                    "premise": episode.premise,
                }
                for episode in episodes
            ],
            "available_host_profiles": [
                self._profile_payload(profile) for profile in host_profiles
            ],
            "available_guest_profiles": [
                self._profile_payload(profile) for profile in guest_profiles
            ],
        }
        return (
            "You are PodoBot's episode casting agent. Suggest one host and one guest "
            "profile for each existing episode.\n\n"
            "Important rules:\n"
            "- Keep the existing episode count and episode order unchanged.\n"
            "- For every episode, choose one host_name from available_host_profiles.\n"
            "- For every episode, choose one guest_name from available_guest_profiles.\n"
            "- host_name and guest_name must use exact profile names from the provided lists.\n"
            "- Do not invent hosts or guests.\n"
            "- Return JSON only with this exact shape: "
            '{"episodes":[{"episode_number":1,"host_name":"...","guest_name":"..."}]}.\n\n'
            f"Context JSON:\n{json.dumps(context, default=self._json_default)}"
        )

    def _draft_prompt(
        self,
        series: Series,
        narrative: Narrative,
        *,
        instruction: str,
        current_title: str | None,
        current_premise: str | None,
        episodes: list[Episode],
    ) -> str:
        context = {
            "series": {
                "name": series.name,
                "audience": series.audience,
                "description": series.description,
            },
            "selected_narrative": {
                "title": narrative.title,
                "thesis": narrative.thesis,
                "summary": narrative.summary,
            },
            "current_episode": {
                "title": current_title,
                "premise": current_premise,
            },
            "existing_episode_plan": [
                {
                    "episode_number": episode.episode_number,
                    "title": episode.title,
                    "premise": episode.premise,
                }
                for episode in episodes
            ],
            "producer_instruction": instruction,
        }
        return (
            "You are PodoBot's episode draft editor. Generate one podcast episode "
            "title and premise from the producer instruction.\n\n"
            "Important rules:\n"
            "- Return exactly one episode draft.\n"
            "- Preserve the selected narrative arc and avoid duplicating existing episode titles.\n"
            "- If current_episode has content, revise it according to producer_instruction.\n"
            "- If current_episode is empty, create a new episode that fits the plan.\n"
            "- The title must be concrete, production-ready, and at most 220 characters.\n"
            "- The premise must be concise, editorially specific, and explain the "
            "episode promise.\n"
            "- Return JSON only with this exact shape: "
            '{"title":"...","premise":"..."}.\n\n'
            f"Context JSON:\n{json.dumps(context, default=self._json_default)}"
        )

    def _validated_profile_suggestions(
        self,
        response: dict[str, object],
        episodes: list[Episode],
        host_profiles: list[Profile],
        guest_profiles: list[Profile],
    ) -> list[EpisodeProfileSuggestion]:
        raw_episodes = response.get("episodes")
        if not isinstance(raw_episodes, list) or not raw_episodes:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini did not return usable profile suggestions.",
            )

        episode_numbers = {episode.episode_number for episode in episodes}
        host_names = {self._profile_key(profile.name): profile.name for profile in host_profiles}
        guest_names = {self._profile_key(profile.name): profile.name for profile in guest_profiles}
        suggestions: list[EpisodeProfileSuggestion] = []
        seen_episode_numbers: set[int] = set()
        for item in raw_episodes:
            if not isinstance(item, dict):
                continue
            episode_number = self._int_value(item.get("episode_number"))
            if episode_number not in episode_numbers or episode_number in seen_episode_numbers:
                continue
            host_name = self._matched_profile_name(item.get("host_name"), host_names)
            guest_name = self._matched_profile_name(item.get("guest_name"), guest_names)
            if not host_name or not guest_name:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Gemini profile suggestions did not match the profile library.",
                )
            suggestions.append(
                EpisodeProfileSuggestion(
                    episode_number=episode_number,
                    host_name=host_name,
                    guest_name=guest_name,
                )
            )
            seen_episode_numbers.add(episode_number)

        if len(suggestions) != len(episode_numbers):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini did not suggest profiles for every episode.",
            )
        return suggestions

    def _validated_episode_draft(self, response: dict[str, object]) -> EpisodePlanDraft:
        title = self._clean_text(response.get("title"), max_length=220)
        premise = self._clean_text(response.get("premise"), max_length=2000)
        if not title or not premise:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini did not return a valid episode title and premise.",
            )
        return EpisodePlanDraft(title=title, premise=premise)

    def _clean_text(self, value: object, *, max_length: int) -> str:
        text = str(value or "").strip()
        text = re.sub(r"\s+", " ", text)
        return text[:max_length].strip()

    def _matched_profile_name(self, value: object, allowed_names: dict[str, str]) -> str | None:
        if not allowed_names:
            return None
        return allowed_names.get(self._profile_key(str(value or "")))

    def _profile_key(self, value: str) -> str:
        return re.sub(r"\s+", " ", value.strip()).casefold()

    def _profile_payload(self, profile: Profile) -> dict[str, object]:
        return {
            "name": profile.name,
            "role_title": profile.role_title,
            "archetype": profile.archetype,
            "bio": profile.bio,
        }

    def _int_value(self, value: object) -> int | None:
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return None

    def _json_default(self, value: Any) -> str:
        return str(value)
