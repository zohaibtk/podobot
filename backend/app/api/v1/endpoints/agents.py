from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import (
    AgentListResponse,
    AgentResponse,
    AgentRunDetailResponse,
    AgentRunListResponse,
    AgentRunRequest,
    AgentRunRetryRequest,
    AgentTokenStatsPeriod,
    AgentTokenStatsResponse,
    PromptListResponse,
    PromptTemplateResponse,
    PromptVersionCreateRequest,
    PromptVersionResponse,
)
from app.agents.service import AgentExecutionService
from app.db.session import get_db_session
from app.security.auth import CurrentUserDep, require_permission

router = APIRouter(tags=["agents"])


def get_agent_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AgentExecutionService:
    return AgentExecutionService(session)


AgentServiceDep = Annotated[AgentExecutionService, Depends(get_agent_service)]
RequireSeriesView = Depends(require_permission("series.view"))
RequireSettingsManage = Depends(require_permission("settings.manage"))


@router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    service: AgentServiceDep,
    _current_user: CurrentUserDep,
):
    return AgentListResponse(items=await service.list_agents())


@router.get("/agents/runs", response_model=AgentRunListResponse)
async def list_agent_runs(
    service: AgentServiceDep,
    _current_user: CurrentUserDep,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    agent_key: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
):
    response = await service.list_runs(
        entity_type=entity_type,
        entity_id=entity_id,
        agent_key=agent_key,
        limit=limit,
        cursor=cursor,
    )
    if isinstance(response, dict):
        return AgentRunListResponse(**response)
    return AgentRunListResponse(items=response)


@router.get("/agents/token-stats", response_model=AgentTokenStatsResponse)
async def get_agent_token_stats(
    service: AgentServiceDep,
    _current_user: CurrentUserDep,
    period: AgentTokenStatsPeriod = "day",
):
    return AgentTokenStatsResponse(**await service.token_stats(period))


@router.get("/agents/runs/{run_id}", response_model=AgentRunDetailResponse)
async def get_agent_run(
    run_id: UUID,
    service: AgentServiceDep,
    _current_user: CurrentUserDep,
):
    return await service.get_run_detail(run_id)


@router.post("/agents/runs/{run_id}/retry", response_model=AgentRunDetailResponse)
async def retry_agent_run(
    run_id: UUID,
    payload: AgentRunRetryRequest,
    service: AgentServiceDep,
    current_user: CurrentUserDep,
):
    return await service.retry_run(run_id, payload, current_user)


@router.get("/agents/{agent_key}", response_model=AgentResponse)
async def get_agent(
    agent_key: str,
    service: AgentServiceDep,
    _current_user: CurrentUserDep,
):
    return await service.get_agent(agent_key)


@router.post(
    "/agents/{agent_key}/run",
    response_model=AgentRunDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_agent(
    agent_key: str,
    payload: AgentRunRequest,
    service: AgentServiceDep,
    current_user: CurrentUserDep,
):
    return await service.run_agent(agent_key, payload, current_user)


@router.get("/prompts", response_model=PromptListResponse)
async def list_prompts(
    service: AgentServiceDep,
    _current_user: CurrentUserDep,
):
    return PromptListResponse(items=await service.list_prompts())


@router.get("/prompts/{prompt_key}", response_model=PromptTemplateResponse)
async def get_prompt(
    prompt_key: str,
    service: AgentServiceDep,
    _current_user: CurrentUserDep,
):
    return await service.get_prompt(prompt_key)


@router.post(
    "/prompts/{prompt_key}/versions",
    response_model=PromptVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt_version(
    prompt_key: str,
    payload: PromptVersionCreateRequest,
    service: AgentServiceDep,
    _current_user=RequireSettingsManage,
):
    return await service.create_prompt_version(prompt_key, payload)


@router.get(
    "/workflow/{entity_type}/{entity_id}/agent-history",
    response_model=AgentRunListResponse,
)
async def get_workflow_agent_history(
    entity_type: str,
    entity_id: UUID,
    service: AgentServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
    _current_user=RequireSeriesView,
):
    response = await service.list_runs(
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        cursor=cursor,
    )
    if isinstance(response, dict):
        return AgentRunListResponse(**response)
    return AgentRunListResponse(items=response)
