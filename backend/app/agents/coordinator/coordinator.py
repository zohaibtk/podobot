from pydantic import BaseModel, Field

from app.agents.base import AgentContext, AgentResult, BaseAgent


class CoordinationInput(BaseModel):
    requested_action: str
    entity_ref: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class CoordinationOutput(BaseModel):
    accepted: bool
    next_step: str | None = None
    requires_human: bool = False


class CoordinatorAgent(BaseAgent[CoordinationInput, CoordinationOutput]):
    agent_id = "coordinator"

    async def run(
        self,
        input_data: CoordinationInput,
        context: AgentContext,
    ) -> AgentResult[CoordinationOutput]:
        return AgentResult(
            output=CoordinationOutput(
                accepted=True,
                next_step=input_data.requested_action,
                requires_human=False,
            ),
            audit_notes=[f"Foundation coordinator accepted {context.correlation_id}"],
        )
