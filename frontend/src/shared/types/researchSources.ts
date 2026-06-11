import type { PaginatedResponse } from "@/shared/types/pagination";
import type { ResearchConfidenceLevel } from "@/shared/types/research";

export type ResearchSourceStatus = "healthy" | "warning" | "failed" | "disabled" | "unknown";

export type ResearchSourceProviderType =
  | "reddit_json"
  | "hn_algolia"
  | "youtube_data_api"
  | "exa"
  | "firecrawl"
  | "serpapi"
  | "pytrends"
  | "openai"
  | "grok_x"
  | "groq"
  | "gemini";

export type ResearchSourceCategory = "discovery" | "scraping" | "trends" | "llm";
export type ResearchProviderMode = "real" | "unavailable";

export type ResearchSource = {
  id: string;
  key: string;
  name: string;
  provider_type: ResearchSourceProviderType;
  category: ResearchSourceCategory;
  enabled: boolean;
  critical: boolean;
  priority: number;
  status: ResearchSourceStatus;
  quota_status: string;
  last_checked_at: string | null;
  last_failure_reason: string | null;
  documents_fetched_today: number;
  success_rate: number;
  average_latency_ms: number;
  recent_failure_count: number;
  config_json: Record<string, unknown>;
  provider_mode: ResearchProviderMode;
  missing_configuration: boolean;
  configuration_status: string;
  connection_status: string;
  last_test_result: string | null;
  trend_provider_status: string | null;
  total_runs: number;
  last_run_at: string | null;
  documents_collected: number;
  average_composite_score: number;
  average_trend_score: number;
  confidence_distribution: Record<ResearchConfidenceLevel, number>;
  created_at: string;
  updated_at: string;
};

export type ResearchSourceListResponse = PaginatedResponse<ResearchSource>;

export type ResearchSourceFilters = {
  page?: number;
  pageSize?: number;
  category?: ResearchSourceCategory;
  status?: ResearchSourceStatus;
  enabled?: boolean;
  search?: string;
  sort?: string;
};

export type ResearchSourceUpdatePayload = {
  critical?: boolean;
  priority?: number;
  quota_status?: string;
  config_json?: Record<string, unknown>;
  api_key?: string;
  clear_api_key?: boolean;
};

export type ResearchSourceTestResponse = {
  source: ResearchSource;
  success: boolean;
  message: string;
};
