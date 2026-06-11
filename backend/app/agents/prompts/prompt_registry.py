from pydantic import BaseModel, Field


class PromptSpec(BaseModel):
    prompt_id: str
    version: str
    purpose: str
    template: str
    model_policy: dict[str, object] = Field(default_factory=dict)
    approved_for_production: bool = False


class PromptRegistry:
    def __init__(self) -> None:
        self._prompts: dict[tuple[str, str], PromptSpec] = {}

    def register(self, spec: PromptSpec) -> None:
        self._prompts[(spec.prompt_id, spec.version)] = spec

    def get(self, prompt_id: str, version: str) -> PromptSpec:
        return self._prompts[(prompt_id, version)]
