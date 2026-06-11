import type { CursorPaginatedResponse } from "@/shared/types/pagination";

export type MCPServerStatus =
  | "healthy"
  | "degraded"
  | "broken"
  | "not_configured"
  | "disabled";

export type MCPToolStatus = "enabled" | "disabled" | "deprecated";

export type MCPToolRunStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export type MCPAuthConfig = {
  id: string;
  server_id: string;
  auth_type: string;
  has_secret: boolean;
  masked_label: string | null;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type MCPServer = {
  id: string;
  key: string;
  name: string;
  purpose: string;
  adapter_type: string;
  is_critical: boolean;
  status: MCPServerStatus;
  failure_reason: string | null;
  last_tested_at: string | null;
  last_success_at: string | null;
  failure_count: number;
  circuit_open_until: string | null;
  settings: Record<string, unknown>;
  tool_count: number;
  auth_config: MCPAuthConfig | null;
  created_at: string;
  updated_at: string;
};

export type MCPTool = {
  id: string;
  server_id: string;
  server_key: string;
  key: string;
  display_name: string;
  description: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  auth_required: boolean;
  timeout_ms: number;
  retry_policy: Record<string, unknown>;
  circuit_breaker_policy: Record<string, unknown>;
  is_critical: boolean;
  allowed_callers: string[];
  status: MCPToolStatus;
  created_at: string;
  updated_at: string;
};

export type MCPToolRun = {
  id: string;
  server_id: string;
  tool_id: string;
  server_key: string;
  tool_key: string;
  status: MCPToolRunStatus;
  caller_type: string;
  caller_id: string | null;
  requested_by: string | null;
  entity_type: string | null;
  entity_id: string | null;
  workflow_stage: string | null;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown> | null;
  output_metadata: Record<string, unknown>;
  error_reason: string | null;
  retry_of_run_id: string | null;
  attempt_number: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type MCPToolAuditLog = {
  id: string;
  run_id: string;
  server_id: string;
  tool_id: string;
  action: string;
  actor_id: string | null;
  message: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type MCPToolRunDetail = MCPToolRun & {
  audit_logs: MCPToolAuditLog[];
};

export type MCPServerListResponse = {
  items: MCPServer[];
};

export type MCPToolListResponse = {
  items: MCPTool[];
};

export type MCPToolRunListResponse = CursorPaginatedResponse<MCPToolRun>;

export type MCPToolRunPayload = {
  input_payload?: Record<string, unknown>;
  caller_type?: "workflow" | "agent" | "admin" | "system";
  caller_id?: string | null;
  entity_type?: string | null;
  entity_id?: string | null;
  workflow_stage?: string | null;
};

export type MCPServerTestResponse = {
  server: MCPServer;
  run: MCPToolRun;
  success: boolean;
  message: string;
};
