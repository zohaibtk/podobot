from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.db.types import (
    DiscoveryLedgerType,
    ResearchRunSourceUsageStatus,
    ResearchRunStatus,
    ResearchRunType,
    ResearchScoreEntityType,
)
from app.modules.research.schemas import (
    DiscoveryLedgerListResponse,
    ResearchActionResponse,
    ResearchDocumentListResponse,
    ResearchDocumentScoreResponse,
    ResearchRunDetailResponse,
    ResearchRunListResponse,
    ResearchRunSourceUsageListResponse,
    ResearchScoreBreakdownResponse,
    ResearchScoreExplainRequest,
    ResearchScoreExplanationResponse,
    ResearchScoreRunActionResponse,
    ResearchScoreSummaryResponse,
)
from app.modules.research.scoring import ResearchScoringService
from app.modules.research.service import ResearchPersistenceService
from app.security.auth import require_permission

router = APIRouter(prefix="/research", tags=["research"])


def get_research_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResearchPersistenceService:
    return ResearchPersistenceService(session)


def get_research_scoring_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResearchScoringService:
    return ResearchScoringService(session)


ResearchServiceDep = Annotated[ResearchPersistenceService, Depends(get_research_service)]
ResearchScoringServiceDep = Annotated[
    ResearchScoringService,
    Depends(get_research_scoring_service),
]
RequireResearchView = Depends(require_permission("research.view"))
RequireResearchManage = Depends(require_permission("research.manage"))


@router.get("/runs", response_model=ResearchRunListResponse)
async def list_research_runs(
    service: ResearchServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
    search: Annotated[str | None, Query(max_length=240)] = None,
    sort: Annotated[str, Query(max_length=40)] = "-created_at",
    status_filter: Annotated[ResearchRunStatus | None, Query(alias="status")] = None,
    run_type: ResearchRunType | None = None,
    series_id: UUID | None = None,
    episode_id: UUID | None = None,
    strategy_run_id: UUID | None = None,
    source_id: UUID | None = None,
    _current_user=RequireResearchView,
) -> ResearchRunListResponse:
    return ResearchRunListResponse(
        **await service.list_runs(
            page=page,
            page_size=page_size,
            search=search,
            sort=sort,
            status_filter=status_filter,
            run_type=run_type,
            series_id=series_id,
            episode_id=episode_id,
            strategy_run_id=strategy_run_id,
            source_id=source_id,
        )
    )


@router.get("/runs/{run_id}", response_model=ResearchRunDetailResponse)
async def get_research_run(
    run_id: UUID,
    service: ResearchServiceDep,
    _current_user=RequireResearchView,
) -> ResearchRunDetailResponse:
    return ResearchRunDetailResponse(**await service.get_run_detail(run_id))


@router.get("/runs/{run_id}/score-summary", response_model=ResearchScoreSummaryResponse)
async def get_research_run_score_summary(
    run_id: UUID,
    service: ResearchScoringServiceDep,
    _current_user=RequireResearchView,
) -> ResearchScoreSummaryResponse:
    return ResearchScoreSummaryResponse(**await service.run_score_summary(run_id))


@router.post("/runs/{run_id}/score-documents", response_model=ResearchScoreRunActionResponse)
async def score_research_run_documents(
    run_id: UUID,
    service: ResearchScoringServiceDep,
    _current_user=RequireResearchManage,
) -> ResearchScoreRunActionResponse:
    return ResearchScoreRunActionResponse(**await service.score_run_documents(run_id))


@router.post("/runs/{run_id}/retry", response_model=ResearchActionResponse)
async def retry_research_run(
    run_id: UUID,
    service: ResearchServiceDep,
    _current_user=RequireResearchManage,
) -> ResearchActionResponse:
    return ResearchActionResponse(**await service.retry_run(run_id))


@router.post("/runs/clear-failed", response_model=ResearchActionResponse)
async def clear_failed_research_runs(
    service: ResearchServiceDep,
    _current_user=RequireResearchManage,
) -> ResearchActionResponse:
    return ResearchActionResponse(**await service.clear_failed_runs())


