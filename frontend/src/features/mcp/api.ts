import { requestJson } from "@/shared/api/httpClient";
import type {
  MCPServer,
  MCPServerListResponse,
  MCPServerTestResponse,
  MCPTool,
  MCPToolListResponse,
  MCPToolRunDetail,
  MCPToolRunListResponse,
  MCPToolRunPayload
} from "@/shared/types/mcp";

export function listMCPServers() {
  return requestJson<MCPServerListResponse>("/api/v1/mcp/servers");
}

export function getMCPServer(serverKey: string) {
  return requestJson<MCPServer>(`/api/v1/mcp/servers/${serverKey}`);
}

export function testMCPServer(serverKey: string) {
  return requestJson<MCPServerTestResponse>(`/api/v1/mcp/servers/${serverKey}/test`, {
    method: "POST"
  });
}

export function listMCPTools(serverKey?: string) {
  const suffix = serverKey ? `?server_key=${encodeURIComponent(serverKey)}` : "";
  return requestJson<MCPToolListResponse>(`/api/v1/mcp/tools${suffix}`);
}

export function getMCPTool(toolKey: string) {
  return requestJson<MCPTool>(`/api/v1/mcp/tools/${toolKey}`);
}

export function runMCPTool(toolKey: string, payload: MCPToolRunPayload) {
  return requestJson<MCPToolRunDetail>(`/api/v1/mcp/tools/${toolKey}/run`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function listMCPRuns(params: {
  entityType?: string;
  entityId?: string;
  toolKey?: string;
  serverKey?: string;
  limit?: number;
  cursor?: string | null;
} = {}) {
  const search = new URLSearchParams();
  if (params.entityType) {
    search.set("entity_type", params.entityType);
  }
  if (params.entityId) {
    search.set("entity_id", params.entityId);
  }
  if (params.toolKey) {
    search.set("tool_key", params.toolKey);
  }
  if (params.serverKey) {
    search.set("server_key", params.serverKey);
  }
  if (params.limit) {
    search.set("limit", String(params.limit));
  }
  if (params.cursor) {
    search.set("cursor", params.cursor);
  }
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return requestJson<MCPToolRunListResponse>(`/api/v1/mcp/runs${suffix}`);
}

export function getMCPRun(runId: string) {
  return requestJson<MCPToolRunDetail>(`/api/v1/mcp/runs/${runId}`);
}

export function retryMCPRun(runId: string) {
  return requestJson<MCPToolRunDetail>(`/api/v1/mcp/runs/${runId}/retry`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export function getWorkflowMCPHistory(
  entityType: string,
  entityId: string,
  limit = 20,
  cursor?: string | null
) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) {
    params.set("cursor", cursor);
  }
  return requestJson<MCPToolRunListResponse>(
    `/api/v1/workflow/${entityType}/${entityId}/mcp-history?${params.toString()}`
  );
}
