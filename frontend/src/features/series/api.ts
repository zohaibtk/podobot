import { requestJson } from "@/shared/api/httpClient";
import { clearAccessToken, readAccessToken } from "@/features/auth/tokenStorage";
import { env } from "@/shared/config/env";
import type {
  BriefDownload,
  BriefUpdatePayload,
  BufferOAuthStart,
  BufferWorkspace,
  BulkSchedulePayload,
  BriefWorkspace,
  CaptionPlatformCreatePayload,
  CaptionPlatform,
  CaptionUpdatePayload,
  CaptionWorkspace,
  CreateSeriesPayload,
  DiscoveryWorkspace,
  EpisodeAssignmentPayload,
  EpisodeDraftPayload,
  EpisodeDraftGenerationPayload,
  EpisodeDraftGenerationResponse,
  EpisodePlanWorkspace,
  OutlineRegeneratePayload,
  OutlineUpdatePayload,
  OutlineVersionListResponse,
  OutlineWorkspace,
  ProfileListResponse,
  RecordingWorkspace,
  ScheduleCreatePayload,
  ScheduleReschedulePayload,
  ScheduleUpdatePayload,
  ScheduleWorkspace,
  Series,
  SeriesListResponse,
  SignedMediaUrl
} from "@/shared/types/series";

export function listSeries(params: {
  page?: number;
  pageSize?: number;
  search?: string;
  sort?: string;
  status?: string;
} = {}) {
  const query = listQuery({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sort: params.sort,
    status: params.status
  });
  return requestJson<SeriesListResponse>(`/api/v1/series${query}`);
}

export function getSeries(seriesId: string) {
  return requestJson<Series>(`/api/v1/series/${seriesId}`);
}

