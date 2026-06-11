from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    tool_id: str
    display_name: str
    description: str
    enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolSpec, Callable[..., Any]]] = {}

    def register(self, spec: ToolSpec, handler: Callable[..., Any]) -> None:
        self._tools[spec.tool_id] = (spec, handler)

    def get(self, tool_id: str) -> tuple[ToolSpec, Callable[..., Any]]:
        return self._tools[tool_id]

    def list(self) -> list[ToolSpec]:
        return [tool[0] for tool in self._tools.values()]
