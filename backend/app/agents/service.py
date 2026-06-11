import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.defaults import DEFAULT_AGENTS, DEFAULT_PROMPTS
from app.agents.llm.base import BaseLLMProvider, LLMRequest
from app.agents.llm.database import DatabaseGeminiLLMProvider
from app.agents.llm.unavailable import UnavailableLLMProvider
from app.agents.models import (
    Agent,
    AgentAuditLog,
    AgentOutputValidationResult,
    AgentRun,
    PromptTemplate,
    PromptVersion,
)
from app.agents.schemas import (
    AgentRunRequest,
    AgentRunRetryRequest,
    AgentTokenStatsPeriod,
    PromptVersionCreateRequest,
)
from app.agents.validation import validate_agent_output
from app.db.types import AgentRunStatus, PromptVersionStatus
from app.mcp.service import MCPToolExecutionService
from app.modules.series.models import Series
from app.schemas.pagination import cursor_meta, decode_cursor, encode_cursor
from app.security.auth import CurrentUser


def default_llm_provider(session: AsyncSession) -> BaseLLMProvider:
    if session is None:
        return UnavailableLLMProvider()
    return DatabaseGeminiLLMProvider(session)


class AgentRegistryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_defaults(self, *, commit: bool = True) -> None:
        changed = False
        agents_by_key = await self._agents_by_key()
        for default_agent in DEFAULT_AGENTS:
            agent = agents_by_key.get(default_agent.key)
            if agent is None:
                self.session.add(
                    Agent(
                        key=default_agent.key,
                        name=default_agent.name,
                        responsibility=default_agent.responsibility,
                        tools=default_agent.tools,
                        required_permission=default_agent.required_permission,
                        is_enabled=True,
                    )
                )
                changed = True
            else:
                agent.name = default_agent.name
                agent.responsibility = default_agent.responsibility
                agent.tools = default_agent.tools
                agent.required_permission = default_agent.required_permission
                changed = True

        if changed:
            await self.session.flush()

        agents_by_key = await self._agents_by_key()
        templates_by_key = await self._prompt_templates_by_key()
        for default_prompt in DEFAULT_PROMPTS:
            agent = agents_by_key[default_prompt.agent_key]
            template = templates_by_key.get(default_prompt.key)
            if template is None:
                template = PromptTemplate(
                    key=default_prompt.key,
                    agent_id=agent.id,
                    name=default_prompt.name,
                    description=default_prompt.description,
                    created_by="system",
                )
                self.session.add(template)
                await self.session.flush()
                templates_by_key[default_prompt.key] = template
                changed = True

            active = await self.active_prompt_version(default_prompt.key, missing_ok=True)
            if active is None:
                self.session.add(
                    PromptVersion(
                        prompt_template_id=template.id,
                        agent_id=agent.id,
                        prompt_key=default_prompt.key,
                        agent_key=agent.key,
                        version_number=1,
                        template_body=default_prompt.template_body,
                        input_schema=default_prompt.input_schema,
                        output_schema=default_prompt.output_schema,
                        status=PromptVersionStatus.ACTIVE,
                        created_by="system",
                    )
                )
                changed = True

        if changed and commit:
            await self.session.commit()
        elif changed:
            await self.session.flush()

    async def list_agents(self) -> list[Agent]:
        await self.ensure_defaults()
        result = await self.session.execute(select(Agent).order_by(Agent.name.asc()))
        return list(result.scalars().all())

    async def get_agent(self, agent_key: str) -> Agent:
        await self.ensure_defaults()
        agent = await self._agent_by_key(agent_key)
        if agent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        return agent

    async def list_prompts(self) -> list[dict[str, object]]:
        await self.ensure_defaults()
        templates = await self._prompt_templates()
        versions = await self._prompt_versions()
        agents = {agent.id: agent for agent in await self.list_agents()}
        versions_by_template: dict[UUID, list[PromptVersion]] = {}
        for version in versions:
            versions_by_template.setdefault(version.prompt_template_id, []).append(version)
        return [
            self._prompt_payload(
                template,
                agents.get(template.agent_id),
                versions_by_template.get(template.id, []),
            )
            for template in templates
        ]

    async def get_prompt(self, prompt_key: str) -> dict[str, object]:
        await self.ensure_defaults()
        template = await self._prompt_template_by_key(prompt_key)
        if template is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        versions = await self._prompt_versions(template.id)
        agent = await self.session.get(Agent, template.agent_id)
        return self._prompt_payload(template, agent, versions)

    async def create_prompt_version(
        self,
        prompt_key: str,
        payload: PromptVersionCreateRequest,
    ) -> PromptVersion:
        await self.ensure_defaults()
        template = await self._prompt_template_by_key(prompt_key)
        if template is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        agent = await self.session.get(Agent, template.agent_id)
        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Prompt agent was not initialized",
            )
        next_version = await self._next_prompt_version_number(template.id)
        if payload.status == PromptVersionStatus.ACTIVE:
            await self.session.execute(
                update(PromptVersion)
                .where(
                    PromptVersion.prompt_key == prompt_key,
                    PromptVersion.status == PromptVersionStatus.ACTIVE,
                )
                .values(status=PromptVersionStatus.ARCHIVED)
            )
        version = PromptVersion(
            prompt_template_id=template.id,
            agent_id=agent.id,
            prompt_key=template.key,
            agent_key=agent.key,
            version_number=next_version,
            template_body=payload.template_body,
            input_schema=payload.input_schema,
            output_schema=payload.output_schema,
            status=payload.status,
            created_by=payload.created_by,
        )
        self.session.add(version)
        await self.session.commit()
        await self.session.refresh(version)
        return version

    async def active_prompt_version(
        self,
        prompt_key: str,
        *,
        missing_ok: bool = False,
    ) -> PromptVersion | None:
        result = await self.session.execute(
            select(PromptVersion).where(
                PromptVersion.prompt_key == prompt_key,
                PromptVersion.status == PromptVersionStatus.ACTIVE,
            )
        )
        version = result.scalar_one_or_none()
        if version is None and not missing_ok:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active prompt version not found",
            )
        return version

    async def _agent_by_key(self, agent_key: str) -> Agent | None:
        result = await self.session.execute(select(Agent).where(Agent.key == agent_key))
        return result.scalar_one_or_none()

    async def _agents_by_key(self) -> dict[str, Agent]:
        result = await self.session.execute(select(Agent))
        return {agent.key: agent for agent in result.scalars().all()}

    async def _prompt_templates(self) -> list[PromptTemplate]:
        result = await self.session.execute(
            select(PromptTemplate).order_by(PromptTemplate.key.asc())
        )
        return list(result.scalars().all())

    async def _prompt_template_by_key(self, prompt_key: str) -> PromptTemplate | None:
        result = await self.session.execute(
            select(PromptTemplate).where(PromptTemplate.key == prompt_key)
        )
        return result.scalar_one_or_none()

    async def _prompt_templates_by_key(self) -> dict[str, PromptTemplate]:
        result = await self.session.execute(select(PromptTemplate))
        return {template.key: template for template in result.scalars().all()}

    async def _prompt_versions(
        self,
        template_id: UUID | None = None,
    ) -> list[PromptVersion]:
        statement = select(PromptVersion).order_by(
            PromptVersion.prompt_key.asc(),
            PromptVersion.version_number.desc(),
        )
        if template_id is not None:
            statement = statement.where(PromptVersion.prompt_template_id == template_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def _next_prompt_version_number(self, template_id: UUID) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.max(PromptVersion.version_number), 0)).where(
                PromptVersion.prompt_template_id == template_id
            )
        )
        return int(result.scalar_one()) + 1

    def _prompt_payload(
        self,
        template: PromptTemplate,
        agent: Agent | None,
        versions: list[PromptVersion],
    ) -> dict[str, object]:
        active = next(
            (version for version in versions if version.status == PromptVersionStatus.ACTIVE),
            None,
        )
        return {
            "id": template.id,
            "key": template.key,
            "agent_id": template.agent_id,
            "agent_key": agent.key if agent else "",
            "name": template.name,
            "description": template.description,
            "created_by": template.created_by,
            "active_version": active,
            "versions": versions,
            "created_at": template.created_at,
            "updated_at": template.updated_at,
        }


