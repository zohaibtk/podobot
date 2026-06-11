import type { Series } from "@/shared/types/series";
import type { CursorPaginatedResponse } from "@/shared/types/pagination";

export type AgentRunStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "requires_human";

export type StrategyIdeaStatus = "proposed" | "in_review" | "dismissed" | "converted";

export type StrategyRun = {
  id: string;
  run_date: string;
  topic: string;
  status: AgentRunStatus;
  started_at: string;
  completed_at: string | null;
  idea_count: number;
  created_at: string;
  updated_at: string;
};

export type StrategyEvidenceSignal = {
  source_name?: string;
  source_key?: string;
  signal_title?: string;
  confidence_score?: number;
  url?: string | null;
  summary?: string;
};

export type StrategyOpportunityBreakdown = {
  research_confidence?: number;
  source_coverage?: number;
  trend_strength?: number;
  audience_fit?: number;
  content_depth?: number;
  competition_signal?: number;
  formula?: string;
  weights?: Record<string, number>;
};

export type StrategyAudienceMix = {
  label: string;
  percentage: number;
  count?: number;
};

export type StrategyAudienceIntelligence = {
  audience?: string;
  source_mix?: StrategyAudienceMix[];
  reason?: string;
  fit_score?: number;
};

export type StrategySeasonPotential = {
  potential_episodes?: number;
  reason?: string;
  research_coverage?: {
    source_count?: number;
    document_count?: number;
    signals_extracted?: number;
  };
  theme_count?: number;
  themes?: string[];
};

export type StrategyTrendIntelligence = {
  trend_available?: boolean;
  trend_source?: string | null;
  fallback_used?: boolean;
  current_trend?: number;
  previous_trend?: number;
  trend_velocity?: number;
  velocity_label?: string;
  message?: string | null;
  failure_reason?: string;
};

export type StrategySourceProposal = {
  research_topic?: string;
  run_date?: string;
  proposal_title?: string;
  proposal_audience?: string;
  proposal_guest_name?: string | null;
  thesis?: string;
  rationale?: string;
  evidence_signals?: StrategyEvidenceSignal[];
  profile_fits?: {
    suggested_host?: {
      persona?: string;
      fit_score?: number;
    };
    suggested_guest?: {
      persona?: string;
      fit_score?: number;
    };
  };
  opportunity_intelligence?: {
    opportunity_score?: number;
    score_breakdown?: StrategyOpportunityBreakdown;
    score_explanation?: string;
    audience_intelligence?: StrategyAudienceIntelligence;
    season_potential?: StrategySeasonPotential;
    trend_intelligence?: StrategyTrendIntelligence;
    sources_found?: number;
    sources_used?: number;
    signals_extracted?: number;
  };
  episode_plan?: Array<{
    title?: string;
    premise?: string;
    segments?: string[];
    hardest_question?: string;
    throughline?: string;
  }>;
  [key: string]: unknown;
};

export type StrategyIdea = {
  id: string;
  run_id: string;
  title: string;
  audience: string;
  description: string;
  proposed_guest_name: string | null;
  thesis: string;
  rationale: string;
  evidence_signals: StrategyEvidenceSignal[];
  source_proposal: StrategySourceProposal;
  confidence_score: number;
  opportunity_score: number;
  opportunity_score_breakdown: StrategyOpportunityBreakdown;
  opportunity_score_explanation: string;
  audience_intelligence: StrategyAudienceIntelligence;
  lifecycle_stage: string;
  season_potential: StrategySeasonPotential;
  trend_intelligence: StrategyTrendIntelligence;
  source_count: number;
  potential_episode_count: number;
  theme_count: number;
  generated_at: string | null;
  status: StrategyIdeaStatus;
  reviewed_at: string | null;
  dismissed_at: string | null;
  converted_at: string | null;
  converted_series_id: string | null;
  run_date: string;
  run_topic: string;
  created_at: string;
  updated_at: string;
};

export type StrategyIdeaGroup = {
  run_id: string;
  run_date: string;
  run_topic: string;
  status: StrategyIdeaStatus;
  ideas: StrategyIdea[];
};

export type StrategyWorkspaceSummary = {
  run_count: number;
  proposed_count: number;
  in_review_count: number;
  dismissed_count: number;
  converted_count: number;
  new_opportunities_count: number;
  high_confidence_count: number;
  hot_trends_count: number;
  converted_this_month_count: number;
  average_opportunity_score: number;
};

export type StrategyWorkspace = {
  runs: StrategyRun[];
  groups: StrategyIdeaGroup[];
  summary: StrategyWorkspaceSummary;
};

export type StrategyRunListResponse = CursorPaginatedResponse<StrategyRun>;

export type StrategyIdeaListResponse = CursorPaginatedResponse<StrategyIdea>;

export type StrategyIdeaActionResponse = {
  workspace: StrategyWorkspace;
  idea: StrategyIdea;
  converted_series: Series | null;
};
