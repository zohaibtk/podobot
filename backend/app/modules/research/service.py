from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import models as _agent_models  # noqa: F401
from app.db.types import (
    DiscoveryLedgerType,
    ResearchConfidenceLevel,
    ResearchRunSourceUsageStatus,
    ResearchRunStatus,
    ResearchRunType,
    ResearchSourceCategory,
)
from app.mcp import models as _mcp_models  # noqa: F401
from app.mcp.security import redact_sensitive
from app.modules.episodes import models as _episode_models  # noqa: F401
from app.modules.research.models import (
    DiscoveryLedgerEntry,
    ResearchDocument,
    ResearchRun,
    ResearchRunSourceUsage,
)
from app.modules.research_sources.models import ResearchSource
from app.modules.research_sources.service import ResearchSourceService
from app.modules.series import models as _series_models  # noqa: F401
from app.modules.settings import models as _settings_models  # noqa: F401
from app.modules.strategy import models as _strategy_models  # noqa: F401
from app.schemas.pagination import OffsetParams, offset_meta


class ResearchPersistenceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.source_service = ResearchSourceService(session)

    async def list_runs(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        sort: str = "-created_at",
        status_filter: ResearchRunStatus | None = None,
        run_type: ResearchRunType | None = None,
        series_id: UUID | None = None,
        episode_id: UUID | None = None,
        strategy_run_id: UUID | None = None,
        source_id: UUID | None = None,
    ) -> dict[str, object]:
        pagination = OffsetParams(page=page, page_size=page_size)
        statement = self._run_statement(
            search=search,
            status_filter=status_filter,
            run_type=run_type,
            series_id=series_id,
            episode_id=episode_id,
            strategy_run_id=strategy_run_id,
            source_id=source_id,
        )
        total = await self._count(statement)
        result = await self.session.execute(
            statement.order_by(*self._run_order_by(sort))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        return {
            "items": [self._run_payload(run) for run in result.scalars().all()],
            "stats": await self.stats(),
            **offset_meta(total=total, page=page, page_size=page_size),
        }

    async def get_run_detail(self, run_id: UUID) -> dict[str, object]:
        run = await self._run(run_id)
        from app.modules.research.scoring import ResearchScoringService

        return {
            **self._run_payload(run),
            "source_usage": (
                await self.list_source_usage(
                    research_run_id=run_id,
                    page=1,
                    page_size=200,
                    sort="started_at",
                )
            )["items"],
            "documents": (
                await self.list_documents(
                    research_run_id=run_id,
                    page=1,
                    page_size=200,
                    sort="-created_at",
                )
            )["items"],
            "ledger_entries": (
                await self.list_ledger_entries(
                    research_run_id=run_id,
                    page=1,
                    page_size=200,
                    sort="-created_at",
                )
            )["items"],
            "score_summary": await ResearchScoringService(self.session).run_score_summary(run_id),
        }

    async def list_documents(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        sort: str = "-created_at",
        research_run_id: UUID | None = None,
        source_id: UUID | None = None,
        series_id: UUID | None = None,
        episode_id: UUID | None = None,
        archived: bool | None = None,
    ) -> dict[str, object]:
        pagination = OffsetParams(page=page, page_size=page_size)
        statement = (
            select(ResearchDocument, ResearchSource)
            .join(ResearchSource, ResearchSource.id == ResearchDocument.source_id)
            .join(ResearchRun, ResearchRun.id == ResearchDocument.research_run_id)
        )
        if research_run_id is not None:
            statement = statement.where(ResearchDocument.research_run_id == research_run_id)
        if source_id is not None:
            statement = statement.where(ResearchDocument.source_id == source_id)
        if series_id is not None:
            statement = statement.where(ResearchRun.series_id == series_id)
        if episode_id is not None:
            statement = statement.where(ResearchRun.episode_id == episode_id)
        if archived is not None:
            statement = statement.where(ResearchDocument.archived.is_(archived))
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    ResearchDocument.title.ilike(pattern),
                    ResearchDocument.url.ilike(pattern),
                    ResearchDocument.author.ilike(pattern),
                    ResearchDocument.content_excerpt.ilike(pattern),
                )
            )
        total = await self._count(statement)
        result = await self.session.execute(
            statement.order_by(*self._document_order_by(sort))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        items = [
            self._document_payload(document, source)
            for document, source in result.all()
        ]
        return {
            "items": items,
            **offset_meta(total=total, page=page, page_size=page_size),
        }

    async def list_ledger_entries(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        sort: str = "-created_at",
        research_run_id: UUID | None = None,
        source_id: UUID | None = None,
        series_id: UUID | None = None,
        episode_id: UUID | None = None,
        strategy_idea_id: UUID | None = None,
        ledger_type: DiscoveryLedgerType | None = None,
    ) -> dict[str, object]:
        pagination = OffsetParams(page=page, page_size=page_size)
        statement = (
            select(DiscoveryLedgerEntry, ResearchSource, ResearchDocument)
            .join(ResearchSource, ResearchSource.id == DiscoveryLedgerEntry.source_id)
            .outerjoin(ResearchDocument, ResearchDocument.id == DiscoveryLedgerEntry.document_id)
        )
        if research_run_id is not None:
            statement = statement.where(DiscoveryLedgerEntry.research_run_id == research_run_id)
        if source_id is not None:
            statement = statement.where(DiscoveryLedgerEntry.source_id == source_id)
        if series_id is not None:
            statement = statement.where(DiscoveryLedgerEntry.series_id == series_id)
        if episode_id is not None:
            statement = statement.where(DiscoveryLedgerEntry.episode_id == episode_id)
        if strategy_idea_id is not None:
            statement = statement.where(DiscoveryLedgerEntry.strategy_idea_id == strategy_idea_id)
        if ledger_type is not None:
            statement = statement.where(DiscoveryLedgerEntry.ledger_type == ledger_type)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    DiscoveryLedgerEntry.evidence_summary.ilike(pattern),
                    ResearchDocument.title.ilike(pattern),
                    ResearchDocument.url.ilike(pattern),
                    ResearchSource.name.ilike(pattern),
                )
            )
        total = await self._count(statement)
        result = await self.session.execute(
            statement.order_by(*self._ledger_order_by(sort))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        return {
            "items": [
                self._ledger_payload(entry, source, document)
                for entry, source, document in result.all()
            ],
            **offset_meta(total=total, page=page, page_size=page_size),
        }

    async def list_source_usage(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        sort: str = "-created_at",
        research_run_id: UUID | None = None,
        source_id: UUID | None = None,
        status_filter: ResearchRunSourceUsageStatus | None = None,
    ) -> dict[str, object]:
        pagination = OffsetParams(page=page, page_size=page_size)
        statement = select(ResearchRunSourceUsage, ResearchSource).join(
            ResearchSource,
            ResearchSource.id == ResearchRunSourceUsage.source_id,
        )
        if research_run_id is not None:
            statement = statement.where(ResearchRunSourceUsage.research_run_id == research_run_id)
        if source_id is not None:
            statement = statement.where(ResearchRunSourceUsage.source_id == source_id)
        if status_filter is not None:
            statement = statement.where(ResearchRunSourceUsage.status == status_filter)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    ResearchSource.name.ilike(pattern),
                    ResearchSource.key.ilike(pattern),
                    ResearchRunSourceUsage.failure_reason.ilike(pattern),
                    ResearchRunSourceUsage.query_text.ilike(pattern),
                )
            )
        total = await self._count(statement)
        result = await self.session.execute(
            statement.order_by(*self._usage_order_by(sort))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        return {
            "items": [self._source_usage_payload(usage, source) for usage, source in result.all()],
            **offset_meta(total=total, page=page, page_size=page_size),
        }

    async def stats(self) -> dict[str, object]:
        result = await self.session.execute(
            select(
                func.count(ResearchRun.id),
                func.coalesce(
                    func.sum(
                        case(
                            (ResearchRun.status == ResearchRunStatus.RUNNING, 1),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case((ResearchRun.status == ResearchRunStatus.FAILED, 1), else_=0)
                    ),
                    0,
                ),
                func.coalesce(func.sum(ResearchRun.total_documents_found), 0),
                func.coalesce(func.sum(ResearchRun.total_documents_used), 0),
                func.coalesce(func.avg(ResearchRun.duration_ms), 0),
            )
        )
        row = result.one()
        return {
            "total_runs": int(row[0] or 0),
            "running_runs": int(row[1] or 0),
            "failed_runs": int(row[2] or 0),
            "total_documents_found": int(row[3] or 0),
            "total_documents_used": int(row[4] or 0),
            "average_duration_ms": int(row[5] or 0),
        }

    async def start_run(
        self,
        *,
        run_type: ResearchRunType,
        query_text: str,
        series_id: UUID | None = None,
        episode_id: UUID | None = None,
        strategy_run_id: UUID | None = None,
        agent_run_id: UUID | None = None,
        initiated_by_user_id: UUID | None = None,
        metadata_json: Mapping[str, object] | None = None,
        enabled_source_count: int = 0,
    ) -> ResearchRun:
        now = datetime.now(UTC)
        run = ResearchRun(
            run_type=run_type,
            status=ResearchRunStatus.RUNNING,
            query_text=query_text.strip() or "Untitled research run",
            series_id=series_id,
            episode_id=episode_id,
            strategy_run_id=strategy_run_id,
            agent_run_id=agent_run_id,
            initiated_by_user_id=initiated_by_user_id,
            started_at=now,
            metadata_json=redact_sensitive(dict(metadata_json or {})),
            enabled_source_count=enabled_source_count,
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def record_source_usage(
        self,
        *,
        run: ResearchRun,
        source: ResearchSource,
        status_value: ResearchRunSourceUsageStatus,
        query_text: str | None = None,
        documents_found: int = 0,
        documents_used: int = 0,
        latency_ms: int = 0,
        failure_reason: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> ResearchRunSourceUsage:
        usage = ResearchRunSourceUsage(
            research_run_id=run.id,
            source_id=source.id,
            status=status_value,
            query_text=query_text,
            documents_found=max(documents_found, 0),
            documents_used=max(documents_used, 0),
            latency_ms=max(latency_ms, 0),
            failure_reason=failure_reason,
            started_at=started_at,
            completed_at=completed_at or datetime.now(UTC),
        )
        self.session.add(usage)
        source.documents_fetched_today = int(source.documents_fetched_today or 0) + max(
            documents_found,
            0,
        )
        if latency_ms:
            source.average_latency_ms = latency_ms
        if status_value == ResearchRunSourceUsageStatus.FAILED:
            source.recent_failure_count = int(source.recent_failure_count or 0) + 1
            source.last_failure_reason = failure_reason
        else:
            source.recent_failure_count = 0
        await self.session.flush()
        return usage

    async def persist_document(
        self,
        *,
        run: ResearchRun,
        source: ResearchSource,
        document: Mapping[str, object],
        used_in_output: bool = True,
        ledger_type: DiscoveryLedgerType = DiscoveryLedgerType.SOURCE,
        evidence_summary: str | None = None,
        series_id: UUID | None = None,
        episode_id: UUID | None = None,
        strategy_idea_id: UUID | None = None,
    ) -> ResearchDocument:
        persisted = ResearchDocument(
            research_run_id=run.id,
            source_id=source.id,
            provider_type=source.provider_type,
            external_resource_id=self._optional_str(document.get("id")),
            title=self._title(document),
            url=self._optional_str(document.get("url")),
            author=self._optional_str(document.get("author")),
            published_at=self._parse_datetime(document.get("published_at")),
            resource_type=self._resource_type(document),
            content_excerpt=self._excerpt(document),
            normalized_content=self._normalized_content(document),
            raw_metadata_json=redact_sensitive(
                {
                    "metadata": (
                        document.get("metadata")
                        if isinstance(document.get("metadata"), dict)
                        else {}
                    ),
                    "scores": (
                        document.get("scores")
                        if isinstance(document.get("scores"), dict)
                        else {}
                    ),
                    "provider_mode": document.get("provider_mode"),
                    "source_key": document.get("source_key"),
                }
            ),
            used_in_output=used_in_output,
        )
        self.session.add(persisted)
        await self.session.flush()
        from app.modules.research.scoring import ResearchScoringService

        await ResearchScoringService(self.session).score_existing_document(
            persisted,
            source,
            include_trend=False,
        )
        self.session.add(
            DiscoveryLedgerEntry(
                research_run_id=run.id,
                document_id=persisted.id,
                source_id=source.id,
                series_id=series_id or run.series_id,
                episode_id=episode_id or run.episode_id,
                strategy_idea_id=strategy_idea_id,
                ledger_type=ledger_type,
                evidence_summary=evidence_summary or self._evidence_summary(persisted),
            )
        )
        await self.session.flush()
        return persisted

    async def complete_run(self, run: ResearchRun, *, failure_reason: str | None = None) -> None:
        counts = await self._run_counts(run.id)
        run.enabled_source_count = counts["enabled_source_count"] or run.enabled_source_count
        run.successful_source_count = counts["successful_source_count"]
        run.failed_source_count = counts["failed_source_count"]
        run.skipped_source_count = counts["skipped_source_count"]
        run.total_documents_found = counts["total_documents_found"]
        run.total_documents_used = counts["total_documents_used"]
        run.failure_reason = failure_reason
        run.completed_at = datetime.now(UTC)
        if run.started_at is not None:
            run.duration_ms = max(
                0,
                round((run.completed_at - run.started_at).total_seconds() * 1000),
            )
        if failure_reason and counts["successful_source_count"] == 0:
            run.status = ResearchRunStatus.FAILED
        elif counts["failed_source_count"] > 0:
            run.status = ResearchRunStatus.PARTIAL_SUCCESS
        else:
            run.status = ResearchRunStatus.COMPLETED
        await self.session.flush()

    async def fail_run(self, run: ResearchRun, *, failure_reason: str) -> None:
        run.status = ResearchRunStatus.FAILED
        run.failure_reason = failure_reason
        run.completed_at = datetime.now(UTC)
        if run.started_at is not None:
            run.duration_ms = max(
                0,
                round((run.completed_at - run.started_at).total_seconds() * 1000),
            )
        await self.session.flush()

    async def archive_document(self, document_id: UUID) -> dict[str, object]:
        document = await self._document(document_id)
        document.archived = True
        await self.session.commit()
        return {
            "success": True,
            "message": "Research document archived.",
            "document": (
                await self.list_documents(research_run_id=document.research_run_id, page_size=1)
            )["items"][0],
        }

    async def retry_run(self, run_id: UUID) -> dict[str, object]:
        run = await self._run(run_id)
        retry = await self.start_run(
            run_type=run.run_type,
            query_text=run.query_text,
            series_id=run.series_id,
            episode_id=run.episode_id,
            strategy_run_id=run.strategy_run_id,
            agent_run_id=run.agent_run_id,
            metadata_json={"retry_of_run_id": str(run.id), **(run.metadata_json or {})},
            enabled_source_count=run.enabled_source_count,
        )
        await self.complete_run(retry)
        await self.session.commit()
        return {
            "success": True,
            "message": "Research retry created for orchestration.",
            "run": self._run_payload(retry),
        }

    async def clear_failed_runs(self) -> dict[str, object]:
        result = await self.session.execute(
            update(ResearchRun)
            .where(ResearchRun.status == ResearchRunStatus.FAILED)
            .values(status=ResearchRunStatus.CANCELLED, failure_reason="Cleared by administrator.")
            .returning(ResearchRun.id)
        )
        cleared = len(result.scalars().all())
        await self.session.commit()
        return {
            "success": True,
            "message": f"Cleared {cleared} failed research run(s).",
        }

    async def record_strategy_run_evidence(
        self,
        *,
        strategy_run_id: UUID,
        query_text: str,
        ideas: list[object],
    ) -> ResearchRun | None:
        if not ideas:
            return None
        source = await self._default_source()
        run = await self.start_run(
            run_type=ResearchRunType.STRATEGY,
            query_text=query_text,
            strategy_run_id=strategy_run_id,
            metadata_json={"idea_count": len(ideas)},
            enabled_source_count=1,
        )
        documents_found = 0
        for idea in ideas:
            evidence_signals = getattr(idea, "evidence_signals", []) or []
            if not isinstance(evidence_signals, list):
                continue
            for index, signal in enumerate(evidence_signals, start=1):
                if not isinstance(signal, Mapping):
                    continue
                title = str(signal.get("signal_title") or getattr(idea, "title", "Strategy idea"))
                document = {
                    "id": f"{getattr(idea, 'id', 'idea')}:{index}",
                    "title": title,
                    "url": f"https://research.local/strategy/{getattr(idea, 'id', index)}",
                    "snippet": (
                        f"{signal.get('source_name', 'Strategy research')} supports "
                        f"{getattr(idea, 'title', 'this strategy idea')}."
                    ),
                    "metadata": {
                        "source_name": signal.get("source_name"),
                        "confidence_score": signal.get("confidence_score"),
                        "idea_title": getattr(idea, "title", None),
                    },
                }
                await self.persist_document(
                    run=run,
                    source=source,
                    document=document,
                    used_in_output=True,
                    ledger_type=DiscoveryLedgerType.STRATEGY_SUPPORT,
                    evidence_summary=str(document["snippet"]),
                    strategy_idea_id=getattr(idea, "id", None),
                )
                documents_found += 1
        await self.record_source_usage(
            run=run,
            source=source,
            status_value=(
                ResearchRunSourceUsageStatus.USED
                if documents_found
                else ResearchRunSourceUsageStatus.NO_RESULTS
            ),
            query_text=query_text,
            documents_found=documents_found,
            documents_used=documents_found,
            latency_ms=180,
            started_at=run.started_at,
        )
        await self.complete_run(run)
        return run

    async def source_metrics(self, source_ids: list[UUID]) -> dict[UUID, dict[str, object]]:
        if not source_ids:
            return {}
        usage_rows = await self.session.execute(
            select(
                ResearchRunSourceUsage.source_id,
                func.count(ResearchRunSourceUsage.id),
                func.max(ResearchRunSourceUsage.completed_at),
                func.coalesce(func.avg(ResearchRunSourceUsage.latency_ms), 0),
            )
            .where(ResearchRunSourceUsage.source_id.in_(source_ids))
            .group_by(ResearchRunSourceUsage.source_id)
        )
        document_rows = await self.session.execute(
            select(
                ResearchDocument.source_id,
                func.count(ResearchDocument.id),
                func.coalesce(func.avg(ResearchDocument.composite_score), 0),
                func.coalesce(func.avg(ResearchDocument.trend_score), 0),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                ResearchDocument.confidence_level
                                == ResearchConfidenceLevel.HIGH,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                ResearchDocument.confidence_level
                                == ResearchConfidenceLevel.MEDIUM,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                ResearchDocument.confidence_level
                                == ResearchConfidenceLevel.LOW,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                ResearchDocument.confidence_level
                                == ResearchConfidenceLevel.WEAK,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
            )
            .where(ResearchDocument.source_id.in_(source_ids))
            .group_by(ResearchDocument.source_id)
        )
        metrics = {
            source_id: {
                "total_runs": int(run_count or 0),
                "last_run_at": last_run,
                "average_latency_ms": int(avg_latency or 0),
                "documents_collected": 0,
                "average_composite_score": 0,
                "average_trend_score": 0,
                "confidence_distribution": {
                    "High": 0,
                    "Medium": 0,
                    "Low": 0,
                    "Weak": 0,
                },
            }
            for source_id, run_count, last_run, avg_latency in usage_rows.all()
        }
        for (
            source_id,
            documents_collected,
            average_composite_score,
            average_trend_score,
            high_count,
            medium_count,
            low_count,
            weak_count,
        ) in document_rows.all():
            source_metrics = metrics.setdefault(
                source_id,
                {
                    "total_runs": 0,
                    "last_run_at": None,
                    "average_latency_ms": 0,
                    "documents_collected": 0,
                    "average_composite_score": 0,
                    "average_trend_score": 0,
                    "confidence_distribution": {
                        "High": 0,
                        "Medium": 0,
                        "Low": 0,
                        "Weak": 0,
                    },
                },
            )
            source_metrics["documents_collected"] = int(documents_collected or 0)
            source_metrics["average_composite_score"] = int(average_composite_score or 0)
            source_metrics["average_trend_score"] = int(average_trend_score or 0)
            source_metrics["confidence_distribution"] = {
                "High": int(high_count or 0),
                "Medium": int(medium_count or 0),
                "Low": int(low_count or 0),
                "Weak": int(weak_count or 0),
            }
        return metrics

    async def _run_counts(self, run_id: UUID) -> dict[str, int]:
        usage_result = await self.session.execute(
            select(
                func.count(ResearchRunSourceUsage.id),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                ResearchRunSourceUsage.status
                                == ResearchRunSourceUsageStatus.USED,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                ResearchRunSourceUsage.status
                                == ResearchRunSourceUsageStatus.FAILED,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                ResearchRunSourceUsage.status
                                == ResearchRunSourceUsageStatus.SKIPPED_DISABLED,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(func.sum(ResearchRunSourceUsage.documents_found), 0),
                func.coalesce(func.sum(ResearchRunSourceUsage.documents_used), 0),
            ).where(ResearchRunSourceUsage.research_run_id == run_id)
        )
        row = usage_result.one()
        return {
            "enabled_source_count": int(row[0] or 0),
            "successful_source_count": int(row[1] or 0),
            "failed_source_count": int(row[2] or 0),
            "skipped_source_count": int(row[3] or 0),
            "total_documents_found": int(row[4] or 0),
            "total_documents_used": int(row[5] or 0),
        }

    async def _default_source(self) -> ResearchSource:
        await self.source_service.ensure_defaults()
        sources = await self.source_service.list_enabled_sources(ResearchSourceCategory.DISCOVERY)
        if not sources:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No research source is available for evidence persistence",
            )
        return sources[0]

    async def _run(self, run_id: UUID) -> ResearchRun:
        run = await self.session.get(ResearchRun, run_id)
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Research run not found",
            )
        return run

    async def _document(self, document_id: UUID) -> ResearchDocument:
        document = await self.session.get(ResearchDocument, document_id)
        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Research document not found",
            )
        return document

    async def _count(self, statement) -> int:
        result = await self.session.execute(select(func.count()).select_from(statement.subquery()))
        return int(result.scalar_one() or 0)

    def _run_statement(
        self,
        *,
        search: str | None,
        status_filter: ResearchRunStatus | None,
        run_type: ResearchRunType | None,
        series_id: UUID | None,
        episode_id: UUID | None,
        strategy_run_id: UUID | None,
        source_id: UUID | None,
    ):
        statement = select(ResearchRun)
        if status_filter is not None:
            statement = statement.where(ResearchRun.status == status_filter)
        if run_type is not None:
            statement = statement.where(ResearchRun.run_type == run_type)
        if series_id is not None:
            statement = statement.where(ResearchRun.series_id == series_id)
        if episode_id is not None:
            statement = statement.where(ResearchRun.episode_id == episode_id)
        if strategy_run_id is not None:
            statement = statement.where(ResearchRun.strategy_run_id == strategy_run_id)
        if source_id is not None:
            statement = statement.where(
                ResearchRun.id.in_(
                    select(ResearchRunSourceUsage.research_run_id).where(
                        ResearchRunSourceUsage.source_id == source_id
                    )
                )
            )
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    ResearchRun.query_text.ilike(pattern),
                    ResearchRun.failure_reason.ilike(pattern),
                )
            )
        return statement

    def _run_order_by(self, sort: str):
        return {
            "created_at": (ResearchRun.created_at.asc(), ResearchRun.id.asc()),
            "-created_at": (ResearchRun.created_at.desc(), ResearchRun.id.desc()),
            "started_at": (ResearchRun.started_at.asc().nullslast(), ResearchRun.id.asc()),
            "-started_at": (ResearchRun.started_at.desc().nullslast(), ResearchRun.id.desc()),
            "duration_ms": (ResearchRun.duration_ms.asc().nullslast(), ResearchRun.id.asc()),
            "-duration_ms": (ResearchRun.duration_ms.desc().nullslast(), ResearchRun.id.desc()),
            "status": (ResearchRun.status.asc(), ResearchRun.created_at.desc()),
            "-status": (ResearchRun.status.desc(), ResearchRun.created_at.desc()),
        }.get(sort, (ResearchRun.created_at.desc(), ResearchRun.id.desc()))

    def _document_order_by(self, sort: str):
        return {
            "created_at": (ResearchDocument.created_at.asc(), ResearchDocument.id.asc()),
            "-created_at": (ResearchDocument.created_at.desc(), ResearchDocument.id.desc()),
            "published_at": (
                ResearchDocument.published_at.asc().nullslast(),
                ResearchDocument.created_at.desc(),
            ),
            "-published_at": (
                ResearchDocument.published_at.desc().nullslast(),
                ResearchDocument.created_at.desc(),
            ),
            "title": (ResearchDocument.title.asc(), ResearchDocument.created_at.desc()),
            "-title": (ResearchDocument.title.desc(), ResearchDocument.created_at.desc()),
        }.get(sort, (ResearchDocument.created_at.desc(), ResearchDocument.id.desc()))

    def _ledger_order_by(self, sort: str):
        return {
            "created_at": (DiscoveryLedgerEntry.created_at.asc(), DiscoveryLedgerEntry.id.asc()),
            "-created_at": (DiscoveryLedgerEntry.created_at.desc(), DiscoveryLedgerEntry.id.desc()),
            "ledger_type": (
                DiscoveryLedgerEntry.ledger_type.asc(),
                DiscoveryLedgerEntry.created_at.desc(),
            ),
            "-ledger_type": (
                DiscoveryLedgerEntry.ledger_type.desc(),
                DiscoveryLedgerEntry.created_at.desc(),
            ),
        }.get(sort, (DiscoveryLedgerEntry.created_at.desc(), DiscoveryLedgerEntry.id.desc()))

    def _usage_order_by(self, sort: str):
        return {
            "created_at": (
                ResearchRunSourceUsage.created_at.asc(),
                ResearchRunSourceUsage.id.asc(),
            ),
            "-created_at": (
                ResearchRunSourceUsage.created_at.desc(),
                ResearchRunSourceUsage.id.desc(),
            ),
            "started_at": (
                ResearchRunSourceUsage.started_at.asc().nullslast(),
                ResearchRunSourceUsage.id.asc(),
            ),
            "-started_at": (
                ResearchRunSourceUsage.started_at.desc().nullslast(),
                ResearchRunSourceUsage.id.desc(),
            ),
            "latency_ms": (
                ResearchRunSourceUsage.latency_ms.asc(),
                ResearchRunSourceUsage.created_at.desc(),
            ),
            "-latency_ms": (
                ResearchRunSourceUsage.latency_ms.desc(),
                ResearchRunSourceUsage.created_at.desc(),
            ),
        }.get(sort, (ResearchRunSourceUsage.created_at.desc(), ResearchRunSourceUsage.id.desc()))

    def _run_payload(self, run: ResearchRun) -> dict[str, object]:
        return {
            "id": run.id,
            "run_type": run.run_type,
            "status": run.status,
            "query_text": run.query_text,
            "series_id": run.series_id,
            "episode_id": run.episode_id,
            "strategy_run_id": run.strategy_run_id,
            "agent_run_id": run.agent_run_id,
            "mcp_tool_run_id": run.mcp_tool_run_id,
            "initiated_by_user_id": run.initiated_by_user_id,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "duration_ms": run.duration_ms,
            "failure_reason": run.failure_reason,
            "enabled_source_count": run.enabled_source_count,
            "successful_source_count": run.successful_source_count,
            "failed_source_count": run.failed_source_count,
            "skipped_source_count": run.skipped_source_count,
            "total_documents_found": run.total_documents_found,
            "total_documents_used": run.total_documents_used,
            "metadata_json": run.metadata_json or {},
            "created_at": run.created_at,
            "updated_at": run.updated_at,
        }

    def _source_usage_payload(
        self,
        usage: ResearchRunSourceUsage,
        source: ResearchSource,
    ) -> dict[str, object]:
        return {
            "id": usage.id,
            "research_run_id": usage.research_run_id,
            "source_id": usage.source_id,
            "source_key": source.key,
            "source_name": source.name,
            "provider_type": source.provider_type,
            "status": usage.status,
            "query_text": usage.query_text,
            "documents_found": usage.documents_found,
            "documents_used": usage.documents_used,
            "latency_ms": usage.latency_ms,
            "failure_reason": usage.failure_reason,
            "started_at": usage.started_at,
            "completed_at": usage.completed_at,
            "created_at": usage.created_at,
        }

    def _document_payload(
        self,
        document: ResearchDocument,
        source: ResearchSource,
    ) -> dict[str, object]:
        return {
            "id": document.id,
            "research_run_id": document.research_run_id,
            "source_id": document.source_id,
            "source_key": source.key,
            "source_name": source.name,
            "provider_type": document.provider_type,
            "external_resource_id": document.external_resource_id,
            "title": document.title,
            "url": document.url,
            "author": document.author,
            "published_at": document.published_at,
            "fetched_at": document.fetched_at,
            "resource_type": document.resource_type,
            "content_excerpt": document.content_excerpt,
            "normalized_content": document.normalized_content,
            "raw_metadata_json": document.raw_metadata_json or {},
            "tier": document.tier,
            "tier_score": document.tier_score,
            "engagement_score": document.engagement_score,
            "freshness_score": document.freshness_score,
            "author_score": document.author_score,
            "composite_score": document.composite_score,
            "trend_score": document.trend_score,
            "trend_available": document.trend_available,
            "trend_source": document.trend_source,
            "trend_failure_reason": document.trend_failure_reason,
            "confidence_level": document.confidence_level,
            "score_explanation_json": document.score_explanation_json or {},
            "used_in_output": document.used_in_output,
            "archived": document.archived,
            "created_at": document.created_at,
        }

    def _ledger_payload(
        self,
        entry: DiscoveryLedgerEntry,
        source: ResearchSource,
        document: ResearchDocument | None,
    ) -> dict[str, object]:
        return {
            "id": entry.id,
            "research_run_id": entry.research_run_id,
            "document_id": entry.document_id,
            "source_id": entry.source_id,
            "source_key": source.key,
            "source_name": source.name,
            "provider_type": source.provider_type,
            "document_title": document.title if document else None,
            "document_url": document.url if document else None,
            "document_tier": document.tier if document else None,
            "document_tier_score": document.tier_score if document else None,
            "document_engagement_score": document.engagement_score if document else None,
            "document_freshness_score": document.freshness_score if document else None,
            "document_author_score": document.author_score if document else None,
            "document_composite_score": document.composite_score if document else None,
            "document_confidence_level": document.confidence_level if document else None,
            "document_trend_score": document.trend_score if document else None,
            "document_trend_available": document.trend_available if document else None,
            "document_score_explanation_json": (
                document.score_explanation_json if document else None
            ),
            "series_id": entry.series_id,
            "episode_id": entry.episode_id,
            "strategy_idea_id": entry.strategy_idea_id,
            "ledger_type": entry.ledger_type,
            "evidence_summary": entry.evidence_summary,
            "created_at": entry.created_at,
        }

    def _title(self, document: Mapping[str, object]) -> str:
        return str(document.get("title") or document.get("name") or "Untitled research document")[
            :500
        ]

    def _resource_type(self, document: Mapping[str, object]) -> str:
        metadata = document.get("metadata")
        if isinstance(metadata, Mapping) and metadata.get("resource_type"):
            return str(metadata["resource_type"])[:80]
        return str(document.get("resource_type") or "document")[:80]

    def _excerpt(self, document: Mapping[str, object]) -> str | None:
        content = self._optional_str(document.get("snippet")) or self._optional_str(
            document.get("content")
        )
        return content[:1000] if content else None

    def _normalized_content(self, document: Mapping[str, object]) -> str | None:
        content = self._optional_str(document.get("content")) or self._optional_str(
            document.get("snippet")
        )
        return content[:12000] if content else None

    def _evidence_summary(self, document: ResearchDocument) -> str:
        if document.content_excerpt:
            return document.content_excerpt[:500]
        return f"{document.title} from persisted research evidence."

    def _optional_str(self, value: object) -> str | None:
        if value in (None, ""):
            return None
        return str(value)

    def _parse_datetime(self, value: object) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        try:
            raw = str(value)
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            parsed = datetime.fromisoformat(raw)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return None