class AgentExecutionService(AgentRegistryService):
    def __init__(
        self,
        session: AsyncSession,
        provider: BaseLLMProvider | None = None,
    ) -> None:
        super().__init__(session)
        self.provider = provider or default_llm_provider(session)

    async def run_agent(
        self,
        agent_key: str,
        payload: AgentRunRequest,
        current_user: CurrentUser,
        *,
        retry_of_run: AgentRun | None = None,
    ) -> dict[str, object]:
        await self.ensure_defaults()
        agent = await self._agent_by_key(agent_key)
        if agent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        self._assert_agent_executable(agent, current_user)
        prompt = await self.active_prompt_version(f"{agent.key}.v1")
        if prompt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active prompt version not found",
            )

        now = datetime.now(UTC)
        attempt_number = (retry_of_run.attempt_number + 1) if retry_of_run else 1
        run = AgentRun(
            agent_id=agent.id,
            agent_key=agent.key,
            prompt_version_id=prompt.id,
            prompt_key=prompt.prompt_key,
            prompt_version_number=prompt.version_number,
            status=AgentRunStatus.RUNNING,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            workflow_stage=payload.workflow_stage,
            trigger=payload.trigger,
            requested_by=current_user.id,
            input_payload=payload.input_payload,
            regeneration_reason=payload.regeneration_reason,
            retry_of_run_id=retry_of_run.id if retry_of_run else None,
            attempt_number=attempt_number,
            started_at=now,
        )
        self.session.add(run)
        await self.session.flush()
        self._audit(
            run=run,
            agent=agent,
            action="run_started",
            actor_id=current_user.id,
            message=f"{agent.name} started.",
            metadata={"trigger": payload.trigger},
        )

        try:
            mcp_tool_key, mcp_input = self._agent_tool_request(agent.key, payload)
            mcp_run = await MCPToolExecutionService(self.session).run_workflow_tool(
                mcp_tool_key,
                input_payload=mcp_input,
                caller_type="agent",
                caller_id=str(run.id),
                entity_type=payload.entity_type,
                entity_id=payload.entity_id,
                workflow_stage=payload.workflow_stage or agent.key,
                commit=False,
            )
            mcp_run_id = mcp_run.id
            mcp_tool_status = mcp_run.status.value
            mcp_tool_result = {
                "tool_key": mcp_tool_key,
                "run_id": str(mcp_run.id),
                "status": mcp_run.status.value,
                "output": mcp_run.output_payload,
                "error_reason": mcp_run.error_reason,
            }
            self._audit(
                run=run,
                agent=agent,
                action="mcp_tool_linked",
                actor_id=current_user.id,
                message=f"{agent.name} called {mcp_tool_key} through MCP.",
                metadata=mcp_tool_result,
            )
            llm_response = await self.provider.generate(
                LLMRequest(
                    agent_key=agent.key,
                    prompt_key=prompt.prompt_key,
                    prompt_version=prompt.version_number,
                    template_body=prompt.template_body,
                    input_payload={
                        **payload.input_payload,
                        "entity_type": payload.entity_type,
                        "workflow_stage": payload.workflow_stage,
                        "mcp_tool_result": mcp_tool_result,
                    },
                )
            )
            validation = validate_agent_output(llm_response.output)
            validation_result = AgentOutputValidationResult(
                run_id=run.id,
                status=validation.status,
                checks=validation.checks,
                errors=validation.errors,
            )
            self.session.add(validation_result)
            run.output_payload = llm_response.output
            run.output_metadata = self._sanitize_metadata(
                {
                    **llm_response.metadata,
                    "mcp_run_ids": [str(mcp_run_id)] if mcp_run_id else [],
                    "mcp_tool_calls": [
                        {
                            "tool_key": mcp_tool_key,
                            "run_id": str(mcp_run_id),
                            "status": mcp_tool_status,
                        }
                    ]
                    if mcp_run_id
                    else [],
                }
            )
            run.validation_summary = {
                "status": validation.status.value,
                "errors": validation.errors,
                "needs_approval": bool(llm_response.output.get("needs_approval")),
            }
            run.status = AgentRunStatus.FAILED if validation.errors else AgentRunStatus.SUCCEEDED
            run.error_reason = "; ".join(validation.errors) if validation.errors else None
            run.completed_at = datetime.now(UTC)
            self._audit(
                run=run,
                agent=agent,
                action="run_completed",
                actor_id=current_user.id,
                message=f"{agent.name} completed with status {run.status.value}.",
                metadata={
                    "validation_status": validation.status.value,
                    "mcp_run_ids": [str(mcp_run_id)] if mcp_run_id else [],
                },
            )
        except Exception as exc:
            run.status = AgentRunStatus.FAILED
            run.error_reason = str(exc)
            run.completed_at = datetime.now(UTC)
            run.validation_summary = {"status": "failed", "errors": [str(exc)]}
            self._audit(
                run=run,
                agent=agent,
                action="run_failed",
                actor_id=current_user.id,
                message=str(exc),
                metadata={"provider": "unavailable"},
            )

        await self.session.commit()
        return await self.get_run_detail(run.id)

    async def retry_run(
        self,
        run_id: UUID,
        payload: AgentRunRetryRequest,
        current_user: CurrentUser,
    ) -> dict[str, object]:
        original = await self._run(run_id)
        retry_payload = AgentRunRequest(
            input_payload=payload.input_payload or original.input_payload,
            entity_type=original.entity_type,
            entity_id=original.entity_id,
            workflow_stage=original.workflow_stage,
            trigger="retry",
            regeneration_reason=payload.regeneration_reason,
        )
        return await self.run_agent(
            original.agent_key,
            retry_payload,
            current_user,
            retry_of_run=original,
        )

    async def list_runs(
        self,
        *,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        agent_key: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, object]:
        await self.ensure_defaults()
        cursor_token = decode_cursor(cursor)
        statement = select(AgentRun)
        if entity_type is not None:
            statement = statement.where(AgentRun.entity_type == entity_type)
        if entity_id is not None:
            statement = statement.where(AgentRun.entity_id == entity_id)
        if agent_key is not None:
            statement = statement.where(AgentRun.agent_key == agent_key)
        if cursor_token is not None:
            statement = statement.where(
                or_(
                    AgentRun.created_at < cursor_token.created_at,
                    and_(
                        AgentRun.created_at == cursor_token.created_at,
                        AgentRun.id < cursor_token.id,
                    ),
                )
            )
        statement = statement.order_by(AgentRun.created_at.desc(), AgentRun.id.desc()).limit(
            limit + 1
        )
        result = await self.session.execute(statement)
        rows = list(result.scalars().all())
        has_next = len(rows) > limit
        items = rows[:limit]
        next_cursor = (
            encode_cursor(items[-1].created_at, items[-1].id) if has_next and items else None
        )
        return {
            "items": items,
            **cursor_meta(
                page_size=limit,
                has_next=has_next,
                next_cursor=next_cursor,
                previous_cursor=None,
            ),
        }

    async def token_stats(self, period: AgentTokenStatsPeriod = "day") -> dict[str, object]:
        await self.ensure_defaults()
        now = datetime.now(UTC)
        window_start = self._token_stats_window_start(period, now)
        agents_by_key = await self._agents_by_key()
        result = await self.session.execute(
            select(AgentRun)
            .where(
                or_(
                    and_(
                        AgentRun.completed_at >= window_start,
                        AgentRun.completed_at <= now,
                    ),
                    and_(
                        AgentRun.completed_at.is_(None),
                        AgentRun.created_at >= window_start,
                        AgentRun.created_at <= now,
                    ),
                )
            )
            .order_by(AgentRun.created_at.asc(), AgentRun.id.asc())
        )
        runs = list(result.scalars().all())
        series_names_by_id = await self._series_names_by_id(runs)
        totals = self._empty_token_totals()
        agent_stats = {
            agent.key: {
                **self._empty_token_totals(),
                "agent_id": agent.id,
                "agent_key": agent.key,
                "agent_name": agent.name,
                "provider": None,
                "last_run_at": None,
            }
            for agent in agents_by_key.values()
        }
        timeline = {
            label: {
                "label": label,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "run_count": 0,
            }
            for label in self._token_timeline_labels(period, window_start)
        }
        token_requests: list[dict[str, object]] = []

        for run in runs:
            timestamp = run.completed_at or run.created_at
            if timestamp is None or timestamp < window_start or timestamp > now:
                continue
            agent = agents_by_key.get(run.agent_key)
            if run.agent_key not in agent_stats:
                agent_stats[run.agent_key] = {
                    **self._empty_token_totals(),
                    "agent_id": run.agent_id,
                    "agent_key": run.agent_key,
                    "agent_name": agent.name if agent else run.agent_key.replace("_", " ").title(),
                    "provider": None,
                    "last_run_at": None,
                }

            usage = self._token_usage_from_metadata(run.output_metadata or {})
            provider = self._provider_from_metadata(run.output_metadata or {})
            estimated_usage = self._estimated_token_usage_for_run(run)
            display_usage = usage if usage["total_tokens"] > 0 else estimated_usage
            is_estimated = usage["total_tokens"] == 0 and estimated_usage["total_tokens"] > 0
            self._add_token_usage(totals, usage)
            totals["run_count"] += 1
            bucket = timeline[self._token_timeline_label(period, timestamp)]
            self._add_token_usage(bucket, usage, include_cached=False)
            bucket["run_count"] += 1

            stat = agent_stats[run.agent_key]
            agent_name = str(stat["agent_name"])
            self._add_token_usage(stat, usage)
            stat["run_count"] += 1
            if provider and provider != "workflow_service":
                stat["provider"] = provider
            if usage["total_tokens"] > 0:
                stat["tokenized_run_count"] += 1
                totals["tokenized_run_count"] += 1
            last_run_at = stat["last_run_at"]
            if last_run_at is None or timestamp > last_run_at:
                stat["last_run_at"] = timestamp
            series_id = run.entity_id if run.entity_type == "series" else None
            token_requests.append(
                {
                    "id": run.id,
                    "agent_id": run.agent_id,
                    "agent_key": run.agent_key,
                    "agent_name": agent_name,
                    "provider": provider if provider != "workflow_service" else None,
                    "status": run.status,
                    "trigger": run.trigger,
                    "entity_type": run.entity_type,
                    "entity_id": run.entity_id,
                    "series_id": series_id,
                    "series_name": series_names_by_id.get(series_id) if series_id else None,
                    "workflow_stage": run.workflow_stage,
                    "sequence_number": len(token_requests) + 1,
                    "label": self._token_request_label(agent_name, len(token_requests) + 1),
                    "created_at": run.created_at,
                    "completed_at": run.completed_at,
                    "prompt_tokens": usage["prompt_tokens"],
                    "completion_tokens": usage["completion_tokens"],
                    "cached_tokens": usage["cached_tokens"],
                    "reasoning_tokens": usage["reasoning_tokens"],
                    "total_tokens": usage["total_tokens"],
                    "estimated_prompt_tokens": estimated_usage["prompt_tokens"],
                    "estimated_completion_tokens": estimated_usage["completion_tokens"],
                    "estimated_total_tokens": estimated_usage["total_tokens"],
                    "display_prompt_tokens": display_usage["prompt_tokens"],
                    "display_completion_tokens": display_usage["completion_tokens"],
                    "display_total_tokens": display_usage["total_tokens"],
                    "is_estimated": is_estimated,
                }
            )

        self._finish_token_totals(totals)
        total_tokens = totals["total_tokens"]
        agents = []
        for stat in agent_stats.values():
            self._finish_token_totals(stat)
            stat["share_percentage"] = (
                round((stat["total_tokens"] / total_tokens) * 100, 1) if total_tokens else 0
            )
            if stat["run_count"] or stat["total_tokens"]:
                agents.append(stat)

        return {
            "period": period,
            "generated_at": now,
            "window_start": window_start,
            "window_end": now,
            "totals": totals,
            "agents": sorted(
                agents,
                key=lambda item: (
                    -int(item["total_tokens"]),
                    str(item["agent_name"]).lower(),
                ),
            ),
            "timeline": list(timeline.values()),
            "requests": token_requests,
        }

    async def get_run_detail(self, run_id: UUID) -> dict[str, object]:
        run = await self._run(run_id)
        audit_logs = await self._audit_logs(run_id)
        validations = await self._validation_results(run_id)
        return {
            **run.__dict__,
            "audit_logs": audit_logs,
            "validation_results": validations,
        }

    async def record_workflow_run(
        self,
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
    ) -> AgentRun | None:
        await self.ensure_defaults(commit=False)
        agent = await self._agent_by_key(agent_key)
        prompt = await self.active_prompt_version(f"{agent_key}.v1", missing_ok=True)
        if agent is None or prompt is None:
            return None
        run = AgentRun(
            agent_id=agent.id,
            agent_key=agent.key,
            prompt_version_id=prompt.id,
            prompt_key=prompt.prompt_key,
            prompt_version_number=prompt.version_number,
            status=AgentRunStatus.FAILED if error_reason else AgentRunStatus.SUCCEEDED,
            entity_type=entity_type,
            entity_id=entity_id,
            workflow_stage=workflow_stage,
            trigger=trigger,
            input_payload=input_payload or {},
            output_payload=output_payload
            or {
                "summary": f"{agent.name} completed inside the controlled workflow service.",
                "needs_approval": True,
            },
            output_metadata={
                "provider": "workflow_service",
                "recorded_by": "workflow_service",
                "prompt_key": prompt.prompt_key,
                "prompt_version": prompt.version_number,
            },
            validation_summary={
                "status": "passed" if not error_reason else "failed",
                "needs_approval": True,
                "errors": [error_reason] if error_reason else [],
            },
            error_reason=error_reason,
            regeneration_reason=regeneration_reason,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        self.session.add(run)
        await self.session.flush()
        self._audit(
            run=run,
            agent=agent,
            action="workflow_run_recorded",
            actor_id=None,
            message=f"{agent.name} run recorded by workflow service.",
            metadata={"workflow_stage": workflow_stage, "trigger": trigger},
        )
        return run

    async def _run(self, run_id: UUID) -> AgentRun:
        result = await self.session.execute(select(AgentRun).where(AgentRun.id == run_id))
        run = result.scalar_one_or_none()
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
        return run

    async def _audit_logs(self, run_id: UUID) -> list[AgentAuditLog]:
        result = await self.session.execute(
            select(AgentAuditLog)
            .where(AgentAuditLog.run_id == run_id)
            .order_by(AgentAuditLog.created_at.asc())
        )
        return list(result.scalars().all())

    async def _validation_results(self, run_id: UUID) -> list[AgentOutputValidationResult]:
        result = await self.session.execute(
            select(AgentOutputValidationResult)
            .where(AgentOutputValidationResult.run_id == run_id)
            .order_by(AgentOutputValidationResult.created_at.asc())
        )
        return list(result.scalars().all())

    def _assert_agent_executable(self, agent: Agent, current_user: CurrentUser) -> None:
        if not agent.is_enabled:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Agent is disabled")
        if agent.required_permission and not current_user.has_permission(agent.required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {agent.required_permission}",
            )

    def _audit(
        self,
        *,
        run: AgentRun,
        agent: Agent,
        action: str,
        actor_id: UUID | None,
        message: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.session.add(
            AgentAuditLog(
                run_id=run.id,
                agent_id=agent.id,
                action=action,
                actor_id=actor_id,
                message=message,
                metadata_payload=metadata or {},
            )
        )

    def _sanitize_metadata(self, metadata: dict[str, object]) -> dict[str, object]:
        redacted: dict[str, object] = {}
        for key, value in metadata.items():
            if "key" in key.lower() or "secret" in key.lower() or "token" in key.lower():
                redacted[key] = "[redacted]"
            else:
                redacted[key] = value
        return redacted

    def _agent_tool_request(
        self,
        agent_key: str,
        payload: AgentRunRequest,
    ) -> tuple[str, dict[str, object]]:
        base_payload = {
            **payload.input_payload,
            "entity_type": payload.entity_type,
            "entity_id": str(payload.entity_id) if payload.entity_id else None,
            "workflow_stage": payload.workflow_stage or agent_key,
        }
        if agent_key in {"research", "discovery", "narrative"}:
            return (
                "research.search_sources",
                {
                    **base_payload,
                    "query": str(
                        payload.input_payload.get("query")
                        or payload.input_payload.get("topic")
                        or payload.workflow_stage
                        or agent_key
                    ),
                },
            )
        if agent_key == "publishing":
            return "buffer.test_connection", base_payload
        if agent_key in {"qa", "audit", "coordinator"}:
            return (
                "llm.validate_output",
                {
                    **base_payload,
                    "output": {
                        "agent_key": agent_key,
                        "input": payload.input_payload,
                    },
                },
            )
        return (
            "llm.generate_text",
            {
                **base_payload,
                "prompt": (
                    f"Generate {agent_key} workflow support for "
                    f"{payload.workflow_stage or 'the current stage'}."
                ),
            },
        )

    async def _series_names_by_id(self, runs: list[AgentRun]) -> dict[UUID, str]:
        series_ids = {
            run.entity_id
            for run in runs
            if run.entity_type == "series" and run.entity_id is not None
        }
        if not series_ids:
            return {}
        result = await self.session.execute(
            select(Series.id, Series.name).where(Series.id.in_(series_ids))
        )
        return {series_id: name for series_id, name in result.all()}

    def _empty_token_totals(self) -> dict[str, int]:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cached_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
            "run_count": 0,
            "tokenized_run_count": 0,
            "average_tokens_per_run": 0,
        }

    def _add_token_usage(
        self,
        target: dict[str, object],
        usage: dict[str, int],
        *,
        include_cached: bool = True,
    ) -> None:
        target["prompt_tokens"] = int(target.get("prompt_tokens") or 0) + usage["prompt_tokens"]
        target["completion_tokens"] = int(target.get("completion_tokens") or 0) + usage[
            "completion_tokens"
        ]
        target["total_tokens"] = int(target.get("total_tokens") or 0) + usage["total_tokens"]
        if include_cached:
            target["cached_tokens"] = int(target.get("cached_tokens") or 0) + usage[
                "cached_tokens"
            ]
            target["reasoning_tokens"] = int(target.get("reasoning_tokens") or 0) + usage[
                "reasoning_tokens"
            ]

    def _finish_token_totals(self, target: dict[str, object]) -> None:
        tokenized_runs = int(target.get("tokenized_run_count") or 0)
        target["average_tokens_per_run"] = (
            round(int(target.get("total_tokens") or 0) / tokenized_runs) if tokenized_runs else 0
        )

    def _provider_from_metadata(self, metadata: Mapping[str, object]) -> str | None:
        provider = metadata.get("provider")
        return str(provider) if provider else None

    def _token_usage_from_metadata(self, metadata: Mapping[str, object]) -> dict[str, int]:
        sources: list[Mapping[str, object]] = []
        for key in ("usage", "token_usage", "usage_metadata", "usageMetadata"):
            value = metadata.get(key)
            if isinstance(value, Mapping):
                sources.append(value)
        sources.append(metadata)

        for source in sources:
            prompt_tokens = self._first_token_int(
                source,
                "prompt_tokens",
                "input_tokens",
                "promptTokenCount",
                "inputTokenCount",
            )
            completion_tokens = self._first_token_int(
                source,
                "completion_tokens",
                "output_tokens",
                "completionTokenCount",
                "candidatesTokenCount",
                "outputTokenCount",
            )
            cached_tokens = self._first_token_int(
                source,
                "cached_tokens",
                "cachedContentTokenCount",
                "cache_read_input_tokens",
            )
            reasoning_tokens = self._first_token_int(
                source,
                "reasoning_tokens",
                "thoughtsTokenCount",
            )
            total_tokens = self._first_token_int(source, "total_tokens", "totalTokenCount")
            if total_tokens == 0 and (prompt_tokens or completion_tokens or reasoning_tokens):
                total_tokens = prompt_tokens + completion_tokens + reasoning_tokens
            if (
                prompt_tokens
                or completion_tokens
                or cached_tokens
                or reasoning_tokens
                or total_tokens
            ):
                return {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "cached_tokens": cached_tokens,
                    "reasoning_tokens": reasoning_tokens,
                    "total_tokens": total_tokens,
                }
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cached_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
        }

    def _estimated_token_usage_for_run(self, run: AgentRun) -> dict[str, int]:
        prompt_tokens = self._estimated_token_count(run.input_payload or {})
        completion_source = run.output_payload or run.validation_summary or {}
        completion_tokens = self._estimated_token_count(completion_source)
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cached_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": prompt_tokens + completion_tokens,
        }

    def _estimated_token_count(self, value: object) -> int:
        if value in (None, "", {}, []):
            return 0
        try:
            text = json.dumps(value, default=str, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            text = str(value)
        text = text.strip()
        return max(round(len(text) / 4), 1) if text else 0

    def _token_request_label(self, agent_name: str, sequence_number: int) -> str:
        short_name = agent_name.replace(" Agent", "")
        return f"{short_name} #{sequence_number}"

    def _first_token_int(self, metadata: Mapping[str, object], *keys: str) -> int:
        for key in keys:
            value = metadata.get(key)
            if isinstance(value, bool) or value is None:
                continue
            try:
                return max(int(value), 0)
            except (TypeError, ValueError):
                continue
        return 0

    def _token_stats_window_start(
        self,
        period: AgentTokenStatsPeriod,
        now: datetime,
    ) -> datetime:
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if period == "day":
            return start_of_day
        if period == "week":
            return start_of_day - timedelta(days=start_of_day.weekday())
        return start_of_day.replace(day=1)

    def _token_timeline_labels(
        self,
        period: AgentTokenStatsPeriod,
        window_start: datetime,
    ) -> list[str]:
        if period == "day":
            return ["Today"]
        if period == "week":
            return [
                (window_start + timedelta(days=offset)).strftime("%a")
                for offset in range(7)
            ]
        return [f"W{index}" for index in range(1, 6)]

    def _token_timeline_label(self, period: AgentTokenStatsPeriod, value: datetime) -> str:
        if period == "day":
            return "Today"
        if period == "week":
            return value.strftime("%a")
        return f"W{min(((value.day - 1) // 7) + 1, 5)}"
