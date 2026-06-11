export type DashboardRange = "today" | "7d" | "30d" | "90d" | "custom";
export type DashboardGroupBy = "hour" | "day" | "week" | "month";
export type DashboardProvider = "real";
export type TrendDirection = "up" | "down" | "flat";
export type Priority = "high" | "medium" | "low";

export type DashboardMeta = {
  generated_at: string;
  range: DashboardRange;
  group_by: DashboardGroupBy;
  provider: DashboardProvider;
  window_start: string;
  window_end: string;
};

export type DashboardKpi = {
  key: string;
  label: string;
  value: number;
  display_value: string;
  delta: number;
  delta_label: string;
  trend: TrendDirection;
  sparkline: number[];
};

export type PipelineStage = {
  stage: string;
  count: number;
  delta: number;
  is_bottleneck: boolean;
};

export type ConfidencePoint = {
  label: string;
  average_confidence: number;
  previous_confidence: number;
};

export type SourceDistribution = {
  source: string;
  documents: number;
  percentage: number;
};

export type TrendingTheme = {
  theme: string;
  score: number;
  growth: number;
};

export type PublishingPerformance = {
  status: string;
  count: number;
  percentage: number;
};

export type ResearchOverview = {
  sources_analyzed: number;
  signals_extracted: number;
  avg_confidence: number;
  top_trend: string;
};

export type SeriesVelocityPoint = {
  label: string;
  series: number;
  previous_series: number;
};

export type EpisodeVelocityPoint = {
  label: string;
  episodes: number;
  previous_episodes: number;
};

export type PublishingVelocityPoint = {
  label: string;
  scheduled: number;
  published: number;
  failed: number;
};

export type CalendarItem = {
  id: string;
  title: string;
  platform: string;
  status: string;
  scheduled_for: string;
};

export type PublishingCalendarDay = {
  date: string;
  items: CalendarItem[];
};

export type StrategyOpportunity = {
  id: string;
  title: string;
  confidence: number;
  trend: string;
  source_count: number;
  status: string;
};

export type ActionQueueItem = {
  id: string;
  priority: Priority;
  type: string;
  entity: string;
  quick_action: string;
  href: string | null;
};

export type SourceHealth = {
  id: string;
  source: string;
  health: string;
  latency_ms: number;
  success_rate: number;
  documents_collected: number;
  last_failure: string | null;
};

export type RecentResearchRun = {
  id: string;
  query: string;
  run_type: string;
  status: string;
  sources_used: number;
  documents_found: number;
  signals_extracted: number;
  avg_confidence: number;
  duration_ms: number | null;
  created_at: string;
};

export type AgentActivity = {
  id: string;
  agent_name: string;
  status: string;
  started_at: string | null;
  duration_ms: number | null;
  related_entity: string;
  href: string | null;
};

export type DashboardAnalytics = {
  meta: DashboardMeta;
  kpis: DashboardKpi[];
  pipeline: PipelineStage[];
  research_confidence: ConfidencePoint[];
  source_distribution: SourceDistribution[];
  trending_themes: TrendingTheme[];
  publishing_performance: PublishingPerformance[];
  research_overview: ResearchOverview;
  series_velocity: SeriesVelocityPoint[];
  episode_velocity: EpisodeVelocityPoint[];
  publishing_velocity: PublishingVelocityPoint[];
  publishing_calendar: PublishingCalendarDay[];
  strategy_opportunities: StrategyOpportunity[];
  action_queue: ActionQueueItem[];
  source_health: SourceHealth[];
  recent_research_runs: RecentResearchRun[];
  agent_activity: AgentActivity[];
};

export type DashboardAnalyticsQuery = {
  range: DashboardRange;
  groupBy?: DashboardGroupBy;
  startDate?: string;
  endDate?: string;
};
