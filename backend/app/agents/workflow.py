from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.service import AgentExecutionService


async def record_workflow_agent_run(
    session: AsyncSession,
    *,
    agent_key: str,
    entity_type: str,
    entity_id: UUID,
    workflow_stage: str,
    trigger: str,
    input_payload: dict[str, object] | None = None,
    output_payload: dict[str, object] | None = None,
    error_reason: str | None = None,
    regeneration_reason: str | None = None,
) -> None:
    await AgentExecutionService(session).record_workflow_run(
        agent_key=agent_key,
        entity_type=entity_type,
        entity_id=entity_id,
        workflow_stage=workflow_stage,
        trigger=trigger,
        input_payload=input_payload,
        output_payload=output_payload,
        error_reason=error_reason,
        regeneration_reason=regeneration_reason,
    )
