import type { CursorPaginatedResponse } from "@/shared/types/pagination";

export type AgentRunStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "requires_human";

export type PromptVersionStatus = "draft" | "active" | "archived";
export type AgentOutputValidationStatus = "passed" | "warning" | "failed";
export type AgentTokenStatsPeriod = "day" | "week" | "month";

export type Agent = {
  id: string;
  key: string;
  name: string;
  responsibility: string;
  tools: string[];
  required_permission: string | null;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type PromptVersion = {
  id: string;
  prompt_template_id: string;
  agent_id: string;
  prompt_key: string;
  agent_key: string;
  version_number: number;
  template_body: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  status: PromptVersionStatus;
  created_by: string;
  created_at: string;
};

export type PromptTemplate = {
  id: string;
  key: string;
  agent_id: string;
  agent_key: string;
  name: string;
  description: string;
  created_by: string;
  active_version: PromptVersion | null;
  versions: PromptVersion[];
  created_at: string;
  updated_at: string;
};

export type AgentRun = {
  id: string;
  agent_id: string;
  agent_key: string;
  prompt_version_id: string | null;
  prompt_key: string | null;
  prompt_version_number: number | null;
  status: AgentRunStatus;
  entity_type: string | null;
  entity_id: string | null;
  workflow_stage: string | null;
  trigger: string;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown> | null;
  output_metadata: Record<string, unknown>;
  validation_summary: Record<string, unknown>;
  error_reason: string | null;
  regeneration_reason: string | null;
  retry_of_run_id: string | null;
  attempt_number: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentAuditLog = {
  id: string;
  run_id: string;
  agent_id: string;
  action: string;
  actor_id: string | null;
  message: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AgentOutputValidationResult = {
  id: string;
  run_id: string;
  status: AgentOutputValidationStatus;
  checks: Record<string, unknown>[];
  errors: string[];
  created_at: string;
};

export type AgentRunDetail = AgentRun & {
  audit_logs: AgentAuditLog[];
  validation_results: AgentOutputValidationResult[];
};

export type AgentListResponse = {
  items: Agent[];
};

export type PromptListResponse = {
  items: PromptTemplate[];
};

export type AgentRunListResponse = CursorPaginatedResponse<AgentRun>;

export type AgentRunPayload = {
  input_payload?: Record<string, unknown>;
  entity_type?: string | null;
  entity_id?: string | null;
  workflow_stage?: string | null;
  trigger?: string;
  regeneration_reason?: string | null;
};

export type AgentRunRetryPayload = {
  regeneration_reason?: string | null;
  input_payload?: Record<string, unknown> | null;
};

export type PromptVersionPayload = {
  template_body: string;
  input_schema?: Record<string, unknown>;
  output_schema?: Record<string, unknown>;
  status?: PromptVersionStatus;
  created_by?: string;
};

export type AgentTokenTotals = {
  prompt_tokens: number;
  completion_tokens: number;
  cached_tokens: number;
  reasoning_tokens: number;
  total_tokens: number;
  run_count: number;
  tokenized_run_count: number;
  average_tokens_per_run: number;
};

export type AgentTokenUsage = AgentTokenTotals & {
  agent_id: string;
  agent_key: string;
  agent_name: string;
  provider: string | null;
  share_percentage: number;
  last_run_at: string | null;
};

export type AgentTokenTimelinePoint = {
  label: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  run_count: number;
};

export type AgentTokenRequestUsage = {
  id: string;
  agent_id: string;
  agent_key: string;
  agent_name: string;
  provider: string | null;
  status: AgentRunStatus;
  trigger: string;
  entity_type: string | null;
  entity_id: string | null;
  series_id: string | null;
  series_name: string | null;
  workflow_stage: string | null;
  sequence_number: number;
  label: string;
  created_at: string;
  completed_at: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  cached_tokens: number;
  reasoning_tokens: number;
  total_tokens: number;
  estimated_prompt_tokens: number;
  estimated_completion_tokens: number;
  estimated_total_tokens: number;
  display_prompt_tokens: number;
  display_completion_tokens: number;
  display_total_tokens: number;
  is_estimated: boolean;
};

export type AgentTokenStats = {
  period: AgentTokenStatsPeriod;
  generated_at: string;
  window_start: string;
  window_end: string;
  totals: AgentTokenTotals;
  agents: AgentTokenUsage[];
  timeline: AgentTokenTimelinePoint[];
  requests: AgentTokenRequestUsage[];
};
