import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getPublishingAudits,
  getPublishingQueue,
  getPublishingTimeline,
  getPublishingWorkspace,
  retryPublishingRows,
  stopPublishingRows,
  syncPublishingRows
} from "@/features/publishing/api";
import type {
  PublishingBulkActionPayload,
  PublishingOperationsWorkspace,
  PublishingQueue,
  PublishingQueueFilters
} from "@/shared/types/publishing";
import { mutationToast } from "@/shared/toasts/queryToast";

const PUBLISHING_QUERY_KEY = ["publishing"] as const;
const PUBLISHING_STATUS_POLL_MS = 30_000;

export function usePublishingWorkspace() {
  return useQuery({
    queryKey: PUBLISHING_QUERY_KEY,
    queryFn: getPublishingWorkspace,
    refetchInterval: (query) =>
      hasScheduledWorkspaceRows(query.state.data)
        ? PUBLISHING_STATUS_POLL_MS
        : false
  });
}

export function usePublishingQueue(filters: PublishingQueueFilters) {
  return useQuery({
    queryKey: ["publishing", "queue", filters],
    queryFn: () => getPublishingQueue(filters),
    refetchInterval: (query) =>
      hasScheduledQueueRows(query.state.data) ? PUBLISHING_STATUS_POLL_MS : false
  });
}

export function usePublishingAudits(limit = 100) {
  return useQuery({
    queryKey: ["publishing", "audits", limit],
    queryFn: () => getPublishingAudits(limit)
  });
}

export function usePublishingTimeline(limit = 40, cursor?: string | null) {
  return useQuery({
    queryKey: ["publishing", "timeline", limit, cursor],
    queryFn: () => getPublishingTimeline(limit, cursor)
  });
}

export function usePublishingAuditsPage(limit = 40, cursor?: string | null) {
  return useQuery({
    queryKey: ["publishing", "audits", limit, cursor],
    queryFn: () => getPublishingAudits(limit, cursor)
  });
}

function usePublishingInvalidation() {
  const queryClient = useQueryClient();
  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: PUBLISHING_QUERY_KEY }),
      queryClient.invalidateQueries({ queryKey: ["publishing", "queue"] }),
      queryClient.invalidateQueries({ queryKey: ["publishing", "audits"] }),
      queryClient.invalidateQueries({ queryKey: ["series"] })
    ]);
  };
}

export function useRetryPublishingRows() {
  const invalidate = usePublishingInvalidation();

  return useMutation({
    meta: mutationToast("Retrying publishing rows", "Publishing retry queued", "Retry failed"),
    mutationFn: (payload: PublishingBulkActionPayload) => retryPublishingRows(payload),
    onSuccess: invalidate
  });
}

export function useSyncPublishingRows() {
  const invalidate = usePublishingInvalidation();

  return useMutation({
    meta: mutationToast("Syncing publishing status", "Publishing status synced", "Sync failed"),
    mutationFn: (payload: PublishingBulkActionPayload) => syncPublishingRows(payload),
    onSuccess: invalidate
  });
}

export function useStopPublishingRows() {
  const invalidate = usePublishingInvalidation();

  return useMutation({
    meta: mutationToast("Stopping publishing rows", "Publishing rows stopped", "Stop failed"),
    mutationFn: (payload: PublishingBulkActionPayload) => stopPublishingRows(payload),
    onSuccess: invalidate
  });
}

function hasScheduledWorkspaceRows(data: PublishingOperationsWorkspace | undefined) {
  return Boolean(data?.analytics.scheduled_count);
}

function hasScheduledQueueRows(data: PublishingQueue | undefined) {
  return Boolean(data?.items.some((item) => item.status === "scheduled"));
}
