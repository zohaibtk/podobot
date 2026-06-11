import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MCPAdminPanel } from "@/features/mcp/MCPAdminPanel";

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false }
    }
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MCPAdminPanel />
    </QueryClientProvider>
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("MCPAdminPanel", () => {
  it("renders server health, masked auth, tools, and run history entry", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/api/v1/mcp/servers")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: "server-1",
                key: "buffer",
                name: "Buffer",
                purpose: "Publishing and schedule management.",
                adapter_type: "mock",
                is_critical: true,
                status: "healthy",
                failure_reason: null,
                last_tested_at: null,
                last_success_at: null,
                failure_count: 0,
                circuit_open_until: null,
                settings: { mode: "mock" },
                tool_count: 6,
                auth_config: {
                  id: "auth-1",
                  server_id: "server-1",
                  auth_type: "bearer",
                  has_secret: true,
                  masked_label: "buf_****_key",
                  settings: {},
                  created_at: "2026-06-06T00:00:00Z",
                  updated_at: "2026-06-06T00:00:00Z"
                },
                created_at: "2026-06-06T00:00:00Z",
                updated_at: "2026-06-06T00:00:00Z"
              }
            ]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      if (url.includes("/api/v1/mcp/tools")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: "tool-1",
                server_id: "server-1",
                server_key: "buffer",
                key: "buffer.create_scheduled_post",
                display_name: "Create scheduled Buffer post",
                description: "Create one scheduled post.",
                input_schema: { type: "object", required: ["caption_id"] },
                output_schema: { type: "object", required: ["post_id"] },
                auth_required: true,
                timeout_ms: 30000,
                retry_policy: { max_attempts: 2 },
                circuit_breaker_policy: { failure_threshold: 3 },
                is_critical: true,
                allowed_callers: ["workflow", "agent", "system"],
                status: "enabled",
                created_at: "2026-06-06T00:00:00Z",
                updated_at: "2026-06-06T00:00:00Z"
              }
            ]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      return new Response(
        JSON.stringify({
          items: [
            {
              id: "run-1",
              server_id: "server-1",
              tool_id: "tool-1",
              server_key: "buffer",
              tool_key: "buffer.create_scheduled_post",
              status: "succeeded",
              caller_type: "workflow",
              caller_id: "schedule_service",
              requested_by: null,
              entity_type: "series",
              entity_id: "11111111-1111-1111-1111-111111111111",
              workflow_stage: "schedule",
              input_payload: {},
              output_payload: { post_id: "buf_123", status: "queued" },
              output_metadata: { adapter: "mock" },
              error_reason: null,
              retry_of_run_id: null,
              attempt_number: 1,
              started_at: "2026-06-06T00:00:00Z",
              completed_at: "2026-06-06T00:00:00Z",
              created_at: "2026-06-06T00:00:00Z",
              updated_at: "2026-06-06T00:00:00Z"
            }
          ]
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    });

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("Buffer")).toBeInTheDocument();
    });
    expect(screen.getByText("masked auth")).toBeInTheDocument();
    expect(screen.getByText("Create scheduled Buffer post")).toBeInTheDocument();
    expect(screen.getByText("buffer.create_scheduled_post")).toBeInTheDocument();
  });
});
