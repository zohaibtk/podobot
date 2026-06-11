import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  addCaptionPlatform,
  addEpisode,
  approveBriefPair,
  approveOutline,
  assignEpisodeProfiles,
  bulkSchedule,
  cancelSchedule,
  createSeries,
  createSchedule,
  deleteEpisodeThumbnail,
  downloadBrief,
  generateBriefPair,
  generateCaption,
  deleteSeries,
  getBriefWorkspace,
  getBufferWorkspace,
  getCaptionWorkspace,
  getEpisodePlan,
  generateEpisodeDraft,
  getDiscoveryWorkspace,
  getOutlineWorkspace,
  getRecordingWorkspace,
  getScheduleWorkspace,
  getSeries,
  listProfiles,
  regenerateBrief,
  regenerateCaption,
  regenerateOutline,
  listSeries,
  lockEpisodeRecording,
  lockEpisodePlan,
  removeEpisode,
  regenerateNarratives,
  reorderEpisodes,
  runDiscovery,
  reschedulePost,
  requestClipSuggestions,
  selectNarrative,
  selectEpisodeThumbnail,
  startBufferOAuth,
  syncScheduleStatuses,
  syncBufferChannels,
  updateBrief,
  updateBufferChannelMapping,
  updateCaption,
  updateSchedule,
  updateOutline,
  updateEpisode,
  uploadClipSuggestionVideo,
  uploadEpisodeThumbnail,
  uploadEpisodeTranscript,
  uploadEpisodeVideo
} from "@/features/series/api";
import type {
  BriefUpdatePayload,
  BulkSchedulePayload,
  CaptionPlatformCreatePayload,
  CaptionPlatform,
  CaptionUpdatePayload,
  CreateSeriesPayload,
  EpisodeAssignmentPayload,
  EpisodeDraftPayload,
  EpisodeDraftGenerationPayload,
  OutlineRegeneratePayload,
  OutlineUpdatePayload,
  ScheduleCreatePayload,
  ScheduleReschedulePayload,
  ScheduleUpdatePayload
} from "@/shared/types/series";
import { mutationToast } from "@/shared/toasts/queryToast";

const SERIES_QUERY_KEY = ["series"] as const;

export function useSeriesList(params: {
  page?: number;
  pageSize?: number;
  search?: string;
  sort?: string;
  status?: string;
} = {}) {
  return useQuery({
    queryKey: [...SERIES_QUERY_KEY, params],
    queryFn: () => listSeries(params)
  });
}

export function useSeries(seriesId: string | undefined) {
  return useQuery({
    queryKey: ["series", seriesId],
    queryFn: () => getSeries(seriesId as string),
    enabled: Boolean(seriesId)
  });
}

export function useCreateSeries() {
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Creating series", "Series created", "Series create failed"),
    mutationFn: (payload: CreateSeriesPayload) => createSeries(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: SERIES_QUERY_KEY });
    }
  });
}

export function useDeleteSeries() {
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Deleting series", "Series deleted", "Series delete failed"),
    mutationFn: (seriesId: string) => deleteSeries(seriesId),
    onSuccess: async (_result, seriesId) => {
      queryClient.removeQueries({ queryKey: ["series", seriesId] });
      await queryClient.invalidateQueries({ queryKey: SERIES_QUERY_KEY });
    }
  });
}

export function useDiscoveryWorkspace(seriesId: string | undefined) {
  return useQuery({
    queryKey: ["series", seriesId, "discovery"],
    queryFn: () => getDiscoveryWorkspace(seriesId as string),
    enabled: Boolean(seriesId)
  });
}

export function useRunDiscovery(seriesId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Running discovery", "Discovery updated", "Discovery failed"),
    mutationFn: () => runDiscovery(seriesId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["series"] }),
        queryClient.invalidateQueries({ queryKey: ["series", seriesId] }),
        queryClient.invalidateQueries({ queryKey: ["series", seriesId, "discovery"] }),
        queryClient.invalidateQueries({ queryKey: ["research-runs"] })
      ]);
    }
  });
}

