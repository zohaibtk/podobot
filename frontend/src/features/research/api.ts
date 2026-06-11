import { requestJson } from "@/shared/api/httpClient";
import type {
  DiscoveryLedgerListResponse,
  ResearchDocumentListResponse,
  ResearchDocumentScore,
  ResearchFilters,
  ResearchRunDetail,
  ResearchRunListResponse,
  ResearchScoreBreakdown,
  ResearchScoreEntityType,
  ResearchScoreSummary,
  ResearchSourceUsageListResponse
} from "@/shared/types/research";

function queryString(filters: ResearchFilters = {}) {
  const params = new URLSearchParams();
  if (filters.page) params.set("page", String(filters.page));
  if (filters.pageSize) params.set("page_size", String(filters.pageSize));
  if (filters.search) params.set("search", filters.search);
  if (filters.sort) params.set("sort", filters.sort);
  if (filters.status) params.set("status", filters.status);
  if (filters.runType) params.set("run_type", filters.runType);
  if (filters.researchRunId) params.set("research_run_id", filters.researchRunId);
  if (filters.sourceId) params.set("source_id", filters.sourceId);
  if (filters.seriesId) params.set("series_id", filters.seriesId);
  if (filters.episodeId) params.set("episode_id", filters.episodeId);
  if (filters.strategyRunId) params.set("strategy_run_id", filters.strategyRunId);
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

export function listResearchRuns(filters: ResearchFilters = {}) {
  return requestJson<ResearchRunListResponse>(`/api/v1/research/runs${queryString(filters)}`);
}

export function getResearchRun(runId: string) {
  return requestJson<ResearchRunDetail>(`/api/v1/research/runs/${runId}`);
}

export function getResearchRunScoreSummary(runId: string) {
  return requestJson<ResearchScoreSummary>(`/api/v1/research/runs/${runId}/score-summary`);
}

export function scoreResearchRunDocuments(runId: string) {
  return requestJson<{ success: boolean; message: string; score_summary: ResearchScoreSummary }>(
    `/api/v1/research/runs/${runId}/score-documents`,
    { method: "POST" }
  );
}

export function listResearchDocuments(filters: ResearchFilters = {}) {
  return requestJson<ResearchDocumentListResponse>(
    `/api/v1/research/documents${queryString(filters)}`
  );
}

export function getResearchDocumentScore(documentId: string) {
  return requestJson<ResearchDocumentScore>(`/api/v1/research/documents/${documentId}/score`);
}

export function rescoreResearchDocument(documentId: string) {
  return requestJson<ResearchDocumentScore>(
    `/api/v1/research/documents/${documentId}/rescore`,
    { method: "POST" }
  );
}

export function explainResearchScore(payload: {
  tier_score: number;
  engagement_score: number;
  freshness_score: number;
  author_score: number;
}) {
  return requestJson<{
    formula: string;
    formula_version: string;
    tier_score: number;
    engagement_score: number;
    freshness_score: number;
    author_score: number;
    composite_score: number;
    confidence_level: string;
    explanation: string;
  }>("/api/v1/research/score/explain", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getEntityScoreBreakdown(entityType: ResearchScoreEntityType, entityId: string) {
  return requestJson<ResearchScoreBreakdown>(
    `/api/v1/research/entities/${entityType}/${entityId}/score-breakdown`
  );
}

export function listDiscoveryLedger(filters: ResearchFilters = {}) {
  return requestJson<DiscoveryLedgerListResponse>(
    `/api/v1/research/ledger${queryString(filters)}`
  );
}

export function listResearchSourceUsage(filters: ResearchFilters = {}) {
  return requestJson<ResearchSourceUsageListResponse>(
    `/api/v1/research/source-usage${queryString(filters)}`
  );
}
