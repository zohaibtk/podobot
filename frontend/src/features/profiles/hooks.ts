import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createProfile,
  deleteProfile,
  getProfile,
  getProfileRecommendations,
  listProfiles,
  updateProfile
} from "@/features/profiles/api";
import type {
  ProfileDraftPayload,
  ProfileFilters,
  ProfileKind
} from "@/shared/types/series";
import { mutationToast } from "@/shared/toasts/queryToast";

export const PROFILE_QUERY_KEY = ["profiles"] as const;

export function useProfileList(filters: ProfileFilters = {}) {
  return useQuery({
    queryKey: [...PROFILE_QUERY_KEY, filters],
    queryFn: () => listProfiles(filters)
  });
}

export function useProfile(profileId: string | undefined) {
  return useQuery({
    queryKey: [...PROFILE_QUERY_KEY, profileId],
    queryFn: () => getProfile(profileId as string),
    enabled: Boolean(profileId)
  });
}

export function useProfileRecommendations({
  kind,
  search,
  limit = 5,
  enabled = true
}: {
  kind: ProfileKind;
  search?: string;
  limit?: number;
  enabled?: boolean;
}) {
  return useQuery({
    queryKey: [...PROFILE_QUERY_KEY, "recommendations", kind, search ?? "", limit],
    queryFn: () => getProfileRecommendations({ kind, search, limit }),
    enabled
  });
}

export function useCreateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Saving profile", "Profile saved", "Profile save failed"),
    mutationFn: (payload: ProfileDraftPayload) => createProfile(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: PROFILE_QUERY_KEY });
    }
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Saving profile", "Profile updated", "Profile update failed"),
    mutationFn: ({ profileId, payload }: { profileId: string; payload: ProfileDraftPayload }) =>
      updateProfile(profileId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: PROFILE_QUERY_KEY });
    }
  });
}

export function useDeleteProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Deleting profile", "Profile deleted", "Profile delete failed"),
    mutationFn: (profileId: string) => deleteProfile(profileId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: PROFILE_QUERY_KEY }),
        queryClient.invalidateQueries({ queryKey: ["series"] })
      ]);
    }
  });
}
