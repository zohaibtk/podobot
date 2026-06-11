import { requestJson } from "@/shared/api/httpClient";
import type {
  Agent,
  AgentListResponse,
  AgentRunDetail,
  AgentRunListResponse,
  AgentRunPayload,
  AgentRunRetryPayload,
  AgentTokenStats,
  AgentTokenStatsPeriod,
  PromptListResponse,
  PromptTemplate,
  PromptVersion,
  PromptVersionPayload
} from "@/shared/types/agents";

export function listAgents() {
  return requestJson<AgentListResponse>("/api/v1/agents");
}

export function getAgent(agentKey: string) {
  return requestJson<Agent>(`/api/v1/agents/${agentKey}`);
}

export function listAgentRuns(params: {
  entityType?: string;
  entityId?: string;
  agentKey?: string;
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
  if (params.agentKey) {
    search.set("agent_key", params.agentKey);
  }
  if (params.limit) {
    search.set("limit", String(params.limit));
  }
  if (params.cursor) {
    search.set("cursor", params.cursor);
  }
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return requestJson<AgentRunListResponse>(`/api/v1/agents/runs${suffix}`);
}

export function getAgentRun(runId: string) {
  return requestJson<AgentRunDetail>(`/api/v1/agents/runs/${runId}`);
}

export function getAgentTokenStats(period: AgentTokenStatsPeriod) {
  const params = new URLSearchParams({ period });
  return requestJson<AgentTokenStats>(`/api/v1/agents/token-stats?${params.toString()}`);
}

export function runAgent(agentKey: string, payload: AgentRunPayload) {
  return requestJson<AgentRunDetail>(`/api/v1/agents/${agentKey}/run`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function retryAgentRun(runId: string, payload: AgentRunRetryPayload) {
  return requestJson<AgentRunDetail>(`/api/v1/agents/runs/${runId}/retry`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function listPrompts() {
  return requestJson<PromptListResponse>("/api/v1/prompts");
}

export function getPrompt(promptKey: string) {
  return requestJson<PromptTemplate>(`/api/v1/prompts/${promptKey}`);
}

export function createPromptVersion(promptKey: string, payload: PromptVersionPayload) {
  return requestJson<PromptVersion>(`/api/v1/prompts/${promptKey}/versions`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getWorkflowAgentHistory(
  entityType: string,
  entityId: string,
  limit = 50,
  cursor?: string | null
) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) {
    params.set("cursor", cursor);
  }
  return requestJson<AgentRunListResponse>(
    `/api/v1/workflow/${entityType}/${entityId}/agent-history?${params.toString()}`
  );
}