export function useRegenerateNarratives(seriesId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Regenerating narratives", "Narratives refreshed", "Narrative generation failed"),
    mutationFn: () => regenerateNarratives(seriesId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["series", seriesId] }),
        queryClient.invalidateQueries({ queryKey: ["series", seriesId, "discovery"] })
      ]);
    }
  });
}

export function useSelectNarrative(seriesId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Selecting narrative", "Narrative selected", "Narrative selection failed"),
    mutationFn: (narrativeId: string) => selectNarrative(seriesId, narrativeId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["series"] }),
        queryClient.invalidateQueries({ queryKey: ["series", seriesId] }),
        queryClient.invalidateQueries({ queryKey: ["series", seriesId, "discovery"] }),
        queryClient.invalidateQueries({ queryKey: ["series", seriesId, "episode-plan"] })
      ]);
    }
  });
}

export function useProfiles() {
  return useQuery({
    queryKey: ["profiles"],
    queryFn: () => listProfiles()
  });
}

export function useEpisodePlan(seriesId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ["series", seriesId, "episode-plan"],
    queryFn: () => getEpisodePlan(seriesId as string),
    enabled: Boolean(seriesId) && enabled
  });
}

function useEpisodePlanInvalidation(seriesId: string) {
  const queryClient = useQueryClient();

  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["series"] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId, "episode-plan"] })
    ]);
  };
}

export function useAddEpisode(seriesId: string) {
  const invalidate = useEpisodePlanInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Adding episode", "Episode added", "Episode add failed"),
    mutationFn: (payload: EpisodeDraftPayload) => addEpisode(seriesId, payload),
    onSuccess: invalidate
  });
}

export function useUpdateEpisode(seriesId: string) {
  const invalidate = useEpisodePlanInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Saving episode", "Episode saved", "Episode save failed"),
    mutationFn: ({ episodeId, payload }: { episodeId: string; payload: EpisodeDraftPayload }) =>
      updateEpisode(seriesId, episodeId, payload),
    onSuccess: invalidate
  });
}

export function useGenerateEpisodeDraft(seriesId: string) {
  return useMutation({
    meta: mutationToast("Generating episode draft", "Episode draft ready", "Episode draft failed"),
    mutationFn: (payload: EpisodeDraftGenerationPayload) =>
      generateEpisodeDraft(seriesId, payload)
  });
}

export function useRemoveEpisode(seriesId: string) {
  const invalidate = useEpisodePlanInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Removing episode", "Episode removed", "Episode remove failed"),
    mutationFn: (episodeId: string) => removeEpisode(seriesId, episodeId),
    onSuccess: invalidate
  });
}

export function useReorderEpisodes(seriesId: string) {
  const invalidate = useEpisodePlanInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Reordering episodes", "Episode order saved", "Episode reorder failed"),
    mutationFn: (episodeIds: string[]) => reorderEpisodes(seriesId, episodeIds),
    onSuccess: invalidate
  });
}

export function useAssignEpisodeProfiles(seriesId: string) {
  const invalidate = useEpisodePlanInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Assigning personas", "Personas assigned", "Persona assignment failed"),
    mutationFn: ({
      episodeId,
      payload
    }: {
      episodeId: string;
      payload: EpisodeAssignmentPayload;
    }) => assignEpisodeProfiles(seriesId, episodeId, payload),
    onSuccess: invalidate
  });
}

export function useLockEpisodePlan(seriesId: string) {
  const invalidate = useEpisodePlanInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Locking plan", "Plan locked", "Plan lock failed"),
    mutationFn: () => lockEpisodePlan(seriesId),
    onSuccess: invalidate
  });
}

export function useOutlineWorkspace(seriesId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ["series", seriesId, "outlines"],
    queryFn: () => getOutlineWorkspace(seriesId as string),
    enabled: Boolean(seriesId) && enabled
  });
}

function useOutlineInvalidation(seriesId: string) {
  const queryClient = useQueryClient();

  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["series"] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId, "episode-plan"] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId, "outlines"] })
    ]);
  };
}

