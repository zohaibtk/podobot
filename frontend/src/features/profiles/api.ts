import { requestJson } from "@/shared/api/httpClient";
import type {
  Profile,
  ProfileDraftPayload,
  ProfileFilters,
  ProfileKind,
  ProfileListResponse,
  ProfileRecommendationsResponse
} from "@/shared/types/series";

function profileQuery(filters: ProfileFilters = {}) {
  const params = new URLSearchParams();
  if (filters.search?.trim()) {
    params.set("search", filters.search.trim());
  }
  if (filters.kind) {
    params.set("kind", filters.kind);
  }
  if (filters.archetype?.trim()) {
    params.set("archetype", filters.archetype.trim());
  }
  if (filters.includeInactive) {
    params.set("include_inactive", "true");
  }
  if (filters.page) {
    params.set("page", String(filters.page));
  }
  if (filters.pageSize) {
    params.set("page_size", String(filters.pageSize));
  }
  if (filters.sort) {
    params.set("sort", filters.sort);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function listProfiles(filters: ProfileFilters = {}) {
  return requestJson<ProfileListResponse>(`/api/v1/profiles${profileQuery(filters)}`);
}

export function searchProfiles(filters: Omit<ProfileFilters, "search"> & { q?: string }) {
  const params = new URLSearchParams();
  if (filters.q?.trim()) {
    params.set("q", filters.q.trim());
  }
  if (filters.kind) {
    params.set("kind", filters.kind);
  }
  if (filters.archetype?.trim()) {
    params.set("archetype", filters.archetype.trim());
  }
  if (filters.page) {
    params.set("page", String(filters.page));
  }
  if (filters.pageSize) {
    params.set("page_size", String(filters.pageSize));
  }
  if (filters.sort) {
    params.set("sort", filters.sort);
  }
  const query = params.toString();
  return requestJson<ProfileListResponse>(`/api/v1/profiles/search${query ? `?${query}` : ""}`);
}

export function getProfile(profileId: string) {
  return requestJson<Profile>(`/api/v1/profiles/${profileId}`);
}

export function createProfile(payload: ProfileDraftPayload) {
  return requestJson<Profile>("/api/v1/profiles", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateProfile(profileId: string, payload: ProfileDraftPayload) {
  return requestJson<Profile>(`/api/v1/profiles/${profileId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function deleteProfile(profileId: string) {
  return requestJson<Profile>(`/api/v1/profiles/${profileId}`, {
    method: "DELETE"
  });
}

export function getProfileRecommendations({
  kind,
  search,
  limit = 5
}: {
  kind: ProfileKind;
  search?: string;
  limit?: number;
}) {
  const params = new URLSearchParams({ kind, limit: String(limit) });
  if (search?.trim()) {
    params.set("search", search.trim());
  }
  return requestJson<ProfileRecommendationsResponse>(
    `/api/v1/profiles/recommendations?${params.toString()}`
  );
}
