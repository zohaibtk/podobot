from datetime import UTC, datetime
from typing import TypedDict
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.workflow import record_workflow_agent_run
from app.db.types import EpisodeOutlineStatus, EpisodeStatus, OutlineVersionSource, SeriesStage
from app.modules.episodes.models import Episode
from app.modules.outlines.models import EpisodeOutline, OutlineVersion
from app.modules.outlines.schemas import OutlineRegenerateRequest, OutlineUpdateRequest
from app.modules.series.models import Series
from app.modules.series.service import SeriesService
from app.schemas.pagination import OffsetParams, offset_meta

DOWNSTREAM_DEPENDENCY_STATUSES = {
    EpisodeStatus.BRIEF_READY,
    EpisodeStatus.APPROVED,
    EpisodeStatus.RECORDED,
    EpisodeStatus.CAPTIONING,
    EpisodeStatus.SCHEDULED,
    EpisodeStatus.PARTIALLY_PUBLISHED,
    EpisodeStatus.PUBLISHED,
}


class OutlineVariant(TypedDict):
    angle: str
    audience: list[str]
    beat_heading: str
    beats: list[str]
    handoff: str


class OutlineService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.series_service = SeriesService(session)

    async def get_workspace(self, series_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_plan_locked(series)
        await self._ensure_outlines_for_locked_plan(series)
        await self.session.commit()
        return await self._workspace_response(series_id)

    async def update_outline(
        self,
        series_id: UUID,
        outline_id: UUID,
        payload: OutlineUpdateRequest,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_plan_locked(series)
        outline, episode = await self._get_outline_with_episode(series_id, outline_id)
        self._assert_outline_editable(episode)
        self._assert_outline_not_approved(outline)

        title = payload.title or outline.title
        version = await self._create_version(
            outline=outline,
            title=title,
            outline_markdown=payload.outline_markdown,
            source=OutlineVersionSource.MANUAL_EDIT,
        )
        outline.title = title
        outline.outline_markdown = payload.outline_markdown
        outline.status = EpisodeOutlineStatus.DRAFT
        outline.current_version_id = version.id
        outline.approved_version_id = None
        outline.approved_at = None
        await self._refresh_series_outline_gate(series)

        await self.session.commit()
        return await self._workspace_response(series_id)

    async def regenerate_outline(
        self,
        series_id: UUID,
        outline_id: UUID,
        payload: OutlineRegenerateRequest | None = None,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_plan_locked(series)
        outline, episode = await self._get_outline_with_episode(series_id, outline_id)
        self._assert_outline_editable(episode)

        instruction = self._clean_instruction(payload.instruction if payload else None)
        next_version_number = await self._next_version_number(outline.id)
        outline_markdown = self._generated_outline_markdown(
            series,
            episode,
            regenerated=True,
            instruction=instruction,
            variant_seed=next_version_number,
        )
        title = self._regenerated_outline_title(episode, next_version_number)
        version = await self._create_version(
            outline=outline,
            title=title,
            outline_markdown=outline_markdown,
            source=OutlineVersionSource.REGENERATION,
        )
        outline.title = title
        outline.outline_markdown = outline_markdown
        outline.status = EpisodeOutlineStatus.GENERATED
        outline.current_version_id = version.id
        outline.approved_version_id = None
        outline.approved_at = None
        await self._refresh_series_outline_gate(series)
        await record_workflow_agent_run(
            self.session,
            agent_key="outline",
            entity_type="series",
            entity_id=series.id,
            workflow_stage="outlines",
            trigger="regeneration",
            input_payload={"outline_id": str(outline.id), "episode_id": str(episode.id)},
            output_payload={
                "summary": "Outline regenerated as a new version.",
                "instruction": instruction,
                "needs_approval": True,
                "outline_version": version.version_number,
            },
        )

        await self.session.commit()
        return await self._workspace_response(series_id)

    async def approve_outline(
        self,
        series_id: UUID,
        outline_id: UUID,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_plan_locked(series)
        outline, episode = await self._get_outline_with_episode(series_id, outline_id)
        self._assert_outline_editable(episode)
        if outline.current_version_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Outline must have a current version before approval",
            )

        outline.status = EpisodeOutlineStatus.APPROVED
        outline.approved_version_id = outline.current_version_id
        outline.approved_at = datetime.now(UTC)
        await self._refresh_series_outline_gate(series)

        await self.session.commit()
        return await self._workspace_response(series_id)

    async def list_versions(
        self,
        series_id: UUID,
        outline_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        self._assert_plan_locked(series)
        outline, _episode = await self._get_outline_with_episode(series_id, outline_id)
        total = int(
            (
                await self.session.execute(
                    select(func.count(OutlineVersion.id)).where(
                        OutlineVersion.outline_id == outline.id
                    )
                )
            ).scalar_one()
        )
        pagination = OffsetParams(page=page, page_size=page_size)
        result = await self.session.execute(
            select(OutlineVersion)
            .where(OutlineVersion.outline_id == outline.id)
            .order_by(OutlineVersion.version_number.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        return {
            "items": list(result.scalars().all()),
            **offset_meta(total=total, page=page, page_size=page_size),
        }

    async def create_outline_for_episode(
        self,
        series: Series,
        episode: Episode,
    ) -> EpisodeOutline:
        outline_markdown = self._generated_outline_markdown(series, episode)
        outline = EpisodeOutline(
            series_id=series.id,
            episode_id=episode.id,
            title=f"Generated outline: {episode.title}",
            outline_markdown=outline_markdown,
            status=EpisodeOutlineStatus.GENERATED,
        )
        self.session.add(outline)
        await self.session.flush()

        version = await self._create_version(
            outline=outline,
            title=outline.title,
            outline_markdown=outline.outline_markdown,
            source=OutlineVersionSource.LOCK_GENERATED,
        )
        outline.current_version_id = version.id
        await self.session.flush()
        await record_workflow_agent_run(
            self.session,
            agent_key="outline",
            entity_type="series",
            entity_id=series.id,
            workflow_stage="outlines",
            trigger="generation",
            input_payload={"episode_id": str(episode.id)},
            output_payload={
                "summary": "Profile-agnostic outline generated from locked plan.",
                "needs_approval": True,
                "outline_id": str(outline.id),
            },
        )
        return outline

    async def _workspace_response(self, series_id: UUID) -> dict[str, object]:
        series = await self.series_service.get_series(series_id)
        await self.session.refresh(series)
        rows = await self._outline_episode_rows(series_id)
        versions_by_outline = await self._versions_by_outline({outline.id for outline, _ in rows})
        outline_payloads = [
            self._outline_payload(outline, episode, versions_by_outline.get(outline.id, []))
            for outline, episode in rows
        ]
        approved_count = sum(outline["is_ready_for_brief"] for outline in outline_payloads)
        warnings = []
        if not outline_payloads:
            warnings.append("No outlines exist for the locked plan.")
        if outline_payloads and approved_count != len(outline_payloads):
            warnings.append("Every outline must be approved before Brief generation is ready.")

        return {
            "series": series,
            "outlines": outline_payloads,
            "readiness": {
                "total_outline_count": len(outline_payloads),
                "approved_outline_count": approved_count,
                "is_ready_for_briefs": bool(outline_payloads)
                and approved_count == len(outline_payloads),
                "warnings": warnings,
            },
        }

    async def _ensure_outlines_for_locked_plan(self, series: Series) -> None:
        episodes = await self._episodes(series.id)
        existing = await self._outlines(series.id)
        existing_episode_ids = {outline.episode_id for outline in existing}
        for episode in episodes:
            if episode.id not in existing_episode_ids:
                await self.create_outline_for_episode(series, episode)

        for outline in existing:
            versions = await self._versions(outline.id)
            if not versions:
                version = await self._create_version(
                    outline=outline,
                    title=outline.title,
                    outline_markdown=outline.outline_markdown,
                    source=OutlineVersionSource.LOCK_GENERATED,
                )
                outline.current_version_id = version.id

    async def _refresh_series_outline_gate(self, series: Series) -> None:
        await self.session.flush()
        outlines = await self._outlines(series.id)
        if outlines and all(
            outline.status == EpisodeOutlineStatus.APPROVED for outline in outlines
        ):
            series.current_stage = SeriesStage.BRIEFS
            return

        if series.current_stage == SeriesStage.BRIEFS:
            series.current_stage = SeriesStage.OUTLINES

    async def _create_version(
        self,
        outline: EpisodeOutline,
        title: str,
        outline_markdown: str,
        source: OutlineVersionSource,
    ) -> OutlineVersion:
        version_number = await self._next_version_number(outline.id)
        version = OutlineVersion(
            outline_id=outline.id,
            series_id=outline.series_id,
            episode_id=outline.episode_id,
            version_number=version_number,
            title=title,
            outline_markdown=outline_markdown,
            source=source,
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def _next_version_number(self, outline_id: UUID) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.max(OutlineVersion.version_number), 0)).where(
                OutlineVersion.outline_id == outline_id
            )
        )
        return int(result.scalar_one()) + 1

    async def _outline_episode_rows(self, series_id: UUID) -> list[tuple[EpisodeOutline, Episode]]:
        result = await self.session.execute(
            select(EpisodeOutline, Episode)
            .join(Episode, Episode.id == EpisodeOutline.episode_id)
            .where(EpisodeOutline.series_id == series_id)
            .order_by(Episode.episode_number.asc())
        )
        return [(outline, episode) for outline, episode in result.all()]

    async def _get_outline_with_episode(
        self,
        series_id: UUID,
        outline_id: UUID,
    ) -> tuple[EpisodeOutline, Episode]:
        result = await self.session.execute(
            select(EpisodeOutline, Episode)
            .join(Episode, Episode.id == EpisodeOutline.episode_id)
            .where(EpisodeOutline.series_id == series_id, EpisodeOutline.id == outline_id)
        )
        row = result.one_or_none()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outline not found")
        outline, episode = row
        return outline, episode

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

    async def _versions(self, outline_id: UUID) -> list[OutlineVersion]:
        result = await self.session.execute(
            select(OutlineVersion)
            .where(OutlineVersion.outline_id == outline_id)
            .order_by(OutlineVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def _versions_by_outline(
        self,
        outline_ids: set[UUID],
    ) -> dict[UUID, list[OutlineVersion]]:
        if not outline_ids:
            return {}
        result = await self.session.execute(
            select(OutlineVersion)
            .where(OutlineVersion.outline_id.in_(outline_ids))
            .order_by(OutlineVersion.outline_id.asc(), OutlineVersion.version_number.desc())
        )
        grouped: dict[UUID, list[OutlineVersion]] = {}
        for version in result.scalars().all():
            grouped.setdefault(version.outline_id, []).append(version)
        return grouped

    def _outline_payload(
        self,
        outline: EpisodeOutline,
        episode: Episode,
        versions: list[OutlineVersion],
    ) -> dict[str, object]:
        read_only_reason = self._read_only_reason(episode)
        latest_version_number = versions[0].version_number if versions else None
        return {
            "id": outline.id,
            "series_id": outline.series_id,
            "episode_id": outline.episode_id,
            "title": outline.title,
            "outline_markdown": outline.outline_markdown,
            "status": outline.status,
            "current_version_id": outline.current_version_id,
            "approved_version_id": outline.approved_version_id,
            "approved_at": outline.approved_at,
            "created_at": outline.created_at,
            "updated_at": outline.updated_at,
            "episode_number": episode.episode_number,
            "episode_title": episode.title,
            "episode_premise": episode.premise,
            "version_count": len(versions),
            "latest_version_number": latest_version_number,
            "can_edit": read_only_reason is None,
            "read_only_reason": read_only_reason,
            "is_ready_for_brief": outline.status == EpisodeOutlineStatus.APPROVED,
            "versions": versions,
        }

    def _assert_plan_locked(self, series: Series) -> None:
        if series.plan_locked_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Lock the episode plan before working on outlines",
            )

    def _assert_outline_editable(self, episode: Episode) -> None:
        reason = self._read_only_reason(episode)
        if reason is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=reason)

    def _assert_outline_not_approved(self, outline: EpisodeOutline) -> None:
        if outline.status == EpisodeOutlineStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Approved outlines are read-only. Regenerate the outline to create "
                    "a new editable version."
                ),
            )

    def _read_only_reason(self, episode: Episode) -> str | None:
        if episode.status in DOWNSTREAM_DEPENDENCY_STATUSES:
            return "Outline is read-only because downstream dependencies already exist"
        return None

    def _generated_outline_markdown(
        self,
        series: Series,
        episode: Episode,
        regenerated: bool = False,
        instruction: str | None = None,
        variant_seed: int | None = None,
    ) -> str:
        action_label = "Regenerated" if regenerated else "Generated"
        variant = self._outline_variant(variant_seed)
        version_label = f" v{variant_seed}" if regenerated and variant_seed else ""
        instruction_line = (
            f"- Producer direction: {instruction}\n"
            if instruction
            else f"- Regeneration angle: {variant['angle']}\n"
        )
        audience_lines = "\n".join(f"- {line}" for line in variant["audience"])
        beat_lines = "\n".join(f"- {line}" for line in variant["beats"])
        return (
            f"## {episode.title}\n\n"
            f"### Narrative promise\n"
            f"- {episode.premise}\n\n"
            f"### Audience frame\n"
            f"- Built for {series.audience}.\n"
            f"{instruction_line}"
            f"{audience_lines}\n\n"
            f"### {variant['beat_heading']}\n"
            f"{beat_lines}\n\n"
            "### Brief handoff context\n"
            f"- {action_label} outline{version_label} is the latest context source "
            "for Brief generation.\n"
            f"- {variant['handoff']}\n"
        )

    def _outline_variant(self, variant_seed: int | None) -> OutlineVariant:
        variants: list[OutlineVariant] = [
            {
                "angle": "Set up the stakes, then move from evidence to producer decisions.",
                "audience": [
                    "Keep the outline profile-agnostic so host and guest voices can be "
                    "assigned later.",
                    "Make the executive takeaway visible before the Brief stage expands "
                    "the script.",
                ],
                "beat_heading": "Editorial beats",
                "beats": [
                    "Opening context and stakes",
                    "Evidence, examples, and implications",
                    "Producer notes for the Brief stage",
                ],
                "handoff": (
                    "Brief should preserve the decision arc and avoid adding "
                    "profile-specific voice."
                ),
            },
            {
                "angle": (
                    "Lead with a sharper hook, then organize the story around proof "
                    "and consequence."
                ),
                "audience": [
                    "Frame the episode for listeners who need a concise, action-oriented read.",
                    "Leave room for host and guest assignments without naming final speakers.",
                ],
                "beat_heading": "Producer beat map",
                "beats": [
                    "Cold-open hook that names the central tension",
                    "Context setup with the strongest supporting signal",
                    "What changes for the audience if this promise is true",
                    "Brief notes for examples, transitions, and emphasis",
                ],
                "handoff": (
                    "Brief should expand the hook and consequence before drafting "
                    "speaker-specific guidance."
                ),
            },
            {
                "angle": (
                    "Stress-test the premise with counterpoints before landing the "
                    "usable takeaway."
                ),
                "audience": [
                    "Write for listeners comparing options, tradeoffs, or operational next steps.",
                    "Keep the outline adaptable for different host and guest pairings.",
                ],
                "beat_heading": "Argument flow",
                "beats": [
                    "Initial claim and why it matters now",
                    "Counterpoint, risk, or uncertainty worth acknowledging",
                    "Evidence that resolves or narrows the tension",
                    "Practical takeaway the Brief can turn into segments",
                ],
                "handoff": (
                    "Brief should turn the counterpoint into a clear segment, not a "
                    "passing caveat."
                ),
            },
        ]
        index = 0 if variant_seed is None else (variant_seed - 1) % len(variants)
        return variants[index]

    def _clean_instruction(self, instruction: str | None) -> str | None:
        if instruction is None:
            return None
        cleaned = " ".join(instruction.split())
        return cleaned or None

    def _regenerated_outline_title(self, episode: Episode, version_number: int) -> str:
        title = f"Regenerated outline v{version_number}: {episode.title}"
        return title[:220]
