import { requestJson } from "@/shared/api/httpClient";
import type {
  InviteUserPayload,
  Permission,
  PermissionList,
  PermissionPayload,
  Role,
  RoleClonePayload,
  RoleMatrix,
  RolePayload,
  RolePermissionsPayload,
  RoleUpdatePayload,
  SettingsWorkspace,
  UserRolePayload,
  UserInvitation,
  UserManagement,
  UserStatusPayload,
  WorkspaceUser
} from "@/shared/types/settings";

export function getSettingsWorkspace() {
  return requestJson<SettingsWorkspace>("/api/v1/settings");
}

export function getRoleMatrix() {
  return requestJson<RoleMatrix>("/api/v1/settings/roles");
}

export function listPermissions(params: {
  page?: number;
  pageSize?: number;
  search?: string;
  module?: string;
  sort?: string;
} = {}) {
  const query = offsetQuery(params);
  return requestJson<PermissionList>(`/api/v1/settings/permissions${query}`);
}

export function createPermission(payload: PermissionPayload) {
  return requestJson<Permission>("/api/v1/settings/permissions", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updatePermission(permissionId: string, payload: Partial<PermissionPayload>) {
  return requestJson<Permission>(`/api/v1/settings/permissions/${permissionId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function deletePermission(permissionId: string) {
  return requestJson<void>(`/api/v1/settings/permissions/${permissionId}`, {
    method: "DELETE"
  });
}

export function createRole(payload: RolePayload) {
  return requestJson<Role>("/api/v1/settings/roles", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateRole(roleId: string, payload: RoleUpdatePayload) {
  return requestJson<Role>(`/api/v1/settings/roles/${roleId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function deleteRole(roleId: string) {
  return requestJson<void>(`/api/v1/settings/roles/${roleId}`, {
    method: "DELETE"
  });
}

export function cloneRole(roleId: string, payload: RoleClonePayload) {
  return requestJson<Role>(`/api/v1/settings/roles/${roleId}/clone`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateRolePermissions(roleId: string, payload: RolePermissionsPayload) {
  return requestJson<RoleMatrix>(`/api/v1/settings/roles/${roleId}/permissions`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getUserManagement(params: {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: string;
  sort?: string;
} = {}) {
  const query = offsetQuery(params);
  return requestJson<UserManagement>(`/api/v1/settings/users${query}`);
}

export function inviteUser(payload: InviteUserPayload) {
  return requestJson<UserInvitation>("/api/v1/settings/users/invitations", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateUserStatus(userId: string, payload: UserStatusPayload) {
  return requestJson<WorkspaceUser>(`/api/v1/settings/users/${userId}/status`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function assignUserRole(userId: string, payload: UserRolePayload) {
  return requestJson<WorkspaceUser>(`/api/v1/settings/users/${userId}/roles`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function removeUserRole(userId: string, roleId: string) {
  return requestJson<WorkspaceUser>(`/api/v1/settings/users/${userId}/roles/${roleId}`, {
    method: "DELETE"
  });
}

function offsetQuery(params: {
  page?: number;
  pageSize?: number;
  search?: string;
  module?: string;
  status?: string;
  sort?: string;
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
  if (params.module) {
    searchParams.set("module", params.module);
  }
  if (params.status) {
    searchParams.set("status", params.status);
  }
  if (params.sort) {
    searchParams.set("sort", params.sort);
  }
  const query = searchParams.toString();
  return query ? `?${query}` : "";
}
