from pydantic import BaseModel, Field


class McpToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, object] = Field(default_factory=dict)
    enabled: bool = False
