import type { PaginatedResponse } from "@/shared/types/pagination";
import type { ResearchSourceProviderType } from "@/shared/types/researchSources";

export type ResearchRunType =
  | "discovery"
  | "strategy"
  | "narrative_regeneration"
  | "topic_generation"
  | "brief_context"
  | "manual_research";

export type ResearchRunStatus =
  | "pending"
  | "running"
  | "completed"
  | "partial_success"
  | "failed"
  | "cancelled";

export type ResearchSourceUsageStatus =
  | "used"
  | "skipped_disabled"
  | "failed"
  | "no_results";

export type DiscoveryLedgerType =
  | "source"
  | "signal"
  | "narrative_support"
  | "narrative_counter"
  | "topic_support"
  | "strategy_support";

export type ResearchConfidenceLevel = "High" | "Medium" | "Low" | "Weak";

export type ResearchScoreEntityType =
  | "research_document"
  | "narrative"
  | "episode_topic"
  | "strategy_idea"
  | "outline"
  | "brief";

export type ScoreExplanation = {
  formula?: string;
  formula_version?: string;
  tier?: string;
  tier_score?: number;
  engagement_score?: number;
  freshness_score?: number;
  author_score?: number;
  composite_score?: number;
  confidence_level?: ResearchConfidenceLevel;
  trend_score?: number | null;
  trend_available?: boolean;
  trend_source?: string | null;
  trend_failure_reason?: string | null;
  explanation?: string;
  warning?: string;
  metadata_used?: Record<string, unknown>;
};

export type ResearchScoreSummary = {
  document_count: number;
  tier_score_avg: number;
  engagement_score_avg: number;
  freshness_score_avg: number;
  author_score_avg: number;
  composite_score: number;
  trend_score: number | null;
  trend_available: boolean;
  confidence_level: ResearchConfidenceLevel;
  confidence_distribution: Record<ResearchConfidenceLevel, number>;
  tier_distribution: Record<string, number>;
  explanation: string;
};

export type ResearchRunStats = {
  total_runs: number;
  running_runs: number;
  failed_runs: number;
  total_documents_found: number;
  total_documents_used: number;
  average_duration_ms: number;
};

export type ResearchRun = {
  id: string;
  run_type: ResearchRunType;
  status: ResearchRunStatus;
  query_text: string;
  series_id: string | null;
  episode_id: string | null;
  strategy_run_id: string | null;
  agent_run_id: string | null;
  mcp_tool_run_id: string | null;
  initiated_by_user_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  failure_reason: string | null;
  enabled_source_count: number;
  successful_source_count: number;
  failed_source_count: number;
  skipped_source_count: number;
  total_documents_found: number;
  total_documents_used: number;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ResearchSourceUsage = {
  id: string;
  research_run_id: string;
  source_id: string;
  source_key: string;
  source_name: string;
  provider_type: ResearchSourceProviderType;
  status: ResearchSourceUsageStatus;
  query_text: string | null;
  documents_found: number;
  documents_used: number;
  latency_ms: number;
  failure_reason: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
};

export type ResearchDocument = {
  id: string;
  research_run_id: string;
  source_id: string;
  source_key: string;
  source_name: string;
  provider_type: ResearchSourceProviderType;
  external_resource_id: string | null;
  title: string;
  url: string | null;
  author: string | null;
  published_at: string | null;
  fetched_at: string;
  resource_type: string;
  content_excerpt: string | null;
  normalized_content: string | null;
  raw_metadata_json: Record<string, unknown>;
  tier: string;
  tier_score: number;
  engagement_score: number;
  freshness_score: number;
  author_score: number;
  composite_score: number;
  trend_score: number | null;
  trend_available: boolean;
  trend_source: string | null;
  trend_failure_reason: string | null;
  confidence_level: ResearchConfidenceLevel;
  score_explanation_json: ScoreExplanation;
  used_in_output: boolean;
  archived: boolean;
  created_at: string;
};

export type DiscoveryLedgerEntry = {
  id: string;
  research_run_id: string;
  document_id: string | null;
  source_id: string;
  source_key: string;
  source_name: string;
  provider_type: ResearchSourceProviderType;
  document_title: string | null;
  document_url: string | null;
  document_tier: string | null;
  document_tier_score: number | null;
  document_engagement_score: number | null;
  document_freshness_score: number | null;
  document_author_score: number | null;
  document_composite_score: number | null;
  document_confidence_level: ResearchConfidenceLevel | null;
  document_trend_score: number | null;
  document_trend_available: boolean | null;
  document_score_explanation_json: ScoreExplanation | null;
  series_id: string | null;
  episode_id: string | null;
  strategy_idea_id: string | null;
  ledger_type: DiscoveryLedgerType;
  evidence_summary: string;
  created_at: string;
};

export type ResearchRunListResponse = PaginatedResponse<ResearchRun> & {
  stats: ResearchRunStats;
};

export type ResearchRunDetail = ResearchRun & {
  source_usage: ResearchSourceUsage[];
  documents: ResearchDocument[];
  ledger_entries: DiscoveryLedgerEntry[];
  score_summary: ResearchScoreSummary;
};

export type ResearchDocumentScore = {
  document_id: string;
  research_run_id: string;
  source_id: string;
  source_key: string;
  source_name: string;
  provider_type: ResearchSourceProviderType;
  title: string;
  tier: string;
  tier_score: number;
  engagement_score: number;
  freshness_score: number;
  author_score: number;
  composite_score: number;
  trend_score: number | null;
  trend_available: boolean;
  trend_source: string | null;
  trend_failure_reason: string | null;
  confidence_level: ResearchConfidenceLevel;
  score_explanation_json: ScoreExplanation;
};

export type ResearchScoreBreakdown = {
  id: string;
  entity_type: ResearchScoreEntityType;
  entity_id: string;
  research_run_id: string | null;
  tier_score_avg: number;
  engagement_score_avg: number;
  freshness_score_avg: number;
  author_score_avg: number;
  composite_score: number;
  trend_score: number | null;
  trend_available: boolean;
  confidence_level: ResearchConfidenceLevel;
  formula_version: string;
  explanation_json: ScoreExplanation;
  created_at: string;
};

export type ResearchDocumentListResponse = PaginatedResponse<ResearchDocument>;
export type DiscoveryLedgerListResponse = PaginatedResponse<DiscoveryLedgerEntry>;
export type ResearchSourceUsageListResponse = PaginatedResponse<ResearchSourceUsage>;

export type ResearchFilters = {
  page?: number;
  pageSize?: number;
  search?: string;
  sort?: string;
  status?: ResearchRunStatus;
  runType?: ResearchRunType;
  researchRunId?: string;
  sourceId?: string;
  seriesId?: string;
  episodeId?: string;
  strategyRunId?: string;
};
