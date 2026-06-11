from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.workflow import record_workflow_agent_run
from app.db.types import (
    BriefKind,
    BriefStatus,
    BriefVersionSource,
    EpisodeOutlineStatus,
    EpisodeStatus,
    ProfileKind,
    SeriesStage,
    SeriesStatus,
)
from app.modules.briefs.models import BriefVersion, EpisodeBrief
from app.modules.briefs.schemas import BriefUpdateRequest
from app.modules.episodes.models import Episode
from app.modules.outlines.models import EpisodeOutline, OutlineVersion
from app.modules.profiles.models import Profile
from app.modules.series.models import Series
from app.modules.series.service import SeriesService

RECORDED_OR_LATER_STATUSES = {
    EpisodeStatus.RECORDED,
    EpisodeStatus.CAPTIONING,
    EpisodeStatus.SCHEDULED,
    EpisodeStatus.PARTIALLY_PUBLISHED,
    EpisodeStatus.PUBLISHED,
}


class BriefService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.series_service = SeriesService(session)

    async def get_workspace(self, series_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_plan_locked(series)
        return await self._workspace_response(series_id)

    async def generate_pair(self, series_id: UUID, episode_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_plan_locked(series)
        episode = await self._get_episode(series_id, episode_id)
        self._assert_briefs_editable(episode)
        context = await self._generation_context(series, episode)
        existing = await self._briefs_for_episode(series_id, episode.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Brief pair already exists. Regenerate an individual brief instead.",
            )

        await self._create_brief(
            series=series,
            episode=episode,
            kind=BriefKind.HOST,
            profile=context["host_profile"],
            counterpart=context["guest_profile"],
            outline=context["outline"],
            outline_version=context["outline_version"],
            source=BriefVersionSource.GENERATION,
        )
        await self._create_brief(
            series=series,
            episode=episode,
            kind=BriefKind.GUEST,
            profile=context["guest_profile"],
            counterpart=context["host_profile"],
            outline=context["outline"],
            outline_version=context["outline_version"],
            source=BriefVersionSource.GENERATION,
        )
        episode.status = EpisodeStatus.BRIEF_READY
        series.current_stage = SeriesStage.BRIEFS
        series.status = SeriesStatus.IN_PRODUCTION
        await self._refresh_series_brief_gate(series)
        await record_workflow_agent_run(
            self.session,
            agent_key="brief",
            entity_type="series",
            entity_id=series.id,
            workflow_stage=SeriesStage.BRIEFS.value,
            trigger="generation",
            input_payload={"episode_id": str(episode.id)},
            output_payload={
                "summary": "Generated host and guest brief pair.",
                "needs_approval": True,
            },
        )

        await self.session.commit()
        return await self._workspace_response(series_id)

    async def update_brief(
        self,
        series_id: UUID,
        brief_id: UUID,
        payload: BriefUpdateRequest,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_plan_locked(series)
        brief, episode = await self._get_brief_with_episode(series_id, brief_id)
        self._assert_briefs_editable(episode)
        current_version = await self._current_version(brief)
        if current_version is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Brief must have a current version before editing",
            )

        title = payload.title or brief.title
        version = await self._create_version(
            brief=brief,
            title=title,
            brief_markdown=payload.brief_markdown,
            outline_id=current_version.outline_id,
            outline_version_id=current_version.outline_version_id,
            source=BriefVersionSource.MANUAL_EDIT,
        )
        brief.title = title
        brief.brief_markdown = payload.brief_markdown
        brief.status = BriefStatus.DRAFT
        brief.current_version_id = version.id
        await self._invalidate_pair_approval(series, episode, edited_brief_id=brief.id)

        await self.session.commit()
        return await self._workspace_response(series_id)

    async def regenerate_brief(self, series_id: UUID, brief_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_plan_locked(series)
        brief, episode = await self._get_brief_with_episode(series_id, brief_id)
        self._assert_briefs_editable(episode)
        context = await self._generation_context(series, episode)

        profile = (
            context["host_profile"] if brief.kind == BriefKind.HOST else context["guest_profile"]
        )
        counterpart = (
            context["guest_profile"] if brief.kind == BriefKind.HOST else context["host_profile"]
        )
        title = self._brief_title(episode, profile, brief.kind, regenerated=True)
        brief_markdown = self._generated_brief_markdown(
            series=series,
            episode=episode,
            kind=brief.kind,
            profile=profile,
            counterpart=counterpart,
            outline_version=context["outline_version"],
            regenerated=True,
        )
        version = await self._create_version(
            brief=brief,
            title=title,
            brief_markdown=brief_markdown,
            outline_id=context["outline"].id,
            outline_version_id=context["outline_version"].id,
            source=BriefVersionSource.REGENERATION,
        )
        brief.title = title
        brief.brief_markdown = brief_markdown
        brief.status = BriefStatus.GENERATED
        brief.current_version_id = version.id
        await self._invalidate_pair_approval(series, episode)
        await record_workflow_agent_run(
            self.session,
            agent_key="brief",
            entity_type="series",
            entity_id=series.id,
            workflow_stage=SeriesStage.BRIEFS.value,
            trigger="regeneration",
            input_payload={"episode_id": str(episode.id), "brief_id": str(brief.id)},
            output_payload={
                "summary": f"Regenerated {brief.kind.value} brief version.",
                "needs_approval": True,
                "brief_version": version.version_number,
            },
        )

        await self.session.commit()
        return await self._workspace_response(series_id)

    async def approve_pair(self, series_id: UUID, episode_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_plan_locked(series)
        episode = await self._get_episode(series_id, episode_id)
        self._assert_briefs_editable(episode)
        briefs = await self._briefs_for_episode(series_id, episode.id)
        briefs_by_kind = {brief.kind: brief for brief in briefs}
        host_brief = briefs_by_kind.get(BriefKind.HOST)
        guest_brief = briefs_by_kind.get(BriefKind.GUEST)
        if host_brief is None or guest_brief is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Generate both host and guest briefs before approval",
            )
        if host_brief.current_version_id is None or guest_brief.current_version_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Both briefs need current versions before approval",
            )

        approved_at = datetime.now(UTC)
        for brief in (host_brief, guest_brief):
            brief.status = BriefStatus.APPROVED
            brief.approved_version_id = brief.current_version_id
            brief.approved_at = approved_at
            brief.approval_invalidated_at = None
        episode.status = EpisodeStatus.APPROVED
        await self._refresh_series_brief_gate(series, approved_at=approved_at)

        await self.session.commit()
        return await self._workspace_response(series_id)

    async def download_brief(self, series_id: UUID, brief_id: UUID) -> tuple[str, str]:
        _series = await self.series_service.get_series(series_id)
        brief, episode = await self._get_brief_with_episode(series_id, brief_id)
        filename = (
            f"episode-{episode.episode_number}-{brief.kind.value}-brief"
            f"-v{await self._latest_version_number(brief)}.md"
        )
        return filename, brief.brief_markdown

    async def _workspace_response(self, series_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        await self.session.refresh(series)
        episodes = await self._episodes(series_id)
        outlines = await self._outlines_by_episode(series_id)
        briefs = await self._briefs_by_episode(series_id)
        versions = await self._versions_by_brief(
            {brief.id for episode_briefs in briefs.values() for brief in episode_briefs}
        )
        profile_ids = {
            profile_id
            for episode in episodes
            for profile_id in (episode.host_profile_id, episode.guest_profile_id)
            if profile_id is not None
        }
        profiles = await self._profile_map(profile_ids)

        episode_payloads = [
            self._episode_payload(
                series=series,
                episode=episode,
                outline=outlines.get(episode.id),
                briefs=briefs.get(episode.id, []),
                versions_by_brief=versions,
                profiles=profiles,
            )
            for episode in episodes
        ]
        generated_count = sum(item["pair_generated"] for item in episode_payloads)
        approved_count = sum(item["pair_approved"] for item in episode_payloads)

        return {
            "series": series,
            "episodes": episode_payloads,
            "readiness": {
                "total_episode_count": len(episode_payloads),
                "generated_episode_count": generated_count,
                "approved_episode_count": approved_count,
                "recordings_unlocked": series.briefs_approved_at is not None,
                "warnings": self._readiness_warnings(
                    total_count=len(episode_payloads),
                    generated_count=generated_count,
                    approved_count=approved_count,
                ),
            },
        }

    async def _create_brief(
        self,
        series: Series,
        episode: Episode,
        kind: BriefKind,
        profile: Profile,
        counterpart: Profile,
        outline: EpisodeOutline,
        outline_version: OutlineVersion,
        source: BriefVersionSource,
    ) -> EpisodeBrief:
        title = self._brief_title(episode, profile, kind)
        brief_markdown = self._generated_brief_markdown(
            series=series,
            episode=episode,
            kind=kind,
            profile=profile,
            counterpart=counterpart,
            outline_version=outline_version,
        )
        brief = EpisodeBrief(
            series_id=series.id,
            episode_id=episode.id,
            kind=kind,
            title=title,
            brief_markdown=brief_markdown,
            status=BriefStatus.GENERATED,
        )
        self.session.add(brief)
        await self.session.flush()

        version = await self._create_version(
            brief=brief,
            title=title,
            brief_markdown=brief_markdown,
            outline_id=outline.id,
            outline_version_id=outline_version.id,
            source=source,
        )
        brief.current_version_id = version.id
        await self.session.flush()
        return brief

    async def _create_version(
        self,
        brief: EpisodeBrief,
        title: str,
        brief_markdown: str,
        outline_id: UUID,
        outline_version_id: UUID,
        source: BriefVersionSource,
    ) -> BriefVersion:
        result = await self.session.execute(
            select(func.coalesce(func.max(BriefVersion.version_number), 0)).where(
                BriefVersion.brief_id == brief.id
            )
        )
        version_number = int(result.scalar_one()) + 1
        version = BriefVersion(
            brief_id=brief.id,
            series_id=brief.series_id,
            episode_id=brief.episode_id,
            outline_id=outline_id,
            outline_version_id=outline_version_id,
            version_number=version_number,
            title=title,
            brief_markdown=brief_markdown,
            source=source,
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def _generation_context(
        self,
        series: Series,
        episode: Episode,
    ) -> dict[str, Profile | EpisodeOutline | OutlineVersion]:
        missing: list[str] = []
        host_profile = await self._assigned_profile(
            episode.host_profile_id,
            ProfileKind.HOST,
            "host profile",
            missing,
        )
        guest_profile = await self._assigned_profile(
            episode.guest_profile_id,
            ProfileKind.GUEST,
            "guest profile",
            missing,
        )
        outline, outline_version = await self._outline_context(episode.id, missing)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Brief generation blocked: {', '.join(missing)}",
            )
        if (
            host_profile is None
            or guest_profile is None
            or outline is None
            or outline_version is None
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Brief generation blocked by missing requirements",
            )
        return {
            "host_profile": host_profile,
            "guest_profile": guest_profile,
            "outline": outline,
            "outline_version": outline_version,
        }

    async def _assigned_profile(
        self,
        profile_id: UUID | None,
        expected_kind: ProfileKind,
        label: str,
        missing: list[str],
    ) -> Profile | None:
        if profile_id is None:
            missing.append(label)
            return None
        profile = await self.session.get(Profile, profile_id)
        if profile is None or not profile.is_active or profile.kind != expected_kind:
            missing.append(label)
            return None
        return profile

    async def _outline_context(
        self,
        episode_id: UUID,
        missing: list[str],
    ) -> tuple[EpisodeOutline | None, OutlineVersion | None]:
        result = await self.session.execute(
            select(EpisodeOutline).where(EpisodeOutline.episode_id == episode_id)
        )
        outline = result.scalar_one_or_none()
        if outline is None:
            missing.append("outline")
            return None, None
        if outline.current_version_id is None:
            missing.append("outline version")
            return outline, None
        if outline.status != EpisodeOutlineStatus.APPROVED:
            missing.append("outline approval")
            return outline, None
        outline_version = await self.session.get(OutlineVersion, outline.current_version_id)
        if outline_version is None:
            missing.append("outline version")
            return outline, None
        return outline, outline_version

    async def _invalidate_pair_approval(
        self,
        series: Series,
        episode: Episode,
        edited_brief_id: UUID | None = None,
    ) -> None:
        briefs = await self._briefs_for_episode(series.id, episode.id)
        invalidated_at = datetime.now(UTC)
        for brief in briefs:
            had_approval = (
                brief.status == BriefStatus.APPROVED
                or brief.approved_version_id is not None
                or brief.approved_at is not None
            )
            brief.approved_version_id = None
            brief.approved_at = None
            if had_approval:
                brief.approval_invalidated_at = invalidated_at
            if brief.id != edited_brief_id and brief.status == BriefStatus.APPROVED:
                brief.status = BriefStatus.GENERATED

        if episode.status == EpisodeStatus.APPROVED:
            episode.status = EpisodeStatus.BRIEF_READY
        await self._refresh_series_brief_gate(series)

    async def _refresh_series_brief_gate(
        self,
        series: Series,
        approved_at: datetime | None = None,
    ) -> None:
        await self.session.flush()
        approved_episode_ids = await self._approved_episode_ids(series.id)
        if approved_episode_ids:
            series.briefs_approved_at = (
                series.briefs_approved_at or approved_at or datetime.now(UTC)
            )
            series.current_stage = SeriesStage.RECORDINGS
            series.status = SeriesStatus.IN_PRODUCTION
            return

        series.briefs_approved_at = None
        if series.current_stage == SeriesStage.RECORDINGS:
            series.current_stage = SeriesStage.BRIEFS

    async def _approved_episode_ids(self, series_id: UUID) -> set[UUID]:
        result = await self.session.execute(
            select(EpisodeBrief.episode_id)
            .where(
                EpisodeBrief.series_id == series_id,
                EpisodeBrief.status == BriefStatus.APPROVED,
            )
            .group_by(EpisodeBrief.episode_id)
            .having(func.count(EpisodeBrief.id) == 2)
        )
        return set(result.scalars().all())

    async def _episodes(self, series_id: UUID) -> list[Episode]:
        result = await self.session.execute(
            select(Episode)
            .where(Episode.series_id == series_id)
            .order_by(Episode.episode_number.asc())
        )
        return list(result.scalars().all())

    async def _get_episode(self, series_id: UUID, episode_id: UUID) -> Episode:
        episode = await self.session.get(Episode, episode_id)
        if episode is None or episode.series_id != series_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found")
        return episode

    async def _get_brief_with_episode(
        self,
        series_id: UUID,
        brief_id: UUID,
    ) -> tuple[EpisodeBrief, Episode]:
        result = await self.session.execute(
            select(EpisodeBrief, Episode)
            .join(Episode, Episode.id == EpisodeBrief.episode_id)
            .where(EpisodeBrief.series_id == series_id, EpisodeBrief.id == brief_id)
        )
        row = result.one_or_none()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")
        brief, episode = row
        return brief, episode

    async def _briefs_for_episode(self, series_id: UUID, episode_id: UUID) -> list[EpisodeBrief]:
        result = await self.session.execute(
            select(EpisodeBrief)
            .where(EpisodeBrief.series_id == series_id, EpisodeBrief.episode_id == episode_id)
            .order_by(EpisodeBrief.kind.asc())
        )
        return list(result.scalars().all())

    async def _briefs_by_episode(self, series_id: UUID) -> dict[UUID, list[EpisodeBrief]]:
        result = await self.session.execute(
            select(EpisodeBrief)
            .where(EpisodeBrief.series_id == series_id)
            .order_by(EpisodeBrief.episode_id.asc(), EpisodeBrief.kind.asc())
        )
        grouped: dict[UUID, list[EpisodeBrief]] = {}
        for brief in result.scalars().all():
            grouped.setdefault(brief.episode_id, []).append(brief)
        return grouped

    async def _outlines_by_episode(self, series_id: UUID) -> dict[UUID, EpisodeOutline]:
        result = await self.session.execute(
            select(EpisodeOutline).where(EpisodeOutline.series_id == series_id)
        )
        return {outline.episode_id: outline for outline in result.scalars().all()}

    async def _profile_map(self, profile_ids: set[UUID]) -> dict[UUID, Profile]:
        if not profile_ids:
            return {}
        result = await self.session.execute(select(Profile).where(Profile.id.in_(profile_ids)))
        return {profile.id: profile for profile in result.scalars().all()}

    async def _versions_by_brief(
        self,
        brief_ids: set[UUID],
    ) -> dict[UUID, list[BriefVersion]]:
        if not brief_ids:
            return {}
        result = await self.session.execute(
            select(BriefVersion)
            .where(BriefVersion.brief_id.in_(brief_ids))
            .order_by(BriefVersion.brief_id.asc(), BriefVersion.version_number.desc())
        )
        grouped: dict[UUID, list[BriefVersion]] = {}
        for version in result.scalars().all():
            grouped.setdefault(version.brief_id, []).append(version)
        return grouped

    async def _current_version(self, brief: EpisodeBrief) -> BriefVersion | None:
        if brief.current_version_id is None:
            return None
        return await self.session.get(BriefVersion, brief.current_version_id)

    async def _latest_version_number(self, brief: EpisodeBrief) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.max(BriefVersion.version_number), 0)).where(
                BriefVersion.brief_id == brief.id
            )
        )
        return int(result.scalar_one())

    def _episode_payload(
        self,
        series: Series,
        episode: Episode,
        outline: EpisodeOutline | None,
        briefs: list[EpisodeBrief],
        versions_by_brief: dict[UUID, list[BriefVersion]],
        profiles: dict[UUID, Profile],
    ) -> dict[str, object]:
        briefs_by_kind = {brief.kind: brief for brief in briefs}
        host_profile = profiles.get(episode.host_profile_id) if episode.host_profile_id else None
        guest_profile = profiles.get(episode.guest_profile_id) if episode.guest_profile_id else None
        host_brief = briefs_by_kind.get(BriefKind.HOST)
        guest_brief = briefs_by_kind.get(BriefKind.GUEST)
        requirement = self._requirement_payload(episode, outline, host_profile, guest_profile)
        pair_generated = host_brief is not None and guest_brief is not None
        pair_approved = (
            pair_generated
            and host_brief.status == BriefStatus.APPROVED
            and guest_brief.status == BriefStatus.APPROVED
        )
        pair_approved_at = (
            self._pair_approved_at(host_brief, guest_brief) if pair_approved else None
        )
        approval_invalidated_at = self._pair_invalidated_at(host_brief, guest_brief)

        return {
            "episode_id": episode.id,
            "episode_number": episode.episode_number,
            "episode_title": episode.title,
            "episode_premise": episode.premise,
            "episode_status": episode.status,
            "requirement": requirement,
            "host_brief": self._brief_payload(
                brief=host_brief,
                profile=host_profile,
                episode=episode,
                versions=versions_by_brief.get(host_brief.id, []) if host_brief else [],
            )
            if host_brief
            else None,
            "guest_brief": self._brief_payload(
                brief=guest_brief,
                profile=guest_profile,
                episode=episode,
                versions=versions_by_brief.get(guest_brief.id, []) if guest_brief else [],
            )
            if guest_brief
            else None,
            "pair_generated": pair_generated,
            "pair_approved": pair_approved,
            "pair_approved_at": pair_approved_at,
            "approval_invalidated_at": approval_invalidated_at,
        }

    def _requirement_payload(
        self,
        episode: Episode,
        outline: EpisodeOutline | None,
        host_profile: Profile | None,
        guest_profile: Profile | None,
    ) -> dict[str, object]:
        missing = []
        if host_profile is None:
            missing.append("host profile")
        if guest_profile is None:
            missing.append("guest profile")
        if outline is None:
            missing.append("outline")
        elif outline.current_version_id is None:
            missing.append("outline version")
        elif outline.status != EpisodeOutlineStatus.APPROVED:
            missing.append("outline approval")

        return {
            "episode_id": episode.id,
            "episode_number": episode.episode_number,
            "episode_title": episode.title,
            "host_profile_id": episode.host_profile_id,
            "host_profile_name": host_profile.name if host_profile else None,
            "guest_profile_id": episode.guest_profile_id,
            "guest_profile_name": guest_profile.name if guest_profile else None,
            "outline_id": outline.id if outline else None,
            "outline_status": outline.status if outline else None,
            "outline_current_version_id": outline.current_version_id if outline else None,
            "missing_requirements": missing,
            "can_generate": not missing,
        }

    def _brief_payload(
        self,
        brief: EpisodeBrief,
        profile: Profile | None,
        episode: Episode,
        versions: list[BriefVersion],
    ) -> dict[str, object]:
        read_only_reason = self._read_only_reason(episode)
        latest_version_number = versions[0].version_number if versions else None
        return {
            "id": brief.id,
            "series_id": brief.series_id,
            "episode_id": brief.episode_id,
            "kind": brief.kind,
            "title": brief.title,
            "brief_markdown": brief.brief_markdown,
            "status": brief.status,
            "current_version_id": brief.current_version_id,
            "approved_version_id": brief.approved_version_id,
            "approved_at": brief.approved_at,
            "approval_invalidated_at": brief.approval_invalidated_at,
            "created_at": brief.created_at,
            "updated_at": brief.updated_at,
            "profile_id": profile.id if profile else None,
            "profile_name": profile.name if profile else None,
            "profile_role_title": profile.role_title if profile else None,
            "version_count": len(versions),
            "latest_version_number": latest_version_number,
            "can_edit": read_only_reason is None,
            "read_only_reason": read_only_reason,
            "versions": versions,
        }

    def _assert_plan_locked(self, series: Series) -> None:
        if series.plan_locked_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Lock the episode plan before working on briefs",
            )

    def _assert_briefs_editable(self, episode: Episode) -> None:
        reason = self._read_only_reason(episode)
        if reason is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=reason)

    def _read_only_reason(self, episode: Episode) -> str | None:
        if episode.status in RECORDED_OR_LATER_STATUSES:
            return "Briefs are read-only because recording has started"
        return None

    def _brief_title(
        self,
        episode: Episode,
        profile: Profile,
        kind: BriefKind,
        regenerated: bool = False,
    ) -> str:
        prefix = "Regenerated" if regenerated else "Generated"
        return f"{prefix} {kind.value} brief: {episode.title} for {profile.name}"

    def _generated_brief_markdown(
        self,
        series: Series,
        episode: Episode,
        kind: BriefKind,
        profile: Profile,
        counterpart: Profile,
        outline_version: OutlineVersion,
        regenerated: bool = False,
    ) -> str:
        action = "Regenerated" if regenerated else "Generated"
        lane = "Host" if kind == BriefKind.HOST else "Guest"
        counterpart_label = "guest" if kind == BriefKind.HOST else "host"
        outline_focus = self._brief_outline_focus(outline_version)
        profile_note = f"- Profile note: {profile.bio}\n" if profile.bio else ""
        if kind == BriefKind.HOST:
            role_sections = (
                "### Host mission\n"
                f"- Own the editorial throughline for {series.audience}.\n"
                "- Move the conversation from setup to insight to practical takeaway.\n"
                f"- Bring {counterpart.name} in for examples, tensions, and proof points.\n\n"
                "### Question flow\n"
                "- Open with the audience problem and why this episode matters now.\n"
                "- Ask for the clearest lived example before expanding into analysis.\n"
                "- Probe tradeoffs, risks, and what a producer should listen for.\n"
                "- Close by turning the strongest insight into an actionable takeaway.\n\n"
                "### Handoff cues\n"
                f"- Invite {counterpart.name} to validate or challenge the outline promise.\n"
                "- Pause after dense answers and restate the usable signal for listeners.\n"
                "- Keep claims anchored to the approved outline and episode premise.\n\n"
                "### Producer notes for host\n"
                "- Prepare two follow-up questions that can rescue a generic answer.\n"
                "- Watch for over-explaining; the host brief should protect pace and clarity.\n"
            )
        else:
            role_sections = (
                "### Guest contribution\n"
                f"- Bring specialist perspective for {series.audience} "
                "without retelling the full outline.\n"
                "- Prepare specific examples, decisions, or observations that prove the premise.\n"
                f"- Give {counterpart.name} clean openings for follow-up questions.\n\n"
                "### Talking points to prepare\n"
                "- A short origin story or firsthand example tied to the episode premise.\n"
                "- One useful tension, mistake, or tradeoff the audience should understand.\n"
                "- One practical takeaway the host can return to near the close.\n\n"
                "### Evidence and boundaries\n"
                "- Bring concrete names, numbers, moments, or artifacts where available.\n"
                "- Flag anything speculative so the host can frame it responsibly.\n"
                "- Avoid broad commentary that does not connect to the selected narrative.\n\n"
                "### Producer notes for guest\n"
                "- Keep answers modular so the host can redirect or deepen the thread.\n"
                "- Prepare a concise final answer that leaves the audience with next steps.\n"
            )
        return (
            f"## {lane} Brief: {episode.title}\n\n"
            f"### Series context\n"
            f"- Series: {series.name}\n"
            f"- Audience: {series.audience}\n"
            f"- Episode premise: {episode.premise}\n\n"
            f"### Persona guidance\n"
            f"- Assigned {kind.value}: {profile.name}, {profile.role_title}\n"
            f"- Archetype: {profile.archetype}\n"
            f"{profile_note}"
            f"- Coordinate with {counterpart_label}: {counterpart.name}\n\n"
            "### Outline context\n"
            f"- Uses latest approved outline version {outline_version.version_number}.\n"
            f"- Outline title: {outline_version.title}\n\n"
            f"- Outline focus: {outline_focus}\n\n"
            f"{role_sections}\n\n"
            "### Production notes\n"
            f"- {action} by the Brief service for producer review.\n"
            "- Approval applies only when both host and guest briefs are approved together.\n"
        )

    def _brief_outline_focus(self, outline_version: OutlineVersion) -> str:
        outline_text = " ".join(outline_version.outline_markdown.split())
        if not outline_text:
            return "Use the approved outline as the source of truth."
        if len(outline_text) <= 260:
            return outline_text
        return f"{outline_text[:257]}..."

    def _pair_approved_at(
        self,
        host_brief: EpisodeBrief | None,
        guest_brief: EpisodeBrief | None,
    ) -> datetime | None:
        timestamps = [
            brief.approved_at for brief in (host_brief, guest_brief) if brief and brief.approved_at
        ]
        return min(timestamps) if timestamps else None

    def _pair_invalidated_at(
        self,
        host_brief: EpisodeBrief | None,
        guest_brief: EpisodeBrief | None,
    ) -> datetime | None:
        timestamps = [
            brief.approval_invalidated_at
            for brief in (host_brief, guest_brief)
            if brief and brief.approval_invalidated_at
        ]
        return max(timestamps) if timestamps else None

    def _readiness_warnings(
        self,
        total_count: int,
        generated_count: int,
        approved_count: int,
    ) -> list[str]:
        warnings = []
        if total_count == 0:
            warnings.append("No locked episodes exist for Brief generation.")
            return warnings
        if generated_count < total_count:
            warnings.append(
                f"{total_count - generated_count} episode(s) still need explicit brief generation."
            )
        if generated_count and approved_count == 0:
            warnings.append("Approve one host/guest brief pair to unlock Recordings.")
        if approved_count and approved_count < total_count:
            warnings.append(f"{total_count - approved_count} episode(s) still need pair approval.")
        return warnings
