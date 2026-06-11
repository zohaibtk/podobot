import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PublishingOperationsPage } from "@/features/publishing/PublishingOperationsPage";

const scheduleId = "11111111-1111-1111-1111-111111111111";

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <PublishingOperationsPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function workspacePayload() {
  const channel = channelPayload();
  const item = queueItemPayload();
  const audit = auditPayload();
  return {
    analytics: {
      scheduled_count: 2,
      published_count: 1,
      failed_count: 1,
      cancelled_count: 0,
      retryable_count: 1,
      active_channel_count: 1,
      unhealthy_channel_count: 0,
      audit_event_count: 2,
      webhook_event_count: 1,
      buffer_account_status: "connected",
      warnings: ["1 failed post(s) need recovery."]
    },
    queue: { items: [item], total_count: 1, filters: {} },
    failed: { items: [item], total_count: 1, filters: {} },
    retry_center: { items: [item], total_count: 1, filters: {} },
    channel_health: [
      {
        channel,
        mapped_platforms: ["linkedin"],
        scheduled_count: 2,
        published_count: 1,
        failed_count: 1,
        health_status: "healthy",
        warnings: []
      }
    ],
    timeline: [
      {
        id: "audit:1",
        event_type: "publishing.bulk.retry",
        title: "Publishing Bulk Retry",
        status: "succeeded",
        description: "Publishing action recorded.",
        occurred_at: "2026-06-06T00:00:00Z",
        schedule_id: scheduleId,
        series_id: "22222222-2222-2222-2222-222222222222",
        platform: "linkedin"
      }
    ],
    activity_feed: [
      {
        id: "audit:1",
        event_type: "publishing.bulk.retry",
        title: "Publishing Bulk Retry",
        status: "succeeded",
        description: "Publishing action recorded.",
        occurred_at: "2026-06-06T00:00:00Z",
        schedule_id: scheduleId,
        series_id: "22222222-2222-2222-2222-222222222222",
        platform: "linkedin",
        source: "audit"
      }
    ],
    audit_logs: [audit],
    webhooks: [],
    buffer_account: {
      id: "33333333-3333-3333-3333-333333333333",
      integration_id: null,
      buffer_account_id: "buf-account",
      organization_id: "buf-org",
      name: "PodoBot Buffer",
      status: "connected",
      scopes: ["posts:write"],
      token_expires_at: null,
      connected_at: "2026-06-06T00:00:00Z",
      last_synced_at: "2026-06-06T00:00:00Z",
      rate_limit: {},
      created_at: "2026-06-06T00:00:00Z",
      updated_at: "2026-06-06T00:00:00Z"
    }
  };
}

function queueItemPayload() {
  return {
    id: scheduleId,
    series_id: "22222222-2222-2222-2222-222222222222",
    series_name: "Executive AI Briefings",
    episode_id: "44444444-4444-4444-4444-444444444444",
    episode_number: 1,
    episode_title: "Set the executive frame",
    caption_id: "55555555-5555-5555-5555-555555555555",
    video_kind: "full_episode",
    video_key: "full",
    platform: "linkedin",
    status: "failed",
    buffer_status: "failed",
    buffer_post_id: "buf_post_123",
    scheduled_for: "2026-06-06T12:00:00Z",
    scheduled_caption_text: "Publishing copy",
    failure_reason: "Buffer rejected the post.",
    live_url: null,
    retry_count: 1,
    next_retry_at: null,
    last_synced_at: "2026-06-06T00:00:00Z",
    rate_limit_reset_at: null,
    channel: channelPayload(),
    latest_audit: auditPayload(),
    created_at: "2026-06-06T00:00:00Z",
    updated_at: "2026-06-06T00:00:00Z"
  };
}

function channelPayload() {
  return {
    id: "66666666-6666-6666-6666-666666666666",
    buffer_account_id: "33333333-3333-3333-3333-333333333333",
    buffer_channel_id: "buf-linkedin",
    service: "linkedin",
    name: "PodoBot LinkedIn",
    display_name: "PodoBot LinkedIn",
    avatar_url: null,
    is_enabled: true,
    is_queue_paused: false,
    raw_payload: {},
    last_synced_at: "2026-06-06T00:00:00Z",
    created_at: "2026-06-06T00:00:00Z",
    updated_at: "2026-06-06T00:00:00Z"
  };
}

function auditPayload() {
  return {
    id: "77777777-7777-7777-7777-777777777777",
    schedule_id: scheduleId,
    buffer_account_id: null,
    buffer_channel_id: null,
    action: "publishing.bulk.retry",
    status: "succeeded",
    idempotency_key: "idem",
    request_payload: {},
    response_payload: {},
    error_message: null,
    created_at: "2026-06-06T00:00:00Z"
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("PublishingOperationsPage", () => {
  it("renders queue, failure, channel health, and retries selected rows", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.includes("/api/v1/publishing/bulk/retry")) {
        const body = JSON.parse(String(init?.body));
        return jsonResponse({
          action: "retry",
          requested_count: body.schedule_ids.length,
          succeeded_count: 1,
          failed_count: 0,
          results: [
            {
              schedule_id: scheduleId,
              success: true,
              message: "Retry queued.",
              status: "scheduled"
            }
          ],
          workspace: workspacePayload()
        });
      }
      if (url.includes("/api/v1/publishing/queue")) {
        return jsonResponse({ items: [queueItemPayload()], total_count: 1, filters: {} });
      }
      return jsonResponse(workspacePayload());
    });

    renderPage();

    expect(await screen.findByText("Publishing")).toBeInTheDocument();
    expect(screen.getAllByText("Executive AI Briefings")[0]).toBeInTheDocument();
    expect(screen.getByText("Buffer rejected the post.")).toBeInTheDocument();
    expect(screen.getAllByText("PodoBot LinkedIn").length).toBeGreaterThan(1);

    fireEvent.click(screen.getAllByRole("checkbox")[1]);
    fireEvent.click(screen.getByRole("button", { name: /retry selected/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/publishing/bulk/retry"),
        expect.objectContaining({ method: "POST" })
      );
    });
    expect(await screen.findByText("Retry queued.")).toBeInTheDocument();
  });

  it("stops a queued publishing row and removes it from the queue", async () => {
    let stopped = false;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.includes("/api/v1/publishing/bulk/stop")) {
        const body = JSON.parse(String(init?.body));
        stopped = true;
        return jsonResponse({
          action: "stop",
          requested_count: body.schedule_ids.length,
          succeeded_count: 1,
          failed_count: 0,
          results: [
            {
              schedule_id: scheduleId,
              success: true,
              message: "Publishing stopped and Buffer queue item removed.",
              status: null
            }
          ],
          workspace: workspacePayload()
        });
      }
      if (url.includes("/api/v1/publishing/queue")) {
        return jsonResponse({
          items: stopped ? [] : [queueItemPayload()],
          total_count: stopped ? 0 : 1,
          filters: {}
        });
      }
      const workspace = workspacePayload();
      if (stopped) {
        workspace.queue = { items: [], total_count: 0, filters: {} };
      }
      return jsonResponse(workspace);
    });

    renderPage();

    expect(await screen.findByText("Executive AI Briefings")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /stop publish/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/publishing/bulk/stop"),
        expect.objectContaining({ method: "POST" })
      );
    });
    expect(
      await screen.findByText("Publishing stopped and Buffer queue item removed.")
    ).toBeInTheDocument();
    expect(await screen.findByText("Queue is clear")).toBeInTheDocument();
  });
});

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" }
  });
}
