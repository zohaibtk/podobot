from dataclasses import dataclass, field


@dataclass(frozen=True)
class DefaultAgent:
    key: str
    name: str
    responsibility: str
    tools: list[str] = field(default_factory=list)
    required_permission: str | None = None


@dataclass(frozen=True)
class DefaultPrompt:
    key: str
    agent_key: str
    name: str
    description: str
    template_body: str
    input_schema: dict[str, object]
    output_schema: dict[str, object]


DEFAULT_AGENTS = [
    DefaultAgent(
        key="research",
        name="Research Agent",
        responsibility=(
            "Collect external/source signals and summarize evidence without selecting outcomes."
        ),
        tools=["source_ledger", "research_provider"],
        required_permission="narrative.generate",
    ),
    DefaultAgent(
        key="discovery",
        name="Discovery Agent",
        responsibility="Convert research signals into discovery progress and evidence summaries.",
        tools=["source_ledger", "signal_scoring"],
        required_permission="narrative.generate",
    ),
    DefaultAgent(
        key="narrative",
        name="Narrative Agent",
        responsibility="Generate candidate narrative directions from approved research signals.",
        tools=["source_ledger", "narrative_generator"],
        required_permission="narrative.generate",
    ),
    DefaultAgent(
        key="planning",
        name="Planning Agent",
        responsibility="Suggest an episode plan from the selected narrative without locking it.",
        tools=["episode_plan_generator", "profile_context"],
        required_permission="episode.create",
    ),
    DefaultAgent(
        key="outline",
        name="Outline Agent",
        responsibility="Generate profile-agnostic episode outlines from a locked plan.",
        tools=["outline_generator", "series_context"],
        required_permission="outline.generate",
    ),
    DefaultAgent(
        key="brief",
        name="Brief Agent",
        responsibility="Generate host and guest brief drafts from latest approved outline context.",
        tools=["brief_generator", "profile_context"],
        required_permission="brief.generate",
    ),
    DefaultAgent(
        key="clip_suggestion",
        name="Clip Suggestion Agent",
        responsibility=(
            "Identify metadata-only short clip moments from uploaded transcripts using "
            "selected narrative, research evidence, and trend signals."
        ),
        tools=[
            "transcript_context",
            "selected_narrative",
            "research_ledger",
            "trend_signals",
            "llm.generate_json",
        ],
        required_permission="recording.upload",
    ),
    DefaultAgent(
        key="caption",
        name="Caption Agent",
        responsibility="Generate platform captions from transcript-ready media rows.",
        tools=["caption_generator", "platform_rules"],
        required_permission="caption.generate",
    ),
    DefaultAgent(
        key="publishing",
        name="Publishing Agent",
        responsibility="Prepare publishing status checks and recovery recommendations.",
        tools=["buffer_publishing", "schedule_status"],
        required_permission="schedule.create",
    ),
    DefaultAgent(
        key="qa",
        name="QA Agent",
        responsibility="Validate output quality, completeness, citations, and gate readiness.",
        tools=["output_validator", "quality_rules"],
        required_permission="series.edit",
    ),
    DefaultAgent(
        key="audit",
        name="Audit Agent",
        responsibility="Record auditable decisions, failures, retries, and approval checkpoints.",
        tools=["audit_log"],
        required_permission="settings.manage",
    ),
    DefaultAgent(
        key="coordinator",
        name="Coordinator Agent",
        responsibility="Route workflow requests to specialized agents and preserve human gates.",
        tools=["agent_registry", "prompt_registry", "tool_router"],
        required_permission="series.edit",
    ),
]


def _schema(required: list[str]) -> dict[str, object]:
    return {
        "type": "object",
        "required": required,
        "additionalProperties": True,
    }


DEFAULT_PROMPTS = [
    DefaultPrompt(
        key=f"{agent.key}.v1",
        agent_key=agent.key,
        name=f"{agent.name} default prompt",
        description=f"Active v1 prompt for {agent.name}.",
        template_body=(
            f"You are the {agent.name}. Keep responsibility narrow: {agent.responsibility} "
            "Return structured JSON with summary, signals, confidence, needs_approval, "
            "and artifacts. "
            "Do not bypass producer approval gates."
        ),
        input_schema=_schema(["workflow_stage", "entity_type"]),
        output_schema=_schema(["summary", "needs_approval", "artifacts"]),
    )
    for agent in DEFAULT_AGENTS
]
