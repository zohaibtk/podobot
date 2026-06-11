import { requestJson } from "@/shared/api/httpClient";
import type {
  StrategyIdeaActionResponse,
  StrategyIdeaListResponse,
  StrategyIdeaStatus,
  StrategyRunListResponse,
  StrategyWorkspaceSummary,
  StrategyWorkspace
} from "@/shared/types/strategy";

export type StrategySummaryRange = "today" | "7d" | "30d" | "90d" | "all";

export function getStrategyWorkspace() {
  return requestJson<StrategyWorkspace>("/api/v1/strategy");
}

export function getStrategySummary(range: StrategySummaryRange = "30d") {
  const search = new URLSearchParams({ range });
  return requestJson<StrategyWorkspaceSummary>(`/api/v1/strategy/summary?${search}`);
}

export function listStrategyRuns(params: { limit?: number; cursor?: string | null } = {}) {
  const query = cursorQuery(params);
  return requestJson<StrategyRunListResponse>(`/api/v1/strategy/runs${query}`);
}

export function listStrategyIdeas(params: {
  limit?: number;
  cursor?: string | null;
  status?: StrategyIdeaStatus | "all";
  runId?: string | null;
  query?: string;
} = {}) {
  const search = new URLSearchParams();
  if (params.limit) {
    search.set("limit", String(params.limit));
  }
  if (params.cursor) {
    search.set("cursor", params.cursor);
  }
  if (params.status && params.status !== "all") {
    search.set("status", params.status);
  }
  if (params.runId) {
    search.set("run_id", params.runId);
  }
  if (params.query?.trim()) {
    search.set("query", params.query.trim());
  }
  const query = search.toString();
  return requestJson<StrategyIdeaListResponse>(
    `/api/v1/strategy/ideas${query ? `?${query}` : ""}`
  );
}

export function createStrategyRun() {
  return requestJson<StrategyWorkspace>("/api/v1/strategy/runs", {
    method: "POST"
  });
}

export function reviewStrategyIdea(ideaId: string) {
  return requestJson<StrategyIdeaActionResponse>(`/api/v1/strategy/ideas/${ideaId}/review`, {
    method: "POST"
  });
}

export function dismissStrategyIdea(ideaId: string) {
  return requestJson<StrategyIdeaActionResponse>(`/api/v1/strategy/ideas/${ideaId}/dismiss`, {
    method: "POST"
  });
}

export function restoreStrategyIdea(ideaId: string) {
  return requestJson<StrategyIdeaActionResponse>(`/api/v1/strategy/ideas/${ideaId}/restore`, {
    method: "POST"
  });
}

export function convertStrategyIdea(ideaId: string) {
  return requestJson<StrategyIdeaActionResponse>(`/api/v1/strategy/ideas/${ideaId}/convert`, {
    method: "POST"
  });
}

function cursorQuery(params: { limit?: number; cursor?: string | null }) {
  const search = new URLSearchParams();
  if (params.limit) {
    search.set("limit", String(params.limit));
  }
  if (params.cursor) {
    search.set("cursor", params.cursor);
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}