export function useUpdateOutline(seriesId: string) {
  const invalidate = useOutlineInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Saving outline", "Outline saved", "Outline save failed"),
    mutationFn: ({
      outlineId,
      payload
    }: {
      outlineId: string;
      payload: OutlineUpdatePayload;
    }) => updateOutline(seriesId, outlineId, payload),
    onSuccess: invalidate
  });
}

export function useRegenerateOutline(seriesId: string) {
  const invalidate = useOutlineInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Regenerating outline", "Outline regenerated", "Outline regeneration failed"),
    mutationFn: ({
      outlineId,
      payload
    }: {
      outlineId: string;
      payload?: OutlineRegeneratePayload;
    }) => regenerateOutline(seriesId, outlineId, payload),
    onSuccess: invalidate
  });
}

export function useApproveOutline(seriesId: string) {
  const invalidate = useOutlineInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Approving outline", "Outline approved", "Outline approval failed"),
    mutationFn: (outlineId: string) => approveOutline(seriesId, outlineId),
    onSuccess: invalidate
  });
}

export function useBriefWorkspace(seriesId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ["series", seriesId, "briefs"],
    queryFn: () => getBriefWorkspace(seriesId as string),
    enabled: Boolean(seriesId) && enabled
  });
}

function useBriefInvalidation(seriesId: string) {
  const queryClient = useQueryClient();

  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["series"] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId, "episode-plan"] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId, "outlines"] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId, "briefs"] })
    ]);
  };
}

export function useGenerateBriefPair(seriesId: string) {
  const invalidate = useBriefInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Generating briefs", "Briefs generated", "Brief generation failed"),
    mutationFn: (episodeId: string) => generateBriefPair(seriesId, episodeId),
    onSuccess: invalidate
  });
}

export function useUpdateBrief(seriesId: string) {
  const invalidate = useBriefInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Saving brief", "Brief saved", "Brief save failed"),
    mutationFn: ({ briefId, payload }: { briefId: string; payload: BriefUpdatePayload }) =>
      updateBrief(seriesId, briefId, payload),
    onSuccess: invalidate
  });
}

export function useRegenerateBrief(seriesId: string) {
  const invalidate = useBriefInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Regenerating brief", "Brief regenerated", "Brief regeneration failed"),
    mutationFn: (briefId: string) => regenerateBrief(seriesId, briefId),
    onSuccess: invalidate
  });
}

export function useApproveBriefPair(seriesId: string) {
  const invalidate = useBriefInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Approving brief pair", "Brief pair approved", "Brief approval failed"),
    mutationFn: (episodeId: string) => approveBriefPair(seriesId, episodeId),
    onSuccess: invalidate
  });
}

export function useDownloadBrief(seriesId: string) {
  return useMutation({
    meta: mutationToast("Preparing brief download", "Brief download ready", "Brief download failed"),
    mutationFn: (briefId: string) => downloadBrief(seriesId, briefId)
  });
}

export function useRecordingWorkspace(seriesId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ["series", seriesId, "recordings"],
    queryFn: () => getRecordingWorkspace(seriesId as string),
    enabled: Boolean(seriesId) && enabled
  });
}

function useRecordingInvalidation(seriesId: string) {
  const queryClient = useQueryClient();

  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["series"] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId, "episode-plan"] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId, "briefs"] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId, "recordings"] })
    ]);
  };
}

export function useUploadEpisodeVideo(seriesId: string) {
  const invalidate = useRecordingInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Uploading video", "Video uploaded", "Video upload failed"),
    mutationFn: ({ episodeId, file }: { episodeId: string; file: File }) =>
      uploadEpisodeVideo(seriesId, episodeId, file),
    onSuccess: invalidate
  });
}

export function useUploadEpisodeTranscript(seriesId: string) {
  const invalidate = useRecordingInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Uploading transcript", "Transcript uploaded", "Transcript upload failed"),
    mutationFn: ({ episodeId, file }: { episodeId: string; file: File }) =>
      uploadEpisodeTranscript(seriesId, episodeId, file),
    onSuccess: invalidate
  });
}

export function useUploadEpisodeThumbnail(seriesId: string) {
  const invalidate = useRecordingInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Uploading thumbnail", "Thumbnail uploaded", "Thumbnail upload failed"),
    mutationFn: ({ episodeId, file }: { episodeId: string; file: File }) =>
      uploadEpisodeThumbnail(seriesId, episodeId, file),
    onSuccess: invalidate
  });
}

