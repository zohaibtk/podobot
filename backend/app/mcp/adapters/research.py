from uuid import UUID

from app.db.types import (
    ResearchScoreEntityType,
    ResearchSourceCategory,
    ResearchSourceProviderType,
)
from app.mcp.client.base import MCPClientRequest, MCPClientResponse
from app.mcp.client.unavailable import UnavailableMCPClient
from app.modules.research.scoring import ResearchScoringService
from app.research.providers.registry import ResearchProviderRegistry


class ResearchMCPAdapter(UnavailableMCPClient):
    """Provider-backed research MCP adapter."""

    def __init__(self, session) -> None:
        self.session = session
        self.registry = ResearchProviderRegistry(session)

    async def execute(self, request: MCPClientRequest) -> MCPClientResponse:
        if not request.tool_key.startswith("research."):
            return await super().execute(request)

        payload = request.input_payload
        if request.tool_key == "research.list_enabled_sources":
            result = await self.registry.list_enabled_sources()
            return self._response(
                {"sources": result, "count": len(result)},
                {"tool": request.tool_key, "source_count": len(result)},
            )

        if request.tool_key == "research.test_source_connection":
            source_key = self._source_key(payload)
            result = await self.registry.test_source_connection(source_key)
            return self._response(result.output, result.metadata)

        if request.tool_key == "research.search_sources":
            filters = self._filters(payload)
            self._attach_caller_context(filters, request.caller_context)
            result = await self.registry.search_sources(
                query=str(payload.get("query") or ""),
                filters=filters,
                source_key=self._optional_str(payload.get("source_key")),
                provider_type=self._provider_type(payload.get("provider_type")),
                category=self._category(payload.get("category")),
            )
            return self._response(result.output, result.metadata)

        if request.tool_key in {"research.fetch_resource", "research.fetch_source"}:
            resource = str(
                payload.get("resource_id_or_url")
                or payload.get("resource")
                or payload.get("source")
                or ""
            )
            result = await self.registry.fetch_resource(
                resource_id_or_url=resource,
                source_key=self._optional_str(payload.get("source_key")),
                provider_type=self._provider_type(payload.get("provider_type")),
            )
            if request.tool_key == "research.fetch_source":
                document = result.output.get("document")
                result.output["source"] = resource
                result.output["content"] = (
                    document.get("content")
                    if isinstance(document, dict)
                    else "Research source content unavailable."
                )
            return self._response(result.output, result.metadata)

        if request.tool_key == "research.scrape_resource":
            result = await self.registry.scrape_resource(url=str(payload.get("url") or ""))
            return self._response(result.output, result.metadata)

        if request.tool_key == "research.get_trend_score":
            filters = self._filters(payload)
            self._attach_caller_context(filters, request.caller_context)
            result = await self.registry.get_trend_score(
                query=str(payload.get("query") or ""),
                filters=filters,
            )
            return self._response(result.output, result.metadata)

        if request.tool_key == "research.calculate_provider_scores":
            normalized = payload.get("normalized_result")
            if not isinstance(normalized, dict):
                normalized = (
                    payload.get("result")
                    if isinstance(payload.get("result"), dict)
                    else {}
                )
            result = await self.registry.calculate_provider_scores(
                normalized_result=normalized,
                source_key=self._optional_str(payload.get("source_key")),
                provider_type=self._provider_type(payload.get("provider_type")),
            )
            return self._response(result.output, result.metadata)

        if request.tool_key == "research.calculate_composite_score":
            result = await ResearchScoringService(self.session).explain_score(payload)
            return self._response(result, {"tool": request.tool_key, "success": True})

        if request.tool_key == "research.explain_score":
            result = await ResearchScoringService(self.session).explain_score(payload)
            return self._response(result, {"tool": request.tool_key, "success": True})

        if request.tool_key == "research.score_document":
            document_id = UUID(str(payload.get("document_id") or ""))
            result = await ResearchScoringService(self.session).score_document(document_id)
            return self._response(result, {"tool": request.tool_key, "success": True})

        if request.tool_key == "research.score_run_documents":
            run_id = UUID(str(payload.get("run_id") or payload.get("research_run_id") or ""))
            result = await ResearchScoringService(self.session).score_run_documents(run_id)
            return self._response(result, {"tool": request.tool_key, "success": True})

        if request.tool_key == "research.score_entity_evidence":
            entity_type = ResearchScoreEntityType(str(payload.get("entity_type") or ""))
            entity_id = UUID(str(payload.get("entity_id") or ""))
            result = await ResearchScoringService(self.session).entity_score_breakdown(
                entity_type,
                entity_id,
            )
            return self._response(result, {"tool": request.tool_key, "success": True})

        if request.tool_key == "research.extract_signals":
            filters = {"classification": "signals"}
            self._attach_caller_context(filters, request.caller_context)
            result = await self.registry.search_sources(
                query=str(payload.get("content") or "research signal extraction"),
                filters=filters,
                provider_type=ResearchSourceProviderType.GEMINI,
            )
            return self._response(
                {"signals": result.output.get("results", [])},
                result.metadata,
            )

        return await super().execute(request)

    def _response(
        self,
        output_payload: dict[str, object],
        output_metadata: dict[str, object],
    ) -> MCPClientResponse:
        return MCPClientResponse(
            output_payload=output_payload,
            output_metadata={
                "adapter": "research-provider-registry",
                **output_metadata,
            },
        )

    def _source_key(self, payload: dict[str, object]) -> str:
        source_key = payload.get("source_key") or payload.get("source")
        return str(source_key or "")

    def _filters(self, payload: dict[str, object]) -> dict[str, object]:
        filters = payload.get("filters")
        if isinstance(filters, dict):
            return filters
        return {
            key: value
            for key, value in payload.items()
            if key
            not in {
                "query",
                "source",
                "source_key",
                "provider_type",
                "resource",
                "resource_id_or_url",
                "url",
            }
        }

    def _provider_type(self, value: object) -> ResearchSourceProviderType | None:
        if value in (None, ""):
            return None
        return ResearchSourceProviderType(str(value))

    def _category(self, value: object) -> ResearchSourceCategory | None:
        if value in (None, ""):
            return None
        return ResearchSourceCategory(str(value))

    def _optional_str(self, value: object) -> str | None:
        if value in (None, ""):
            return None
        return str(value)

    def _attach_caller_context(
        self,
        filters: dict[str, object],
        caller_context: dict[str, object],
    ) -> None:
        if caller_context:
            filters["_caller_context"] = caller_context
        entity_type = caller_context.get("entity_type")
        entity_id = caller_context.get("entity_id")
        if entity_type == "series" and entity_id:
            filters.setdefault("series_id", entity_id)
        if entity_type == "episode" and entity_id:
            filters.setdefault("episode_id", entity_id)
        if entity_type == "strategy_run" and entity_id:
            filters.setdefault("strategy_run_id", entity_id)
