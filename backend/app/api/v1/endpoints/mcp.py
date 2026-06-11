from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.mcp.schemas.runtime import (
    MCPServerListResponse,
    MCPServerResponse,
    MCPServerTestResponse,
    MCPToolListResponse,
    MCPToolResponse,
    MCPToolRunDetailResponse,
    MCPToolRunListResponse,
    MCPToolRunRequest,
    MCPToolRunResponse,
    MCPToolRunRetryRequest,
)
from app.mcp.service import MCPToolExecutionService
from app.security.auth import CurrentUserDep, require_permission

router = APIRouter(tags=["mcp"])


def get_mcp_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MCPToolExecutionService:
    return MCPToolExecutionService(session)


MCPServiceDep = Annotated[MCPToolExecutionService, Depends(get_mcp_service)]
RequireIntegrationManage = Depends(require_permission("integration.manage"))


@router.get("/mcp/servers", response_model=MCPServerListResponse)
async def list_mcp_servers(
    service: MCPServiceDep,
    _current_user=RequireIntegrationManage,
):
    return MCPServerListResponse(items=await service.list_servers())


@router.get("/mcp/servers/{server_key}", response_model=MCPServerResponse)
async def get_mcp_server(
    server_key: str,
    service: MCPServiceDep,
    _current_user=RequireIntegrationManage,
):
    return await service.get_server(server_key)


@router.post("/mcp/servers/{server_key}/test", response_model=MCPServerTestResponse)
async def test_mcp_server(
    server_key: str,
    service: MCPServiceDep,
    current_user: CurrentUserDep,
):
    return await service.test_server(server_key, current_user)


@router.get("/mcp/tools", response_model=MCPToolListResponse)
async def list_mcp_tools(
    service: MCPServiceDep,
    server_key: str | None = None,
    _current_user=RequireIntegrationManage,
):
    return MCPToolListResponse(items=await service.list_tools(server_key=server_key))


@router.get("/mcp/tools/{tool_key}", response_model=MCPToolResponse)
async def get_mcp_tool(
    tool_key: str,
    service: MCPServiceDep,
    _current_user=RequireIntegrationManage,
):
    return await service.get_tool(tool_key)


@router.post(
    "/mcp/tools/{tool_key}/run",
    response_model=MCPToolRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_mcp_tool(
    tool_key: str,
    payload: MCPToolRunRequest,
    service: MCPServiceDep,
    current_user: CurrentUserDep,
):
    return await service.execute_tool(tool_key, payload, current_user=current_user)


@router.get("/mcp/runs", response_model=MCPToolRunListResponse)
async def list_mcp_runs(
    service: MCPServiceDep,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    tool_key: str | None = None,
    server_key: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
    _current_user=RequireIntegrationManage,
):
    response = await service.list_runs(
        entity_type=entity_type,
        entity_id=entity_id,
        tool_key=tool_key,
        server_key=server_key,
        limit=limit,
        cursor=cursor,
    )
    if isinstance(response, dict):
        return MCPToolRunListResponse(**response)
    return MCPToolRunListResponse(items=response)


@router.get("/mcp/runs/{run_id}", response_model=MCPToolRunDetailResponse)
async def get_mcp_run(
    run_id: UUID,
    service: MCPServiceDep,
    _current_user=RequireIntegrationManage,
):
    return await service.get_run_detail(run_id)


@router.post("/mcp/runs/{run_id}/retry", response_model=MCPToolRunResponse)
async def retry_mcp_run(
    run_id: UUID,
    payload: MCPToolRunRetryRequest,
    service: MCPServiceDep,
    current_user: CurrentUserDep,
):
    return await service.retry_run(run_id, payload, current_user)


@router.get(
    "/workflow/{entity_type}/{entity_id}/mcp-history",
    response_model=MCPToolRunListResponse,
)
async def get_workflow_mcp_history(
    entity_type: str,
    entity_id: UUID,
    service: MCPServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
    _current_user=RequireIntegrationManage,
):
    response = await service.list_runs(
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        cursor=cursor,
    )
    if isinstance(response, dict):
        return MCPToolRunListResponse(**response)
    return MCPToolRunListResponse(items=response)