@router.get("/documents", response_model=ResearchDocumentListResponse)
async def list_research_documents(
    service: ResearchServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
    search: Annotated[str | None, Query(max_length=240)] = None,
    sort: Annotated[str, Query(max_length=40)] = "-created_at",
    research_run_id: UUID | None = None,
    source_id: UUID | None = None,
    series_id: UUID | None = None,
    episode_id: UUID | None = None,
    archived: bool | None = None,
    _current_user=RequireResearchView,
) -> ResearchDocumentListResponse:
    return ResearchDocumentListResponse(
        **await service.list_documents(
            page=page,
            page_size=page_size,
            search=search,
            sort=sort,
            research_run_id=research_run_id,
            source_id=source_id,
            series_id=series_id,
            episode_id=episode_id,
            archived=archived,
        )
    )


@router.get("/documents/{document_id}/score", response_model=ResearchDocumentScoreResponse)
async def get_research_document_score(
    document_id: UUID,
    service: ResearchScoringServiceDep,
    _current_user=RequireResearchView,
) -> ResearchDocumentScoreResponse:
    return ResearchDocumentScoreResponse(**await service.get_document_score(document_id))


@router.post("/documents/{document_id}/rescore", response_model=ResearchDocumentScoreResponse)
async def rescore_research_document(
    document_id: UUID,
    service: ResearchScoringServiceDep,
    _current_user=RequireResearchManage,
) -> ResearchDocumentScoreResponse:
    return ResearchDocumentScoreResponse(**await service.score_document(document_id))


@router.post("/documents/{document_id}/archive", response_model=ResearchActionResponse)
async def archive_research_document(
    document_id: UUID,
    service: ResearchServiceDep,
    _current_user=RequireResearchManage,
) -> ResearchActionResponse:
    return ResearchActionResponse(**await service.archive_document(document_id))


@router.post("/score/explain", response_model=ResearchScoreExplanationResponse)
async def explain_research_score(
    payload: ResearchScoreExplainRequest,
    service: ResearchScoringServiceDep,
    _current_user=RequireResearchView,
) -> ResearchScoreExplanationResponse:
    return ResearchScoreExplanationResponse(
        **await service.explain_score(payload.model_dump())
    )


@router.get(
    "/entities/{entity_type}/{entity_id}/score-breakdown",
    response_model=ResearchScoreBreakdownResponse,
)
async def get_research_entity_score_breakdown(
    entity_type: ResearchScoreEntityType,
    entity_id: UUID,
    service: ResearchScoringServiceDep,
    _current_user=RequireResearchView,
) -> ResearchScoreBreakdownResponse:
    return ResearchScoreBreakdownResponse(
        **await service.entity_score_breakdown(entity_type, entity_id)
    )


@router.get("/ledger", response_model=DiscoveryLedgerListResponse)
async def list_discovery_ledger_entries(
    service: ResearchServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
    search: Annotated[str | None, Query(max_length=240)] = None,
    sort: Annotated[str, Query(max_length=40)] = "-created_at",
    research_run_id: UUID | None = None,
    source_id: UUID | None = None,
    series_id: UUID | None = None,
    episode_id: UUID | None = None,
    strategy_idea_id: UUID | None = None,
    ledger_type: DiscoveryLedgerType | None = None,
    _current_user=RequireResearchView,
) -> DiscoveryLedgerListResponse:
    return DiscoveryLedgerListResponse(
        **await service.list_ledger_entries(
            page=page,
            page_size=page_size,
            search=search,
            sort=sort,
            research_run_id=research_run_id,
            source_id=source_id,
            series_id=series_id,
            episode_id=episode_id,
            strategy_idea_id=strategy_idea_id,
            ledger_type=ledger_type,
        )
    )


@router.get("/source-usage", response_model=ResearchRunSourceUsageListResponse)
async def list_research_source_usage(
    service: ResearchServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
    search: Annotated[str | None, Query(max_length=240)] = None,
    sort: Annotated[str, Query(max_length=40)] = "-created_at",
    research_run_id: UUID | None = None,
    source_id: UUID | None = None,
    status_filter: Annotated[
        ResearchRunSourceUsageStatus | None,
        Query(alias="status"),
    ] = None,
    _current_user=RequireResearchView,
) -> ResearchRunSourceUsageListResponse:
    return ResearchRunSourceUsageListResponse(
        **await service.list_source_usage(
            page=page,
            page_size=page_size,
            search=search,
            sort=sort,
            research_run_id=research_run_id,
            source_id=source_id,
            status_filter=status_filter,
        )
    )
