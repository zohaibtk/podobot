from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.db.types import StrategyIdeaStatus
from app.modules.strategy.schemas import (
    StrategyIdeaActionResponse,
    StrategyIdeaListResponse,
    StrategyRunListResponse,
    StrategyWorkspaceResponse,
    StrategyWorkspaceSummaryResponse,
)
from app.modules.strategy.service import StrategyService
from app.security.auth import require_permission

router = APIRouter(prefix="/strategy", tags=["strategy"])


def get_strategy_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StrategyService:
    return StrategyService(session)


StrategyServiceDep = Annotated[StrategyService, Depends(get_strategy_service)]
RequireStrategyView = Depends(require_permission("strategy.view"))
RequireStrategyConvert = Depends(require_permission("strategy.convert"))


@router.get("", response_model=StrategyWorkspaceResponse)
async def get_strategy_workspace(
    service: StrategyServiceDep,
    _current_user=RequireStrategyView,
):
    return await service.get_workspace()


@router.get("/summary", response_model=StrategyWorkspaceSummaryResponse)
async def get_strategy_summary(
    service: StrategyServiceDep,
    range_value: Annotated[
        str,
        Query(alias="range", pattern="^(today|7d|30d|90d|all)$"),
    ] = "30d",
    _current_user=RequireStrategyView,
):
    return await service.get_summary(range_value=range_value)


@router.get("/runs", response_model=StrategyRunListResponse)
async def list_strategy_runs(
    service: StrategyServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
    _current_user=RequireStrategyView,
):
    return StrategyRunListResponse(
        **await service.list_runs_page(limit=limit, cursor=cursor)
    )


@router.get("/ideas", response_model=StrategyIdeaListResponse)
async def list_strategy_ideas(
    service: StrategyServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
    status_filter: Annotated[StrategyIdeaStatus | None, Query(alias="status")] = None,
    run_id: UUID | None = None,
    query: Annotated[str | None, Query(max_length=240)] = None,
    _current_user=RequireStrategyView,
):
    return StrategyIdeaListResponse(
        **await service.list_ideas_page(
            limit=limit,
            cursor=cursor,
            status_filter=status_filter,
            run_id=run_id,
            query=query,
        )
    )


@router.post("/runs", response_model=StrategyWorkspaceResponse)
async def create_strategy_run(
    service: StrategyServiceDep,
    _current_user=RequireStrategyView,
):
    return await service.create_research_run()


@router.post("/ideas/{idea_id}/review", response_model=StrategyIdeaActionResponse)
async def review_strategy_idea(
    idea_id: UUID,
    service: StrategyServiceDep,
    _current_user=RequireStrategyView,
):
    return await service.review_idea(idea_id)


@router.post("/ideas/{idea_id}/dismiss", response_model=StrategyIdeaActionResponse)
async def dismiss_strategy_idea(
    idea_id: UUID,
    service: StrategyServiceDep,
    _current_user=RequireStrategyView,
):
    return await service.dismiss_idea(idea_id)


@router.post("/ideas/{idea_id}/restore", response_model=StrategyIdeaActionResponse)
async def restore_strategy_idea(
    idea_id: UUID,
    service: StrategyServiceDep,
    _current_user=RequireStrategyView,
):
    return await service.restore_idea(idea_id)


@router.post("/ideas/{idea_id}/convert", response_model=StrategyIdeaActionResponse)
async def convert_strategy_idea(
    idea_id: UUID,
    service: StrategyServiceDep,
    _current_user=RequireStrategyConvert,
):
    return await service.convert_idea(idea_id)
