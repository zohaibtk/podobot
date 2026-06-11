import type { PaginatedResponse } from "@/shared/types/pagination";

export type WorkspaceUserStatus = "active" | "invited" | "suspended";
export type UserInvitationStatus = "pending" | "accepted" | "revoked" | "expired";

export type Role = {
  id: string;
  key: string;
  name: string;
  description: string;
  is_system: boolean;
  is_assignable: boolean;
  created_at: string;
  updated_at: string;
};

export type Permission = {
  id: string;
  key: string;
  module: string;
  action: string;
  label: string;
  description: string;
  is_system: boolean;
  created_at: string;
  updated_at: string | null;
};

export type PermissionGroup = {
  module: string;
  permissions: Permission[];
};

export type PermissionList = PaginatedResponse<Permission> & {
  groups: PermissionGroup[];
};

export type RolePermissionCell = {
  role_id: string;
  role_key: string;
  role_name: string;
  is_allowed: boolean;
};

export type PermissionMatrixRow = {
  permission: Permission;
  role_permissions: RolePermissionCell[];
};

export type RoleMatrix = {
  roles: Role[];
  rows: PermissionMatrixRow[];
  modules: string[];
  grouped_permissions: PermissionGroup[];
  prototype_notice: string;
};

export type WorkspaceUser = {
  id: string;
  email: string;
  full_name: string | null;
  role: Role;
  roles: Role[];
  effective_permissions: string[];
  status: WorkspaceUserStatus;
  invited_at: string | null;
  last_active_at: string | null;
  created_at: string;
  updated_at: string;
};

export type UserInvitation = {
  id: string;
  email: string;
  role: Role;
  status: UserInvitationStatus;
  invited_by: string;
  created_user_id: string | null;
  created_at: string;
  updated_at: string;
};

export type UserManagement = PaginatedResponse<WorkspaceUser> & {
  users: WorkspaceUser[];
  invitations: UserInvitation[];
};

export type SettingsWorkspace = {
  tab_names: string[];
  role_matrix: RoleMatrix;
  users: WorkspaceUser[];
  invitations: UserInvitation[];
  prototype_notice: string;
};

export type InviteUserPayload = {
  email: string;
  role_id: string;
  full_name?: string | null;
};

export type UserStatusPayload = {
  status: WorkspaceUserStatus;
};

export type PermissionPayload = {
  key: string;
  label: string;
  description: string;
};

export type RolePayload = {
  key: string;
  name: string;
  description: string;
  is_assignable?: boolean;
};

export type RoleUpdatePayload = Partial<RolePayload>;

export type RoleClonePayload = {
  key: string;
  name: string;
  description?: string | null;
};

export type RolePermissionsPayload = {
  permission_ids: string[];
};

export type UserRolePayload = {
  role_id: string;
};

export type CurrentUser = {
  id: string;
  email: string;
  name: string;
  full_name: string | null;
  status: WorkspaceUserStatus;
  roles: Role[];
  permissions: string[];
};

export type AuthTokenResponse = {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
  refresh_token_placeholder: string;
  user: CurrentUser;
};
