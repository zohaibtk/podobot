import { requestJson } from "@/shared/api/httpClient";
import type {
  ResearchSource,
  ResearchSourceFilters,
  ResearchSourceListResponse,
  ResearchSourceTestResponse,
  ResearchSourceUpdatePayload
} from "@/shared/types/researchSources";
import type {
  BufferOAuthStart,
  BufferWorkspace,
  CaptionPlatform
} from "@/shared/types/series";

function researchSourceQuery(filters: ResearchSourceFilters = {}) {
  const params = new URLSearchParams();
  if (filters.page) {
    params.set("page", String(filters.page));
  }
  if (filters.pageSize) {
    params.set("page_size", String(filters.pageSize));
  }
  if (filters.category) {
    params.set("category", filters.category);
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (typeof filters.enabled === "boolean") {
    params.set("enabled", String(filters.enabled));
  }
  if (filters.search?.trim()) {
    params.set("search", filters.search.trim());
  }
  if (filters.sort) {
    params.set("sort", filters.sort);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function listResearchSources(filters: ResearchSourceFilters = {}) {
  return requestJson<ResearchSourceListResponse>(
    `/api/v1/research/sources${researchSourceQuery(filters)}`
  );
}

export function getResearchSource(sourceId: string) {
  return requestJson<ResearchSource>(`/api/v1/research/sources/${sourceId}`);
}

export function updateResearchSource(sourceId: string, payload: ResearchSourceUpdatePayload) {
  return requestJson<ResearchSource>(`/api/v1/research/sources/${sourceId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function enableResearchSource(sourceId: string) {
  return requestJson<ResearchSource>(`/api/v1/research/sources/${sourceId}/enable`, {
    method: "POST"
  });
}

export function disableResearchSource(sourceId: string) {
  return requestJson<ResearchSource>(`/api/v1/research/sources/${sourceId}/disable`, {
    method: "POST"
  });
}

export function testResearchSource(sourceId: string) {
  return requestJson<ResearchSourceTestResponse>(
    `/api/v1/research/sources/${sourceId}/test`,
    {
      method: "POST"
    }
  );
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

export function updateBufferChannelMapping(
  platform: CaptionPlatform,
  channelId: string
) {
  return requestJson<BufferWorkspace>(`/api/v1/buffer/channel-mappings/${platform}`, {
    method: "PATCH",
    body: JSON.stringify({ channel_id: channelId })
  });
}
