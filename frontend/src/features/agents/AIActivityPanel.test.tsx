import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AIActivityPanel } from "@/features/agents/AIActivityPanel";

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false }
    }
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AIActivityPanel entityId="11111111-1111-1111-1111-111111111111" entityType="series" />
    </QueryClientProvider>
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("AIActivityPanel", () => {
  it("renders workflow agent history", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [
            {
              id: "run-1",
              agent_id: "agent-1",
              agent_key: "narrative",
              prompt_version_id: "prompt-version-1",
              prompt_key: "narrative.v1",
              prompt_version_number: 1,
              status: "succeeded",
              entity_type: "series",
              entity_id: "11111111-1111-1111-1111-111111111111",
              workflow_stage: "narrative",
              trigger: "generation",
              input_payload: {},
              output_payload: {
                summary: "Generated candidate narratives.",
                needs_approval: true
              },
              output_metadata: { provider: "mock" },
              validation_summary: { status: "passed", needs_approval: true },
              error_reason: null,
              regeneration_reason: null,
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
      )
    );

    renderPanel();

    await waitFor(() => {
      expect(screen.getAllByText("narrative").length).toBeGreaterThan(0);
    });
    expect(screen.getByText("succeeded")).toBeInTheDocument();
    expect(screen.getByText(/narrative.v1 v1/)).toBeInTheDocument();
  });
});