export function createSeries(payload: CreateSeriesPayload) {
  return requestJson<Series>("/api/v1/series", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function deleteSeries(seriesId: string) {
  return requestJson<void>(`/api/v1/series/${seriesId}`, {
    method: "DELETE"
  });
}

export function listProfiles(params: {
  page?: number;
  pageSize?: number;
  search?: string;
  sort?: string;
} = {}) {
  const query = listQuery(params);
  return requestJson<ProfileListResponse>(`/api/v1/profiles${query}`);
}

function listQuery(params: {
  page?: number;
  pageSize?: number;
  search?: string;
  sort?: string;
  status?: string;
}) {
  const searchParams = new URLSearchParams();
  if (params.page) {
    searchParams.set("page", String(params.page));
  }
  if (params.pageSize) {
    searchParams.set("page_size", String(params.pageSize));
  }
  if (params.search?.trim()) {
    searchParams.set("search", params.search.trim());
  }
  if (params.sort) {
    searchParams.set("sort", params.sort);
  }
  if (params.status) {
    searchParams.set("status", params.status);
  }
  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export function getDiscoveryWorkspace(seriesId: string) {
  return requestJson<DiscoveryWorkspace>(`/api/v1/series/${seriesId}/discovery`);
}

export function runDiscovery(seriesId: string) {
  return requestJson<DiscoveryWorkspace>(`/api/v1/series/${seriesId}/discovery/run`, {
    method: "POST"
  });
}

export function regenerateNarratives(seriesId: string) {
  return requestJson<DiscoveryWorkspace>(`/api/v1/series/${seriesId}/narratives/regenerate`, {
    method: "POST"
  });
}

export function selectNarrative(seriesId: string, narrativeId: string) {
  return requestJson<DiscoveryWorkspace>(
    `/api/v1/series/${seriesId}/narratives/${narrativeId}/select`,
    {
      method: "POST"
    }
  );
}

export function getEpisodePlan(seriesId: string) {
  return requestJson<EpisodePlanWorkspace>(`/api/v1/series/${seriesId}/episodes/plan`);
}

export function addEpisode(seriesId: string, payload: EpisodeDraftPayload) {
  return requestJson<EpisodePlanWorkspace>(`/api/v1/series/${seriesId}/episodes`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function generateEpisodeDraft(
  seriesId: string,
  payload: EpisodeDraftGenerationPayload
) {
  return requestJson<EpisodeDraftGenerationResponse>(
    `/api/v1/series/${seriesId}/episodes/draft`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export function updateEpisode(
  seriesId: string,
  episodeId: string,
  payload: EpisodeDraftPayload
) {
  return requestJson<EpisodePlanWorkspace>(
    `/api/v1/series/${seriesId}/episodes/${episodeId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload)
    }
  );
}

export function removeEpisode(seriesId: string, episodeId: string) {
  return requestJson<EpisodePlanWorkspace>(
    `/api/v1/series/${seriesId}/episodes/${episodeId}`,
    {
      method: "DELETE"
    }
  );
}

export function reorderEpisodes(seriesId: string, episodeIds: string[]) {
  return requestJson<EpisodePlanWorkspace>(`/api/v1/series/${seriesId}/episodes/reorder`, {
    method: "POST",
    body: JSON.stringify({ episode_ids: episodeIds })
  });
}

export function assignEpisodeProfiles(
  seriesId: string,
  episodeId: string,
  payload: EpisodeAssignmentPayload
) {
  return requestJson<EpisodePlanWorkspace>(
    `/api/v1/series/${seriesId}/episodes/${episodeId}/assign`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export function lockEpisodePlan(seriesId: string) {
  return requestJson<EpisodePlanWorkspace>(`/api/v1/series/${seriesId}/episodes/lock`, {
    method: "POST"
  });
}

export function getOutlineWorkspace(seriesId: string) {
  return requestJson<OutlineWorkspace>(`/api/v1/series/${seriesId}/outlines`);
}

export function updateOutline(
  seriesId: string,
  outlineId: string,
  payload: OutlineUpdatePayload
) {
  return requestJson<OutlineWorkspace>(`/api/v1/series/${seriesId}/outlines/${outlineId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function regenerateOutline(
  seriesId: string,
  outlineId: string,
  payload: OutlineRegeneratePayload = {}
) {
  return requestJson<OutlineWorkspace>(
    `/api/v1/series/${seriesId}/outlines/${outlineId}/regenerate`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export function approveOutline(seriesId: string, outlineId: string) {
  return requestJson<OutlineWorkspace>(
    `/api/v1/series/${seriesId}/outlines/${outlineId}/approve`,
    {
      method: "POST"
    }
  );
}

export function listOutlineVersions(
  seriesId: string,
  outlineId: string,
  params: { page?: number; pageSize?: number } = {}
) {
  const query = new URLSearchParams();
  if (params.page) {
    query.set("page", String(params.page));
  }
  if (params.pageSize) {
    query.set("page_size", String(params.pageSize));
  }
  const suffix = query.toString();
  return requestJson<OutlineVersionListResponse>(
    `/api/v1/series/${seriesId}/outlines/${outlineId}/versions${suffix ? `?${suffix}` : ""}`
  );
}

export function getBriefWorkspace(seriesId: string) {
  return requestJson<BriefWorkspace>(`/api/v1/series/${seriesId}/briefs`);
}

export function generateBriefPair(seriesId: string, episodeId: string) {
  return requestJson<BriefWorkspace>(
    `/api/v1/series/${seriesId}/briefs/episodes/${episodeId}/generate`,
    {
      method: "POST"
    }
  );
}

export function approveBriefPair(seriesId: string, episodeId: string) {
  return requestJson<BriefWorkspace>(
    `/api/v1/series/${seriesId}/briefs/episodes/${episodeId}/approve`,
    {
      method: "POST"
    }
  );
}

export function updateBrief(seriesId: string, briefId: string, payload: BriefUpdatePayload) {
  return requestJson<BriefWorkspace>(`/api/v1/series/${seriesId}/briefs/${briefId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function regenerateBrief(seriesId: string, briefId: string) {
  return requestJson<BriefWorkspace>(
    `/api/v1/series/${seriesId}/briefs/${briefId}/regenerate`,
    {
      method: "POST"
    }
  );
}

export async function downloadBrief(seriesId: string, briefId: string): Promise<BriefDownload> {
  const response = await authenticatedFetch(
    `/api/v1/series/${seriesId}/briefs/${briefId}/download`
  );
  if (!response.ok) {
    const message = await responseMessage(response);
    handleAuthFailure(response, message);
    throw new Error(message || `Download failed with status ${response.status}`);
  }

  const disposition = response.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename="([^"]+)"/);
  return {
    blob: await response.blob(),
    filename: match?.[1] ?? "episode-brief.md"
  };
}

export function getRecordingWorkspace(seriesId: string) {
  return requestJson<RecordingWorkspace>(`/api/v1/series/${seriesId}/recordings`);
}

export function uploadEpisodeVideo(seriesId: string, episodeId: string, file: File) {
  return uploadRecordingAsset(
    `/api/v1/series/${seriesId}/recordings/episodes/${episodeId}/video`,
    file
  );
}

export function uploadEpisodeTranscript(seriesId: string, episodeId: string, file: File) {
  return uploadRecordingAsset(
    `/api/v1/series/${seriesId}/recordings/episodes/${episodeId}/transcript`,
    file
  );
}

export function uploadEpisodeThumbnail(seriesId: string, episodeId: string, file: File) {
  return uploadRecordingAsset(
    `/api/v1/series/${seriesId}/recordings/episodes/${episodeId}/thumbnails`,
    file
  );
}

export function selectEpisodeThumbnail(
  seriesId: string,
  episodeId: string,
  thumbnailId: string
) {
  return requestJson<RecordingWorkspace>(
    `/api/v1/series/${seriesId}/recordings/episodes/${episodeId}/thumbnails/${thumbnailId}/select`,
    {
      method: "POST"
    }
  );
}

export function deleteEpisodeThumbnail(
  seriesId: string,
  episodeId: string,
  thumbnailId: string
) {
  return requestJson<RecordingWorkspace>(
    `/api/v1/series/${seriesId}/recordings/episodes/${episodeId}/thumbnails/${thumbnailId}`,
    {
      method: "DELETE"
    }
  );
}

export function requestClipSuggestions(seriesId: string, episodeId: string) {
  return requestJson<RecordingWorkspace>(
    `/api/v1/series/${seriesId}/recordings/episodes/${episodeId}/clip-suggestions`,
    {
      method: "POST"
    }
  );
}

export function uploadClipSuggestionVideo(
  seriesId: string,
  episodeId: string,
  clipSuggestionId: string,
  file: File
) {
  return uploadRecordingAsset(
    `/api/v1/series/${seriesId}/recordings/episodes/${episodeId}/clip-suggestions/${clipSuggestionId}/video`,
    file
  );
}

export function lockEpisodeRecording(seriesId: string, episodeId: string) {
  return requestJson<RecordingWorkspace>(
    `/api/v1/series/${seriesId}/recordings/episodes/${episodeId}/lock`,
    {
      method: "POST"
    }
  );
}

export function getSignedMediaUrl(assetId: string) {
  return requestJson<SignedMediaUrl>(`/api/v1/media/assets/${assetId}/signed-url`);
}

export function getCaptionWorkspace(seriesId: string) {
  return requestJson<CaptionWorkspace>(`/api/v1/series/${seriesId}/captions`);
}

export function addCaptionPlatform(
  seriesId: string,
  episodeId: string,
  payload: CaptionPlatformCreatePayload
) {
  return requestJson<CaptionWorkspace>(
    `/api/v1/series/${seriesId}/captions/episodes/${episodeId}/platforms`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export function generateCaption(seriesId: string, captionId: string) {
  return requestJson<CaptionWorkspace>(
    `/api/v1/series/${seriesId}/captions/${captionId}/generate`,
    {
      method: "POST"
    }
  );
}

export function regenerateCaption(seriesId: string, captionId: string) {
  return requestJson<CaptionWorkspace>(
    `/api/v1/series/${seriesId}/captions/${captionId}/regenerate`,
    {
      method: "POST"
    }
  );
}

export function updateCaption(
  seriesId: string,
  captionId: string,
  payload: CaptionUpdatePayload
) {
  return requestJson<CaptionWorkspace>(`/api/v1/series/${seriesId}/captions/${captionId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function getScheduleWorkspace(seriesId: string) {
  return requestJson<ScheduleWorkspace>(`/api/v1/series/${seriesId}/schedules`);
}

export function createSchedule(seriesId: string, payload: ScheduleCreatePayload) {
  return requestJson<ScheduleWorkspace>(`/api/v1/series/${seriesId}/schedules`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function bulkSchedule(seriesId: string, payload: BulkSchedulePayload) {
  return requestJson<ScheduleWorkspace>(`/api/v1/series/${seriesId}/schedules/bulk`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateSchedule(
  seriesId: string,
  scheduleId: string,
  payload: ScheduleUpdatePayload
) {
  return requestJson<ScheduleWorkspace>(
    `/api/v1/series/${seriesId}/schedules/${scheduleId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload)
    }
  );
}

export function reschedulePost(
  seriesId: string,
  scheduleId: string,
  payload: ScheduleReschedulePayload
) {
  return requestJson<ScheduleWorkspace>(
    `/api/v1/series/${seriesId}/schedules/${scheduleId}/reschedule`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export function cancelSchedule(seriesId: string, scheduleId: string) {
  return requestJson<ScheduleWorkspace>(
    `/api/v1/series/${seriesId}/schedules/${scheduleId}/cancel`,
    {
      method: "POST"
    }
  );
}

export function syncScheduleStatuses(seriesId: string) {
  return requestJson<ScheduleWorkspace>(`/api/v1/series/${seriesId}/schedules/sync`, {
    method: "POST"
  });
}

export function getBufferWorkspace() {
  return requestJson<BufferWorkspace>("/api/v1/buffer/workspace");
}

export function startBufferOAuth() {
  return requestJson<BufferOAuthStart>("/api/v1/buffer/oauth/start", {
    method: "POST"
  });
}

export function syncBufferChannels() {
  return requestJson<BufferWorkspace>("/api/v1/buffer/channels/sync", {
    method: "POST"
  });
}

export function updateBufferChannelMapping(platform: CaptionPlatform, channelId: string) {
  return requestJson<BufferWorkspace>(`/api/v1/buffer/channel-mappings/${platform}`, {
    method: "PATCH",
    body: JSON.stringify({ channel_id: channelId })
  });
}

async function uploadRecordingAsset(path: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await authenticatedFetch(path, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    const message = await responseMessage(response);
    handleAuthFailure(response, message);
    throw new Error(message || `Upload failed with status ${response.status}`);
  }

  return (await response.json()) as RecordingWorkspace;
}

function authenticatedFetch(path: string, options: RequestInit = {}) {
  const token = readAccessToken();
  return fetch(`${env.apiBaseUrl}${path}`, {
    ...options,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {})
    }
  });
}

async function responseMessage(response: Response) {
  const raw = await response.text();
  if (!raw) {
    return "";
  }
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    if (typeof parsed.detail === "string") {
      return parsed.detail;
    }
  } catch {
    return raw;
  }
  return raw;
}

function handleAuthFailure(response: Response, message: string) {
  if (response.status !== 401) {
    return;
  }
  clearAccessToken();
  window.dispatchEvent(
    new CustomEvent("podobot:auth-expired", {
      detail: { message }
    })
  );
}
