from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm.database import DatabaseGeminiLLMProvider
from app.db.types import EpisodeStatus, ProfileKind, SeriesStage, SeriesStatus
from app.modules.episodes.generation import LLMEpisodePlanGenerator
from app.modules.episodes.models import Episode
from app.modules.episodes.schemas import (
    EpisodeAssignmentRequest,
    EpisodeCreateRequest,
    EpisodeDraftGenerationRequest,
    EpisodeReorderRequest,
    EpisodeUpdateRequest,
)
from app.modules.narratives.models import Narrative
from app.modules.outlines.models import EpisodeOutline
from app.modules.outlines.service import OutlineService
from app.modules.profiles.models import Profile
from app.modules.profiles.service import ProfileService
from app.modules.series.models import Series
from app.modules.series.service import SeriesService

RECORDED_OR_LATER_STATUSES = {
    EpisodeStatus.RECORDED,
    EpisodeStatus.CAPTIONING,
    EpisodeStatus.SCHEDULED,
    EpisodeStatus.PARTIALLY_PUBLISHED,
    EpisodeStatus.PUBLISHED,
}


class EpisodePlanService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.profile_service = ProfileService(session)
        self.series_service = SeriesService(session)
        self.outline_service = OutlineService(session)
        self.plan_generator = LLMEpisodePlanGenerator(DatabaseGeminiLLMProvider(session))

    async def get_plan(self, series_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        narrative = await self._selected_narrative(series_id)
        await self.ensure_generated_plan(series, narrative)

        await self.session.commit()
        return await self._workspace_response(series_id, narrative.id)

    async def ensure_generated_plan(
        self,
        series: Series,
        narrative: Narrative,
        *,
        replace_existing: bool = False,
    ) -> None:
        if series.plan_locked_at is not None:
            return
        episodes = await self._episodes(series.id)
        if episodes and not replace_existing:
            await self._suggest_profiles_for_uncurated_plan(series, narrative, episodes)
            return
        if episodes:
            has_recorded_episode = any(
                episode.status in RECORDED_OR_LATER_STATUSES for episode in episodes
            )
            if has_recorded_episode:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Recorded episodes cannot be replaced by narrative selection",
                )
            await self.session.execute(delete(Episode).where(Episode.series_id == series.id))
            await self.session.flush()

        host_profiles = await self.profile_service.list_profiles(kind=ProfileKind.HOST)
        guest_profiles = await self.profile_service.list_profiles(kind=ProfileKind.GUEST)
        drafts = await self.plan_generator.generate(
            series,
            narrative,
            host_profiles=host_profiles,
            guest_profiles=guest_profiles,
        )
        hosts_by_name = self._profiles_by_name(host_profiles)
        guests_by_name = self._profiles_by_name(guest_profiles)
        now = datetime.now(UTC)
        for index, draft in enumerate(drafts, start=1):
            host = self._profile_by_name(hosts_by_name, draft.host_name)
            guest = self._profile_by_name(guests_by_name, draft.guest_name)
            self.session.add(
                Episode(
                    series_id=series.id,
                    episode_number=index,
                    title=draft.title,
                    premise=draft.premise,
                    status=EpisodeStatus.PLANNED,
                    host_profile_id=host.id if host else None,
                    guest_profile_id=guest.id if guest else None,
                )
            )
        series.episode_plan_generated_at = now
        await self.session.flush()

    async def _suggest_profiles_for_uncurated_plan(
        self,
        series: Series,
        narrative: Narrative,
        episodes: list[Episode],
    ) -> None:
        if not episodes:
            return
        is_uncurated = all(
            episode.host_profile_id is None
            and episode.guest_profile_id is None
            and not episode.guest_name_override
            for episode in episodes
        )
        if not is_uncurated:
            return

        host_profiles = await self.profile_service.list_profiles(kind=ProfileKind.HOST)
        guest_profiles = await self.profile_service.list_profiles(kind=ProfileKind.GUEST)
        suggestions = await self.plan_generator.suggest_profiles(
            series,
            narrative,
            episodes,
            host_profiles=host_profiles,
            guest_profiles=guest_profiles,
        )
        hosts_by_name = self._profiles_by_name(host_profiles)
        guests_by_name = self._profiles_by_name(guest_profiles)
        suggestions_by_number = {
            suggestion.episode_number: suggestion for suggestion in suggestions
        }

        for episode in episodes:
            suggestion = suggestions_by_number.get(episode.episode_number)
            if suggestion is None:
                continue
            host = self._profile_by_name(hosts_by_name, suggestion.host_name)
            guest = self._profile_by_name(guests_by_name, suggestion.guest_name)
            episode.host_profile_id = host.id if host else None
            episode.guest_profile_id = guest.id if guest else None
        await self.session.flush()

    async def add_episode(
        self,
        series_id: UUID,
        payload: EpisodeCreateRequest,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        narrative = await self._selected_narrative(series_id)
        self._assert_plan_open(series)

        episode_count = await self._episode_count(series_id)
        self.session.add(
            Episode(
                series_id=series_id,
                episode_number=episode_count + 1,
                title=payload.title,
                premise=payload.premise,
            )
        )
        await self.session.commit()
        return await self._workspace_response(series_id, narrative.id)

    async def update_episode(
        self,
        series_id: UUID,
        episode_id: UUID,
        payload: EpisodeUpdateRequest,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        narrative = await self._selected_narrative(series_id)
        self._assert_plan_open(series)
        episode = await self._get_episode(series_id, episode_id)
        self._assert_episode_editable(episode)

        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(episode, field, value)

        await self.session.commit()
        return await self._workspace_response(series_id, narrative.id)

    async def generate_episode_draft(
        self,
        series_id: UUID,
        payload: EpisodeDraftGenerationRequest,
    ) -> dict[str, str]:
        series = await self.series_service.get_series(series_id)
        narrative = await self._selected_narrative(series_id)
        self._assert_plan_open(series)
        episode = (
            await self._get_episode(series_id, payload.episode_id)
            if payload.episode_id is not None
            else None
        )
        if episode is not None:
            self._assert_episode_editable(episode)

        current_title = payload.current_title or (episode.title if episode else None)
        current_premise = payload.current_premise or (episode.premise if episode else None)
        draft = await self.plan_generator.generate_episode_draft(
            series,
            narrative,
            instruction=payload.instruction,
            current_title=current_title,
            current_premise=current_premise,
            episodes=await self._episodes(series_id),
        )

        return {"title": draft.title, "premise": draft.premise}

    async def remove_episode(self, series_id: UUID, episode_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        narrative = await self._selected_narrative(series_id)
        self._assert_plan_open(series)
        episode = await self._get_episode(series_id, episode_id)
        self._assert_episode_editable(episode)

        await self.session.execute(delete(Episode).where(Episode.id == episode.id))
        await self._renumber_episodes(series_id)
        await self.session.commit()
        return await self._workspace_response(series_id, narrative.id)

    async def reorder_episodes(
        self,
        series_id: UUID,
        payload: EpisodeReorderRequest,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        narrative = await self._selected_narrative(series_id)
        self._assert_plan_open(series)
        episodes = await self._episodes(series_id)

        current_ids = [episode.id for episode in episodes]
        if set(payload.episode_ids) != set(current_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reorder payload must include every episode exactly once",
            )

        episode_by_id = {episode.id: episode for episode in episodes}
        has_recorded_episode = any(
            episode_by_id[episode_id].status in RECORDED_OR_LATER_STATUSES
            for episode_id in payload.episode_ids
        )
        if has_recorded_episode:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Recorded episodes cannot be reordered",
            )

        for index, episode in enumerate(episodes, start=1):
            episode.episode_number = 1000 + index
        await self.session.flush()

        for index, episode_id in enumerate(payload.episode_ids, start=1):
            episode_by_id[episode_id].episode_number = index

        await self.session.commit()
        return await self._workspace_response(series_id, narrative.id)

    async def assign_profiles(
        self,
        series_id: UUID,
        episode_id: UUID,
        payload: EpisodeAssignmentRequest,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        narrative = await self._selected_narrative(series_id)
        self._assert_plan_open(series)
        episode = await self._get_episode(series_id, episode_id)
        self._assert_episode_editable(episode)

        updates = payload.model_dump(exclude_unset=True)
        if "host_profile_id" in updates and updates["host_profile_id"] is not None:
            await self.profile_service.get_profile(updates["host_profile_id"], ProfileKind.HOST)
        if "guest_profile_id" in updates and updates["guest_profile_id"] is not None:
            await self.profile_service.get_profile(updates["guest_profile_id"], ProfileKind.GUEST)

        next_host_id = updates.get("host_profile_id", episode.host_profile_id)
        next_guest_id = updates.get("guest_profile_id", episode.guest_profile_id)
        if next_host_id is not None and next_host_id == next_guest_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Host and guest must be different profiles",
            )

        for field, value in updates.items():
            if field == "guest_name_override" and value == "":
                value = None
            setattr(episode, field, value)

        await self.session.commit()
        return await self._workspace_response(series_id, narrative.id)

    async def lock_plan(self, series_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        narrative = await self._selected_narrative(series_id)
        self._assert_plan_open(series)
        episodes = await self._episodes(series_id)
        if not episodes:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Plan has no episodes")

        workspace = await self._workspace_payload(series, episodes, narrative.id)
        readiness = workspace["lock_readiness"]
        if not readiness["is_ready"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Every episode requires an effective host and guest before lock",
            )

        series.plan_locked_at = datetime.now(UTC)
        series.current_stage = SeriesStage.OUTLINES
        series.status = SeriesStatus.IN_PRODUCTION

        outline_episode_ids = {outline.episode_id for outline in await self._outlines(series_id)}
        for episode in episodes:
            if episode.status == EpisodeStatus.PLANNED:
                episode.status = EpisodeStatus.OUTLINED
            if episode.id not in outline_episode_ids:
                await self.outline_service.create_outline_for_episode(series, episode)

        await self.session.commit()
        return await self._workspace_response(series_id, narrative.id)

    async def _workspace_response(
        self,
        series_id: UUID,
        selected_narrative_id: UUID,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        await self.session.refresh(series)
        episodes = await self._episodes(series_id)
        return await self._workspace_payload(series, episodes, selected_narrative_id)

    async def _workspace_payload(
        self,
        series: Series,
        episodes: list[Episode],
        selected_narrative_id: UUID,
    ) -> dict[str, object]:
        outlines = await self._outlines(series.id)
        profile_ids = {
            profile_id
            for episode in episodes
            for profile_id in (episode.host_profile_id, episode.guest_profile_id)
            if profile_id is not None
        }
        profiles = await self._profile_map(profile_ids)
        episode_payloads = [
            self._episode_payload(series, episode, profiles) for episode in episodes
        ]
        missing_episode_ids = [
            episode["id"] for episode in episode_payloads if episode["missing_assignments"]
        ]

        return {
            "series": series,
            "episodes": episode_payloads,
            "outlines": outlines,
            "selected_narrative_id": selected_narrative_id,
            "is_locked": series.plan_locked_at is not None,
            "lock_readiness": {
                "is_ready": bool(episode_payloads) and not missing_episode_ids,
                "missing_episode_count": len(missing_episode_ids),
                "missing_episode_ids": missing_episode_ids,
                "warnings": self._readiness_warnings(episode_payloads),
            },
        }

    async def _selected_narrative(self, series_id: UUID) -> Narrative:
        result = await self.session.execute(
            select(Narrative).where(
                Narrative.series_id == series_id,
                Narrative.is_selected.is_(True),
            )
        )
        narrative = result.scalar_one_or_none()
        if narrative is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Select exactly one narrative before planning episodes",
            )
        return narrative

    async def _episodes(self, series_id: UUID) -> list[Episode]:
        result = await self.session.execute(
            select(Episode)
            .where(Episode.series_id == series_id)
            .order_by(Episode.episode_number.asc())
        )
        return list(result.scalars().all())

    async def _outlines(self, series_id: UUID) -> list[EpisodeOutline]:
        result = await self.session.execute(
            select(EpisodeOutline)
            .where(EpisodeOutline.series_id == series_id)
            .order_by(EpisodeOutline.created_at.asc())
        )
        return list(result.scalars().all())

    async def _profile_map(self, profile_ids: set[UUID]) -> dict[UUID, Profile]:
        if not profile_ids:
            return {}
        result = await self.session.execute(select(Profile).where(Profile.id.in_(profile_ids)))
        return {profile.id: profile for profile in result.scalars().all()}

    async def _episode_count(self, series_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Episode).where(Episode.series_id == series_id)
        )
        return int(result.scalar_one())

    async def _get_episode(self, series_id: UUID, episode_id: UUID) -> Episode:
        episode = await self.session.get(Episode, episode_id)
        if episode is None or episode.series_id != series_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found")
        return episode

    async def _renumber_episodes(self, series_id: UUID) -> None:
        episodes = await self._episodes(series_id)
        for index, episode in enumerate(episodes, start=1):
            episode.episode_number = index
        await self.session.flush()

    def _assert_plan_open(self, series: Series) -> None:
        if series.plan_locked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Locked plans are read-only",
            )

    def _assert_episode_editable(self, episode: Episode) -> None:
        if episode.status in RECORDED_OR_LATER_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Recorded episodes cannot be edited, removed, or reordered",
            )

    def _episode_payload(
        self,
        series: Series,
        episode: Episode,
        profiles: dict[UUID, Profile],
    ) -> dict[str, object]:
        host = profiles.get(episode.host_profile_id) if episode.host_profile_id else None
        guest = profiles.get(episode.guest_profile_id) if episode.guest_profile_id else None
        effective_host = host.name if host else None
        effective_guest = guest.name if guest else None
        missing = []
        if not effective_host:
            missing.append("host")
        if not effective_guest:
            missing.append("guest")

        return {
            "id": episode.id,
            "series_id": episode.series_id,
            "episode_number": episode.episode_number,
            "title": episode.title,
            "premise": episode.premise,
            "status": episode.status,
            "host_profile_id": episode.host_profile_id,
            "guest_profile_id": episode.guest_profile_id,
            "guest_name_override": episode.guest_name_override,
            "host_profile_name": host.name if host else None,
            "guest_profile_name": guest.name if guest else None,
            "effective_host_name": effective_host,
            "effective_guest_name": effective_guest,
            "can_edit": (
                episode.status not in RECORDED_OR_LATER_STATUSES and series.plan_locked_at is None
            ),
            "missing_assignments": missing,
            "created_at": episode.created_at,
            "updated_at": episode.updated_at,
        }

    def _readiness_warnings(self, episode_payloads: list[dict[str, object]]) -> list[str]:
        warnings = []
        missing_hosts = sum(
            "host" in episode["missing_assignments"] for episode in episode_payloads
        )
        missing_guests = sum(
            "guest" in episode["missing_assignments"] for episode in episode_payloads
        )
        if missing_hosts:
            warnings.append(f"{missing_hosts} episode(s) need a host profile")
        if missing_guests:
            warnings.append(f"{missing_guests} episode(s) need a guest profile")
        return warnings

    def _profiles_by_name(self, profiles: list[Profile]) -> dict[str, Profile]:
        return {self._profile_name_key(profile.name): profile for profile in profiles}

    def _profile_by_name(
        self,
        profiles_by_name: dict[str, Profile],
        name: str | None,
    ) -> Profile | None:
        if name is None:
            return None
        return profiles_by_name.get(self._profile_name_key(name))

    def _profile_name_key(self, name: str) -> str:
        return " ".join(name.strip().casefold().split())
