import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getBufferWorkspace,
  startBufferOAuth,
  syncBufferChannels,
  updateBufferChannelMapping,
  disableResearchSource,
  enableResearchSource,
  getResearchSource,
  listResearchSources,
  testResearchSource,
  updateResearchSource
} from "@/features/integrations/api";
import type {
  ResearchSourceFilters,
  ResearchSourceUpdatePayload
} from "@/shared/types/researchSources";
import type { CaptionPlatform } from "@/shared/types/series";
import { mutationToast } from "@/shared/toasts/queryToast";

export const RESEARCH_SOURCES_QUERY_KEY = ["research-sources"] as const;
export const BUFFER_WORKSPACE_QUERY_KEY = ["buffer", "workspace"] as const;

export function useResearchSourceList(filters: ResearchSourceFilters = {}) {
  return useQuery({
    queryKey: [...RESEARCH_SOURCES_QUERY_KEY, filters],
    queryFn: () => listResearchSources(filters)
  });
}

export function useResearchSource(sourceId: string | undefined) {
  return useQuery({
    queryKey: [...RESEARCH_SOURCES_QUERY_KEY, sourceId],
    queryFn: () => getResearchSource(sourceId as string),
    enabled: Boolean(sourceId)
  });
}

function useResearchSourceInvalidation(sourceId?: string) {
  const queryClient = useQueryClient();

  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: RESEARCH_SOURCES_QUERY_KEY }),
      sourceId
        ? queryClient.invalidateQueries({
            queryKey: [...RESEARCH_SOURCES_QUERY_KEY, sourceId]
          })
        : Promise.resolve()
    ]);
  };
}

export function useUpdateResearchSource(sourceId: string | undefined) {
  const invalidate = useResearchSourceInvalidation(sourceId);

  return useMutation({
    meta: mutationToast("Saving source", "Source saved", "Source save failed"),
    mutationFn: (payload: ResearchSourceUpdatePayload) =>
      updateResearchSource(sourceId as string, payload),
    onSuccess: invalidate
  });
}

export function useEnableResearchSource() {
  const invalidate = useResearchSourceInvalidation();

  return useMutation({
    meta: mutationToast("Enabling source", "Source enabled", "Enable failed"),
    mutationFn: (sourceId: string) => enableResearchSource(sourceId),
    onSuccess: invalidate
  });
}

export function useDisableResearchSource() {
  const invalidate = useResearchSourceInvalidation();

  return useMutation({
    meta: mutationToast("Disabling source", "Source disabled", "Disable failed"),
    mutationFn: (sourceId: string) => disableResearchSource(sourceId),
    onSuccess: invalidate
  });
}

export function useTestResearchSource() {
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Testing source", "Source test complete", "Source test failed"),
    mutationFn: (sourceId: string) => testResearchSource(sourceId),
    onSuccess: async (_result, sourceId) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: RESEARCH_SOURCES_QUERY_KEY }),
        queryClient.invalidateQueries({
          queryKey: [...RESEARCH_SOURCES_QUERY_KEY, sourceId]
        })
      ]);
    }
  });
}

export function useBufferWorkspace(enabled = true) {
  return useQuery({
    queryKey: BUFFER_WORKSPACE_QUERY_KEY,
    queryFn: getBufferWorkspace,
    enabled
  });
}

function useBufferWorkspaceInvalidation() {
  const queryClient = useQueryClient();

  return async () => {
    await queryClient.invalidateQueries({ queryKey: BUFFER_WORKSPACE_QUERY_KEY });
  };
}

export function useStartBufferOAuth() {
  const invalidate = useBufferWorkspaceInvalidation();

  return useMutation({
    meta: mutationToast(
      "Opening Buffer connection",
      "Buffer connection ready",
      "Buffer connection failed"
    ),
    mutationFn: startBufferOAuth,
    onSuccess: async (result) => {
      await invalidate();
      if (result.authorization_url) {
        window.open(result.authorization_url, "_blank", "noopener,noreferrer");
      }
    }
  });
}

export function useSyncBufferChannels() {
  const invalidate = useBufferWorkspaceInvalidation();

  return useMutation({
    meta: mutationToast("Syncing Buffer channels", "Buffer channels synced", "Buffer sync failed"),
    mutationFn: syncBufferChannels,
    onSuccess: invalidate
  });
}

export function useUpdateBufferChannelMapping() {
  const invalidate = useBufferWorkspaceInvalidation();

  return useMutation({
    meta: mutationToast(
      "Saving Buffer channel",
      "Buffer channel saved",
      "Buffer channel failed"
    ),
    mutationFn: ({
      platform,
      channelId
    }: {
      platform: CaptionPlatform;
      channelId: string;
    }) => updateBufferChannelMapping(platform, channelId),
    onSuccess: invalidate
  });
}