export function useSelectEpisodeThumbnail(seriesId: string) {
  const invalidate = useRecordingInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Selecting thumbnail", "Thumbnail selected", "Thumbnail selection failed"),
    mutationFn: ({
      episodeId,
      thumbnailId
    }: {
      episodeId: string;
      thumbnailId: string;
    }) => selectEpisodeThumbnail(seriesId, episodeId, thumbnailId),
    onSuccess: invalidate
  });
}

export function useDeleteEpisodeThumbnail(seriesId: string) {
  const invalidate = useRecordingInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Deleting thumbnail", "Thumbnail deleted", "Thumbnail delete failed"),
    mutationFn: ({
      episodeId,
      thumbnailId
    }: {
      episodeId: string;
      thumbnailId: string;
    }) => deleteEpisodeThumbnail(seriesId, episodeId, thumbnailId),
    onSuccess: invalidate
  });
}

export function useRequestClipSuggestions(seriesId: string) {
  const invalidate = useRecordingInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Finding clip ideas", "Clip ideas ready", "Clip suggestion failed"),
    mutationFn: (episodeId: string) => requestClipSuggestions(seriesId, episodeId),
    onSuccess: invalidate
  });
}

export function useUploadClipSuggestionVideo(seriesId: string) {
  const invalidate = useRecordingInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Uploading clip", "Clip uploaded", "Clip upload failed"),
    mutationFn: ({
      clipSuggestionId,
      episodeId,
      file
    }: {
      clipSuggestionId: string;
      episodeId: string;
      file: File;
    }) => uploadClipSuggestionVideo(seriesId, episodeId, clipSuggestionId, file),
    onSuccess: invalidate
  });
}

export function useLockEpisodeRecording(seriesId: string) {
  const invalidate = useRecordingInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Locking recording", "Recording locked", "Recording lock failed"),
    mutationFn: (episodeId: string) => lockEpisodeRecording(seriesId, episodeId),
    onSuccess: invalidate
  });
}

export function useCaptionWorkspace(seriesId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ["series", seriesId, "captions"],
    queryFn: () => getCaptionWorkspace(seriesId as string),
    enabled: Boolean(seriesId) && enabled
  });
}

function useCaptionInvalidation(seriesId: string) {
  const queryClient = useQueryClient();

  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["series"] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId, "episode-plan"] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId, "recordings"] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId, "captions"] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId, "schedules"] })
    ]);
  };
}

export function useAddCaptionPlatform(seriesId: string) {
  const invalidate = useCaptionInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Adding caption platform", "Caption platform added", "Caption platform failed"),
    mutationFn: ({
      episodeId,
      payload
    }: {
      episodeId: string;
      payload: CaptionPlatformCreatePayload;
    }) => addCaptionPlatform(seriesId, episodeId, payload),
    onSuccess: invalidate
  });
}

export function useGenerateCaption(seriesId: string) {
  const invalidate = useCaptionInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Generating caption", "Caption generated", "Caption generation failed"),
    mutationFn: (captionId: string) => generateCaption(seriesId, captionId),
    onSuccess: invalidate
  });
}

export function useRegenerateCaption(seriesId: string) {
  const invalidate = useCaptionInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Regenerating caption", "Caption regenerated", "Caption regeneration failed"),
    mutationFn: (captionId: string) => regenerateCaption(seriesId, captionId),
    onSuccess: invalidate
  });
}

export function useUpdateCaption(seriesId: string) {
  const invalidate = useCaptionInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Saving caption", "Caption saved", "Caption save failed"),
    mutationFn: ({
      captionId,
      payload
    }: {
      captionId: string;
      payload: CaptionUpdatePayload;
    }) => updateCaption(seriesId, captionId, payload),
    onSuccess: invalidate
  });
}

export function useScheduleWorkspace(seriesId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ["series", seriesId, "schedules"],
    queryFn: () => getScheduleWorkspace(seriesId as string),
    enabled: Boolean(seriesId) && enabled
  });
}

