import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  assignUserRole,
  cloneRole,
  createPermission,
  createRole,
  deletePermission,
  deleteRole,
  getSettingsWorkspace,
  getRoleMatrix,
  getUserManagement,
  inviteUser,
  listPermissions,
  removeUserRole,
  updatePermission,
  updateRole,
  updateRolePermissions,
  updateUserStatus
} from "@/features/settings/api";
import type {
  InviteUserPayload,
  PermissionPayload,
  RoleClonePayload,
  RolePayload,
  RolePermissionsPayload,
  RoleUpdatePayload,
  UserRolePayload,
  UserStatusPayload
} from "@/shared/types/settings";
import { mutationToast } from "@/shared/toasts/queryToast";

export const SETTINGS_QUERY_KEY = ["settings"] as const;

export function useSettingsWorkspace() {
  return useQuery({
    queryKey: SETTINGS_QUERY_KEY,
    queryFn: getSettingsWorkspace
  });
}

export function useRoleMatrix() {
  return useQuery({
    queryKey: [...SETTINGS_QUERY_KEY, "roles"],
    queryFn: getRoleMatrix
  });
}

export function usePermissionList(params: {
  page?: number;
  pageSize?: number;
  search?: string;
  module?: string;
  sort?: string;
} = {}) {
  return useQuery({
    queryKey: [...SETTINGS_QUERY_KEY, "permissions", params],
    queryFn: () => listPermissions(params)
  });
}

export function useUserManagement(params: {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: string;
  sort?: string;
} = {}) {
  return useQuery({
    queryKey: [...SETTINGS_QUERY_KEY, "users", params],
    queryFn: () => getUserManagement(params)
  });
}

function useSettingsInvalidation() {
  const queryClient = useQueryClient();
  return async () => {
    await queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEY });
  };
}

export function useInviteUser() {
  const invalidate = useSettingsInvalidation();

  return useMutation({
    meta: mutationToast("Sending invite", "Invite sent", "Invite failed"),
    mutationFn: (payload: InviteUserPayload) => inviteUser(payload),
    onSuccess: invalidate
  });
}

export function useCreatePermission() {
  const invalidate = useSettingsInvalidation();

  return useMutation({
    meta: mutationToast("Creating permission", "Permission created", "Permission create failed"),
    mutationFn: (payload: PermissionPayload) => createPermission(payload),
    onSuccess: invalidate
  });
}

export function useUpdatePermission() {
  const invalidate = useSettingsInvalidation();

  return useMutation({
    meta: mutationToast("Saving permission", "Permission saved", "Permission save failed"),
    mutationFn: ({ permissionId, payload }: { permissionId: string; payload: Partial<PermissionPayload> }) =>
      updatePermission(permissionId, payload),
    onSuccess: invalidate
  });
}

export function useDeletePermission() {
  const invalidate = useSettingsInvalidation();

  return useMutation({
    meta: mutationToast("Deleting permission", "Permission deleted", "Permission delete failed"),
    mutationFn: (permissionId: string) => deletePermission(permissionId),
    onSuccess: invalidate
  });
}

export function useCreateRole() {
  const invalidate = useSettingsInvalidation();

  return useMutation({
    meta: mutationToast("Creating role", "Role created", "Role create failed"),
    mutationFn: (payload: RolePayload) => createRole(payload),
    onSuccess: invalidate
  });
}

export function useUpdateRole() {
  const invalidate = useSettingsInvalidation();

  return useMutation({
    meta: mutationToast("Saving role", "Role saved", "Role save failed"),
    mutationFn: ({ roleId, payload }: { roleId: string; payload: RoleUpdatePayload }) =>
      updateRole(roleId, payload),
    onSuccess: invalidate
  });
}

export function useDeleteRole() {
  const invalidate = useSettingsInvalidation();

  return useMutation({
    meta: mutationToast("Deleting role", "Role deleted", "Role delete failed"),
    mutationFn: (roleId: string) => deleteRole(roleId),
    onSuccess: invalidate
  });
}

export function useCloneRole() {
  const invalidate = useSettingsInvalidation();

  return useMutation({
    meta: mutationToast("Cloning role", "Role cloned", "Role clone failed"),
    mutationFn: ({ roleId, payload }: { roleId: string; payload: RoleClonePayload }) =>
      cloneRole(roleId, payload),
    onSuccess: invalidate
  });
}

export function useUpdateRolePermissions() {
  const invalidate = useSettingsInvalidation();

  return useMutation({
    meta: mutationToast("Saving permissions", "Permissions saved", "Permission update failed"),
    mutationFn: ({ roleId, payload }: { roleId: string; payload: RolePermissionsPayload }) =>
      updateRolePermissions(roleId, payload),
    onSuccess: invalidate
  });
}

export function useUpdateUserStatus() {
  const invalidate = useSettingsInvalidation();

  return useMutation({
    meta: mutationToast("Updating user status", "User status updated", "Status update failed"),
    mutationFn: ({ userId, payload }: { userId: string; payload: UserStatusPayload }) =>
      updateUserStatus(userId, payload),
    onSuccess: invalidate
  });
}

export function useAssignUserRole() {
  const invalidate = useSettingsInvalidation();

  return useMutation({
    meta: mutationToast("Assigning role", "Role assigned", "Role assignment failed"),
    mutationFn: ({ userId, payload }: { userId: string; payload: UserRolePayload }) =>
      assignUserRole(userId, payload),
    onSuccess: invalidate
  });
}

export function useRemoveUserRole() {
  const invalidate = useSettingsInvalidation();

  return useMutation({
    meta: mutationToast("Removing role", "Role removed", "Role removal failed"),
    mutationFn: ({ userId, roleId }: { userId: string; roleId: string }) =>
      removeUserRole(userId, roleId),
    onSuccess: invalidate
  });
}
