import { requestJson } from "@/shared/api/httpClient";
import type {
  PublishingAuditLogResponse,
  PublishingBulkActionPayload,
  PublishingBulkActionResponse,
  PublishingOperationsWorkspace,
  PublishingQueue,
  PublishingQueueFilters,
  PublishingTimelineResponse
} from "@/shared/types/publishing";

export function getPublishingWorkspace() {
  return requestJson<PublishingOperationsWorkspace>("/api/v1/publishing/workspace");
}

export function getPublishingQueue(filters: PublishingQueueFilters = {}) {
  const params = new URLSearchParams();
  filters.statuses?.forEach((status) => params.append("status", status));
  filters.platforms?.forEach((platform) => params.append("platform", platform));
  if (filters.query?.trim()) {
    params.set("query", filters.query.trim());
  }
  if (filters.limit) {
    params.set("limit", String(filters.limit));
  }
  if (filters.page) {
    params.set("page", String(filters.page));
  }
  if (filters.pageSize) {
    params.set("page_size", String(filters.pageSize));
  }
  const query = params.toString();
  return requestJson<PublishingQueue>(`/api/v1/publishing/queue${query ? `?${query}` : ""}`);
}

export function getPublishingTimeline(limit = 40, cursor?: string | null) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) {
    params.set("cursor", cursor);
  }
  return requestJson<PublishingTimelineResponse>(
    `/api/v1/publishing/timeline?${params.toString()}`
  );
}

export function getPublishingAudits(limit = 100, cursor?: string | null) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) {
    params.set("cursor", cursor);
  }
  return requestJson<PublishingAuditLogResponse>(
    `/api/v1/publishing/audits?${params.toString()}`
  );
}

export function retryPublishingRows(payload: PublishingBulkActionPayload) {
  return requestJson<PublishingBulkActionResponse>("/api/v1/publishing/bulk/retry", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function syncPublishingRows(payload: PublishingBulkActionPayload) {
  return requestJson<PublishingBulkActionResponse>("/api/v1/publishing/bulk/sync", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function stopPublishingRows(payload: PublishingBulkActionPayload) {
  return requestJson<PublishingBulkActionResponse>("/api/v1/publishing/bulk/stop", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