function useScheduleInvalidation(seriesId: string) {
  const queryClient = useQueryClient();

  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["series"] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId, "episode-plan"] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId, "captions"] }),
      queryClient.invalidateQueries({ queryKey: ["series", seriesId, "schedules"] })
    ]);
  };
}

export function useCreateSchedule(seriesId: string) {
  const invalidate = useScheduleInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Scheduling post", "Post scheduled", "Scheduling failed"),
    mutationFn: (payload: ScheduleCreatePayload) => createSchedule(seriesId, payload),
    onSuccess: invalidate
  });
}

export function useBulkSchedule(seriesId: string) {
  const invalidate = useScheduleInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Scheduling ready posts", "Posts scheduled", "Bulk schedule failed"),
    mutationFn: (payload: BulkSchedulePayload) => bulkSchedule(seriesId, payload),
    onSuccess: invalidate
  });
}

export function useUpdateSchedule(seriesId: string) {
  const invalidate = useScheduleInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Saving schedule", "Schedule saved", "Schedule save failed"),
    mutationFn: ({
      scheduleId,
      payload
    }: {
      scheduleId: string;
      payload: ScheduleUpdatePayload;
    }) => updateSchedule(seriesId, scheduleId, payload),
    onSuccess: invalidate
  });
}

export function useReschedulePost(seriesId: string) {
  const invalidate = useScheduleInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Rescheduling post", "Post rescheduled", "Reschedule failed"),
    mutationFn: ({
      scheduleId,
      payload
    }: {
      scheduleId: string;
      payload: ScheduleReschedulePayload;
    }) => reschedulePost(seriesId, scheduleId, payload),
    onSuccess: invalidate
  });
}

export function useCancelSchedule(seriesId: string) {
  const invalidate = useScheduleInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Cancelling schedule", "Schedule cancelled", "Cancel failed"),
    mutationFn: (scheduleId: string) => cancelSchedule(seriesId, scheduleId),
    onSuccess: invalidate
  });
}

export function useSyncScheduleStatuses(seriesId: string) {
  const invalidate = useScheduleInvalidation(seriesId);

  return useMutation({
    meta: mutationToast("Syncing schedules", "Schedules synced", "Schedule sync failed"),
    mutationFn: () => syncScheduleStatuses(seriesId),
    onSuccess: invalidate
  });
}

export function useBufferWorkspace(enabled = true) {
  return useQuery({
    queryKey: ["buffer", "workspace"],
    queryFn: getBufferWorkspace,
    enabled
  });
}

export function useStartBufferOAuth(seriesId: string) {
  const invalidate = useScheduleInvalidation(seriesId);
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Opening Buffer connection", "Buffer connection ready", "Buffer connection failed"),
    mutationFn: startBufferOAuth,
    onSuccess: async (result) => {
      await Promise.all([
        invalidate(),
        queryClient.invalidateQueries({ queryKey: ["buffer", "workspace"] })
      ]);
      if (result.authorization_url) {
        window.open(result.authorization_url, "_blank", "noopener,noreferrer");
      }
    }
  });
}

export function useSyncBufferChannels(seriesId: string) {
  const invalidate = useScheduleInvalidation(seriesId);
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Syncing Buffer channels", "Buffer channels synced", "Buffer sync failed"),
    mutationFn: syncBufferChannels,
    onSuccess: async () => {
      await Promise.all([
        invalidate(),
        queryClient.invalidateQueries({ queryKey: ["buffer", "workspace"] })
      ]);
    }
  });
}

export function useUpdateBufferChannelMapping(seriesId: string) {
  const invalidate = useScheduleInvalidation(seriesId);
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Saving channel mapping", "Channel mapping saved", "Channel mapping failed"),
    mutationFn: ({
      platform,
      channelId
    }: {
      platform: CaptionPlatform;
      channelId: string;
    }) => updateBufferChannelMapping(platform, channelId),
    onSuccess: async () => {
      await Promise.all([
        invalidate(),
        queryClient.invalidateQueries({ queryKey: ["buffer", "workspace"] })
      ]);
    }
  });
}
