import { zodResolver } from "@hookform/resolvers/zod";
import {
  Copy,
  KeyRound,
  MailPlus,
  Pencil,
  Plus,
  RotateCcw,
  Save,
  Search,
  Settings,
  ShieldCheck,
  Trash2,
  UserCheck,
  UserMinus,
  Users,
  X
} from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { Modal } from "@/design-system/components/Modal";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Pagination } from "@/design-system/components/Pagination";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { PermissionGuard } from "@/features/auth/guards";
import { BufferIntegrationSection } from "@/features/integrations/BufferIntegrationSection";
import { ResearchSourcesSection } from "@/features/integrations/ResearchSourcesSection";
import { InviteUserModal } from "@/features/settings/InviteUserModal";
import {
  useAssignUserRole,
  useCloneRole,
  useCreatePermission,
  useCreateRole,
  useDeletePermission,
  useDeleteRole,
  usePermissionList,
  useRoleMatrix,
  useRemoveUserRole,
  useUserManagement,
  useUpdatePermission,
  useUpdateRole,
  useUpdateRolePermissions,
  useUpdateUserStatus
} from "@/features/settings/hooks";
import type {
  Permission,
  PermissionMatrixRow,
  Role,
  RoleClonePayload,
  RolePayload,
  WorkspaceUser,
  WorkspaceUserStatus
} from "@/shared/types/settings";
import { usePaginationParams } from "@/shared/hooks/usePaginationParams";
import { useSearchParams } from "react-router-dom";

const settingsTabs = [
  { id: "roles", label: "Role management" },
  { id: "users", label: "User management" },
  { id: "integrations", label: "Integrations" }
] as const;

type SettingsTabId = (typeof settingsTabs)[number]["id"];
type RoleModalMode = "create" | "edit" | "clone";
type PermissionModalMode = "create" | "edit";

function normalizeSettingsTab(value: string | null): SettingsTabId {
  return settingsTabs.some((tab) => tab.id === value) ? (value as SettingsTabId) : "roles";
}

const roleSchema = z.object({
  key: z
    .string()
    .trim()
    .regex(/^[a-z][a-z0-9_]*$/, "Use lowercase letters, numbers, or underscores")
    .max(80),
  name: z.string().trim().min(1, "Role name is required").max(120),
  description: z.string().trim().min(1, "Description is required").max(2000),
  is_assignable: z.boolean()
});

const permissionSchema = z.object({
  key: z
    .string()
    .trim()
    .regex(/^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$/, "Use module.action format")
    .max(160),
  label: z.string().trim().min(1, "Label is required").max(160),
  description: z.string().trim().min(1, "Description is required").max(2000)
});

type RoleFormValues = z.infer<typeof roleSchema>;
type PermissionFormValues = z.infer<typeof permissionSchema>;

export function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = normalizeSettingsTab(searchParams.get("tab"));
  const [isInviteOpen, setInviteOpen] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const roleMatrixQuery = useRoleMatrix();
  const roleMatrix = roleMatrixQuery.data;

  const tabLabels = settingsTabs.map((tab) => tab.label);
  const backendTabLabels = tabLabels;
  const hasExactTabs =
    backendTabLabels.length === tabLabels.length &&
    backendTabLabels.every((label, index) => label === tabLabels[index]);

  return (
    <section className="space-y-6">
      <PageHeader
        actions={
          <div className="grid h-12 w-12 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric">
            <Settings aria-hidden className="h-5 w-5" />
          </div>
        }
        description="Configure roles, permissions, and users with backend-enforced authorization."
        kicker="Settings"
        title="Admin console"
      />

      {roleMatrixQuery.isLoading ? <LoadingState label="Loading settings" /> : null}

      {roleMatrixQuery.isError ? (
        <ErrorState
          actionLabel="Retry"
          description="Roles and users could not be loaded."
          onAction={() => void roleMatrixQuery.refetch()}
          title="Settings unavailable"
        />
      ) : null}

      {!roleMatrixQuery.isLoading && !roleMatrixQuery.isError && roleMatrix ? (
        <>
          <PrototypeNotice notice={roleMatrix.prototype_notice} />

          {!hasExactTabs ? (
            <div className="rounded-streamly-lg border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700">
              Settings tab contract mismatch. Expected exactly Role management,
              User management, and Integrations.
            </div>
          ) : null}

          {feedback ? (
            <div className="rounded-streamly-lg border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm font-bold text-emerald-700">
              {feedback}
            </div>
          ) : null}

          <div className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-2 shadow-streamly-card">
            <div className="grid gap-2 md:grid-cols-3">
              {settingsTabs.map((tab) => (
                <button
                  aria-pressed={activeTab === tab.id}
                  className={[
                    "rounded-streamly-lg px-4 py-3 text-sm font-extrabold transition",
                    activeTab === tab.id
                      ? "bg-streamly-electric text-white shadow-streamly-button"
                      : "bg-streamly-wash text-streamly-purpleBlue hover:bg-streamly-lavender"
                  ].join(" ")}
                  key={tab.id}
                  onClick={() => setSearchParams(tab.id === "roles" ? {} : { tab: tab.id })}
                  type="button"
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {activeTab === "roles" ? (
            <RoleManagementTab
              onFeedback={setFeedback}
              prototypeNotice={roleMatrix.prototype_notice}
              rows={roleMatrix.rows}
              roles={roleMatrix.roles}
            />
          ) : null}

          {activeTab === "users" ? (
            <UserManagementTab
              onInvite={() => setInviteOpen(true)}
              onStatusChanged={setFeedback}
              roles={roleMatrix.roles}
            />
          ) : null}

          {activeTab === "integrations" ? (
            <div className="space-y-5">
              <BufferIntegrationSection />
              <ResearchSourcesSection />
            </div>
          ) : null}

          <PermissionGuard permission="user.manage">
            <InviteUserModal
              isOpen={isInviteOpen}
              onClose={() => setInviteOpen(false)}
              onInvited={(invitation) => {
                setFeedback(`Invitation created for ${invitation.email}.`);
              }}
              roles={roleMatrix.roles}
            />
          </PermissionGuard>
        </>
      ) : null}
    </section>
  );
}

function PrototypeNotice({ notice }: { notice: string }) {
  return (
    <section className="rounded-streamly-xl border border-amber-100 bg-amber-50 p-4 text-amber-900">
      <div className="flex items-start gap-3">
        <ShieldCheck aria-hidden className="mt-0.5 h-5 w-5 shrink-0" />
        <div>
          <h2 className="font-streamly-platform text-base font-extrabold">
            RBAC foundation
          </h2>
          <p className="mt-1 text-sm font-bold leading-6">{notice}</p>
        </div>
      </div>
    </section>
  );
}

function RoleManagementTab({
  onFeedback,
  prototypeNotice,
  roles,
  rows
}: {
  onFeedback: (message: string) => void;
  prototypeNotice: string;
  roles: Role[];
  rows: PermissionMatrixRow[];
}) {
  const [selectedRoleId, setSelectedRoleId] = useState(roles[0]?.id ?? "");
  const [draftPermissionIds, setDraftPermissionIds] = useState<Set<string>>(new Set());
  const [roleModal, setRoleModal] = useState<{ mode: RoleModalMode; role?: Role } | null>(null);
  const [permissionModal, setPermissionModal] = useState<{
    mode: PermissionModalMode;
    permission?: Permission;
  } | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const createRoleMutation = useCreateRole();
  const updateRoleMutation = useUpdateRole();
  const deleteRoleMutation = useDeleteRole();
  const cloneRoleMutation = useCloneRole();
  const updateRolePermissionsMutation = useUpdateRolePermissions();
  const createPermissionMutation = useCreatePermission();
  const updatePermissionMutation = useUpdatePermission();
  const deletePermissionMutation = useDeletePermission();

  const selectedRole = roles.find((role) => role.id === selectedRoleId) ?? roles[0];
  const rowsByModule = useMemo(() => groupRowsByModule(rows), [rows]);
  const permissionPagination = usePaginationParams({
    defaultPageSize: 20,
    defaultSort: "module",
    storageKey: "podobot.settings.permissions.page_size"
  });
  const permissionsQuery = usePermissionList({
    page: permissionPagination.page,
    pageSize: permissionPagination.pageSize,
    search: permissionPagination.search,
    sort: permissionPagination.sort
  });
  const pagedPermissionRows = useMemo(() => {
    const matrixRowsByPermissionId = new Map(rows.map((row) => [row.permission.id, row]));
    return (permissionsQuery.data?.items ?? [])
      .map((permission) => matrixRowsByPermissionId.get(permission.id))
      .filter((row): row is PermissionMatrixRow => Boolean(row));
  }, [permissionsQuery.data?.items, rows]);
  const pagedRowsByModule = useMemo(
    () => groupRowsByModule(pagedPermissionRows),
    [pagedPermissionRows]
  );
  const selectedPermissionIds = useMemo(() => {
    if (!selectedRole) {
      return new Set<string>();
    }
    return new Set(
      rows
        .filter((row) =>
          row.role_permissions.some(
            (cell) => cell.role_id === selectedRole.id && cell.is_allowed
          )
        )
        .map((row) => row.permission.id)
    );
  }, [rows, selectedRole]);

  useEffect(() => {
    if (!selectedRoleId && roles[0]) {
      setSelectedRoleId(roles[0].id);
    }
    if (selectedRoleId && !roles.some((role) => role.id === selectedRoleId) && roles[0]) {
      setSelectedRoleId(roles[0].id);
    }
  }, [roles, selectedRoleId]);

  useEffect(() => {
    setDraftPermissionIds(new Set(selectedPermissionIds));
  }, [selectedPermissionIds]);

  const permissionsDirty = !setsEqual(draftPermissionIds, selectedPermissionIds);

  async function saveRolePermissions() {
    if (!selectedRole) {
      return;
    }
    await updateRolePermissionsMutation.mutateAsync({
      roleId: selectedRole.id,
      payload: { permission_ids: [...draftPermissionIds] }
    });
    onFeedback(`Permissions saved for ${selectedRole.name}.`);
  }

  async function deleteSelectedRole() {
    if (!selectedRole) {
      return;
    }
    setLocalError(null);
    try {
      await deleteRoleMutation.mutateAsync(selectedRole.id);
      onFeedback(`${selectedRole.name} deleted.`);
    } catch (error) {
      setLocalError(errorMessage(error));
    }
  }

  async function deleteSelectedPermission(permission: Permission) {
    setLocalError(null);
    try {
      await deletePermissionMutation.mutateAsync(permission.id);
      onFeedback(`${permission.key} deleted.`);
    } catch (error) {
      setLocalError(errorMessage(error));
    }
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[18rem_minmax(0,1fr)_22rem]">
      <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-streamly-platform text-xl font-extrabold text-streamly-coal">
              Roles
            </h2>
            <p className="mt-1 text-sm font-bold leading-6 text-streamly-purpleBlue">
              {prototypeNotice}
            </p>
          </div>
          <PermissionGuard permission="role.manage">
            <button
              aria-label="Create role"
              className="streamly-button-primary px-3 py-2"
              onClick={() => setRoleModal({ mode: "create" })}
              type="button"
            >
              <Plus aria-hidden className="h-4 w-4" />
            </button>
          </PermissionGuard>
        </div>

        <div className="mt-5 space-y-2">
          {roles.map((role) => (
            <button
              className={[
                "w-full rounded-streamly-lg border px-3 py-3 text-left transition",
                selectedRole?.id === role.id
                  ? "border-streamly-electric bg-streamly-lavender text-streamly-coal"
                  : "border-streamly-lavenderStrong bg-streamly-wash text-streamly-purpleBlue hover:border-streamly-electric/60"
              ].join(" ")}
              key={role.id}
              onClick={() => setSelectedRoleId(role.id)}
              type="button"
            >
              <span className="flex items-center justify-between gap-2">
                <span className="text-sm font-extrabold">{role.name}</span>
                {role.is_system ? <StatusBadge label="system" tone="neutral" /> : null}
              </span>
              <span className="mt-1 block text-xs font-semibold">{role.key}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        {selectedRole ? (
          <>
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-streamly-lavenderStrong pb-4">
              <div>
                <p className="streamly-kicker">Permission matrix</p>
                <h2 className="font-streamly-platform text-xl font-extrabold text-streamly-coal">
                  {selectedRole.name}
                </h2>
                <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
                  Assign or remove permissions by module, then save the role.
                </p>
              </div>
              <PermissionGuard permission="role.manage">
                <div className="flex flex-wrap gap-2">
                  <button
                    className="streamly-button-secondary px-3 py-2 text-xs"
                    onClick={() => setRoleModal({ mode: "edit", role: selectedRole })}
                    type="button"
                  >
                    <Pencil aria-hidden className="h-3.5 w-3.5" />
                    Edit
                  </button>
                  <button
                    className="streamly-button-secondary px-3 py-2 text-xs"
                    onClick={() => setRoleModal({ mode: "clone", role: selectedRole })}
                    type="button"
                  >
                    <Copy aria-hidden className="h-3.5 w-3.5" />
                    Clone
                  </button>
                  <button
                    className="streamly-button-secondary px-3 py-2 text-xs disabled:opacity-50"
                    disabled={selectedRole.is_system || deleteRoleMutation.isPending}
                    onClick={() => void deleteSelectedRole()}
                    title={
                      selectedRole.is_system
                        ? "Protected system roles cannot be deleted"
                        : "Delete role"
                    }
                    type="button"
                  >
                    <Trash2 aria-hidden className="h-3.5 w-3.5" />
                    Delete
                  </button>
                </div>
              </PermissionGuard>
            </div>

            {localError ? <MutationError error={localError} /> : null}

            <div className="mt-5 space-y-4">
              {Object.entries(rowsByModule).map(([module, moduleRows]) => (
                <section
                  className="rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash/70"
                  key={module}
                >
                  <div className="border-b border-streamly-lavenderStrong px-4 py-3 text-xs font-extrabold uppercase text-streamly-purpleBlue">
                    {formatModule(module)}
                  </div>
                  <div className="divide-y divide-streamly-lavenderStrong bg-white">
                    {moduleRows.map((row) => {
                      const checked = draftPermissionIds.has(row.permission.id);
                      return (
                        <label
                          className="grid cursor-pointer gap-3 px-4 py-3 md:grid-cols-[1fr_auto] md:items-center"
                          key={row.permission.id}
                        >
                          <span>
                            <span className="block text-sm font-extrabold text-streamly-coal">
                              {row.permission.label}
                            </span>
                            <span className="mt-1 block text-xs font-semibold text-[var(--streamly-text-muted)]">
                              {row.permission.key} · {row.permission.description}
                            </span>
                          </span>
                          <input
                            checked={checked}
                            className="h-5 w-5 accent-streamly-electric"
                            onChange={(event) => {
                              const next = new Set(draftPermissionIds);
                              if (event.target.checked) {
                                next.add(row.permission.id);
                              } else {
                                next.delete(row.permission.id);
                              }
                              setDraftPermissionIds(next);
                            }}
                            type="checkbox"
                          />
                        </label>
                      );
                    })}
                  </div>
                </section>
              ))}
            </div>

            <PermissionGuard permission="role.manage">
              <div className="mt-5 flex flex-wrap justify-end gap-3 border-t border-streamly-lavenderStrong pt-5">
                <button
                  className="streamly-button-secondary disabled:opacity-50"
                  disabled={!permissionsDirty || updateRolePermissionsMutation.isPending}
                  onClick={() => setDraftPermissionIds(new Set(selectedPermissionIds))}
                  type="button"
                >
                  <RotateCcw aria-hidden className="h-4 w-4" />
                  Cancel
                </button>
                <button
                  className="streamly-button-primary disabled:opacity-50"
                  disabled={!permissionsDirty || updateRolePermissionsMutation.isPending}
                  onClick={() => void saveRolePermissions()}
                  type="button"
                >
                  <Save aria-hidden className="h-4 w-4" />
                  {updateRolePermissionsMutation.isPending ? "Saving..." : "Save permissions"}
                </button>
              </div>
            </PermissionGuard>
          </>
        ) : (
          <EmptyState description="Create a role to start assigning permissions." title="No roles" />
        )}
      </section>

      <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-streamly-platform text-lg font-extrabold text-streamly-coal">
              Permissions
            </h2>
            <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
              System permissions are registered. Custom permissions can be added for future modules.
            </p>
          </div>
          <PermissionGuard permission="role.manage">
            <button
              className="streamly-button-primary px-3 py-2 text-xs"
              onClick={() => setPermissionModal({ mode: "create" })}
              type="button"
            >
              <KeyRound aria-hidden className="h-3.5 w-3.5" />
              Add
            </button>
          </PermissionGuard>
        </div>

        <label className="mt-4 flex items-center gap-2 rounded-streamly-pill bg-streamly-wash px-3 py-2">
          <Search aria-hidden className="h-4 w-4 text-streamly-purpleBlue" />
          <span className="sr-only">Search permissions</span>
          <input
            className="w-full bg-transparent text-sm font-bold text-streamly-coal outline-none placeholder:text-streamly-purpleBlue/70"
            onChange={(event) => permissionPagination.setSearch(event.target.value)}
            placeholder="Search permissions"
            value={permissionPagination.search}
          />
        </label>

        <div className="mt-5 max-h-[46rem] space-y-4 overflow-auto pr-1">
          {permissionsQuery.isLoading ? <LoadingState label="Loading permissions" /> : null}
          {permissionsQuery.isError ? (
            <ErrorState
              actionLabel="Retry"
              description="Permissions could not be loaded."
              onAction={() => void permissionsQuery.refetch()}
              title="Permissions unavailable"
            />
          ) : null}
          {!permissionsQuery.isLoading && !permissionsQuery.isError && pagedPermissionRows.length === 0 ? (
            <EmptyState
              description="No permissions match the current search."
              title="No permissions"
            />
          ) : null}
          {Object.entries(pagedRowsByModule).map(([module, moduleRows]) => (
            <section key={module}>
              <h3 className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
                {formatModule(module)}
              </h3>
              <div className="mt-2 space-y-2">
                {moduleRows.map((row) => (
                  <div
                    className="rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash px-3 py-3"
                    key={row.permission.id}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span>
                        <span className="block text-sm font-extrabold text-streamly-coal">
                          {row.permission.key}
                        </span>
                        <span className="mt-1 block text-xs font-semibold text-[var(--streamly-text-muted)]">
                          {row.permission.label}
                        </span>
                      </span>
                      {row.permission.is_system ? (
                        <StatusBadge label="system" tone="neutral" />
                      ) : null}
                    </div>
                    <PermissionGuard permission="role.manage">
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          className="streamly-button-secondary px-3 py-2 text-xs"
                          onClick={() =>
                            setPermissionModal({
                              mode: "edit",
                              permission: row.permission
                            })
                          }
                          type="button"
                        >
                          <Pencil aria-hidden className="h-3.5 w-3.5" />
                          Edit
                        </button>
                        <button
                          className="streamly-button-secondary px-3 py-2 text-xs disabled:opacity-50"
                          disabled={row.permission.is_system || deletePermissionMutation.isPending}
                          onClick={() => void deleteSelectedPermission(row.permission)}
                          title={
                            row.permission.is_system
                              ? "System permissions cannot be deleted"
                              : "Delete permission"
                          }
                          type="button"
                        >
                          <Trash2 aria-hidden className="h-3.5 w-3.5" />
                          Delete
                        </button>
                      </div>
                    </PermissionGuard>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
        {permissionsQuery.data ? (
          <div className="mt-4">
            <Pagination
              hasNext={permissionsQuery.data.has_next}
              hasPrevious={permissionsQuery.data.has_previous}
              label="permissions"
              onPageChange={permissionPagination.setPage}
              onPageSizeChange={permissionPagination.setPageSize}
              page={permissionsQuery.data.page}
              pageSize={permissionsQuery.data.page_size}
              total={permissionsQuery.data.total}
              totalPages={permissionsQuery.data.total_pages}
            />
          </div>
        ) : null}
      </section>

      <RoleModal
        isOpen={roleModal !== null}
        mode={roleModal?.mode ?? "create"}
        onClose={() => setRoleModal(null)}
        onSubmit={async (values) => {
          if (roleModal?.mode === "edit" && roleModal.role) {
            await updateRoleMutation.mutateAsync({ roleId: roleModal.role.id, payload: values });
            onFeedback(`${values.name} updated.`);
          } else if (roleModal?.mode === "clone" && roleModal.role) {
            await cloneRoleMutation.mutateAsync({
              roleId: roleModal.role.id,
              payload: values as RoleClonePayload
            });
            onFeedback(`${values.name} cloned.`);
          } else {
            await createRoleMutation.mutateAsync(values as RolePayload);
            onFeedback(`${values.name} created.`);
          }
          setRoleModal(null);
        }}
        role={roleModal?.role}
        saving={
          createRoleMutation.isPending ||
          updateRoleMutation.isPending ||
          cloneRoleMutation.isPending
        }
      />

      <PermissionModal
        isOpen={permissionModal !== null}
        mode={permissionModal?.mode ?? "create"}
        onClose={() => setPermissionModal(null)}
        onSubmit={async (values) => {
          if (permissionModal?.mode === "edit" && permissionModal.permission) {
            await updatePermissionMutation.mutateAsync({
              permissionId: permissionModal.permission.id,
              payload: values
            });
            onFeedback(`${values.key} updated.`);
          } else {
            await createPermissionMutation.mutateAsync(values);
            onFeedback(`${values.key} created.`);
          }
          setPermissionModal(null);
        }}
        permission={permissionModal?.permission}
        saving={createPermissionMutation.isPending || updatePermissionMutation.isPending}
      />
    </div>
  );
}

function UserManagementTab({
  onInvite,
  onStatusChanged,
  roles
}: {
  onInvite: () => void;
  onStatusChanged: (message: string) => void;
  roles: Role[];
}) {
  const [statusFilter, setStatusFilter] = useState<"all" | WorkspaceUserStatus>("all");
  const pagination = usePaginationParams({
    defaultPageSize: 20,
    defaultSort: "email",
    storageKey: "podobot.settings.users.page_size"
  });
  const usersQuery = useUserManagement({
    page: pagination.page,
    pageSize: pagination.pageSize,
    search: pagination.search,
    sort: pagination.sort,
    status: statusFilter === "all" ? undefined : statusFilter
  });
  const users = usersQuery.data?.users ?? [];
  const invitations = usersQuery.data?.invitations ?? [];

  return (
    <div className="space-y-5">
      <div className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="font-streamly-platform text-xl font-extrabold text-streamly-coal">
              Users
            </h2>
            <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
              Assign reusable roles, inspect effective permissions, and manage access state.
            </p>
          </div>
          <PermissionGuard permission="user.manage">
            <button className="streamly-button-primary" onClick={onInvite} type="button">
              <MailPlus aria-hidden className="h-4 w-4" />
              Invite user
            </button>
          </PermissionGuard>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_12rem]">
          <label className="flex items-center gap-2 rounded-streamly-pill bg-streamly-wash px-3 py-2">
            <Search aria-hidden className="h-4 w-4 text-streamly-purpleBlue" />
            <span className="sr-only">Search users</span>
            <input
              className="w-full bg-transparent text-sm font-bold text-streamly-coal outline-none placeholder:text-streamly-purpleBlue/70"
              onChange={(event) => pagination.setSearch(event.target.value)}
              placeholder="Search users by email or name"
              value={pagination.search}
            />
          </label>
          <label>
            <span className="sr-only">Filter user status</span>
            <select
              className="w-full rounded-streamly-pill border border-streamly-lavenderStrong bg-white px-3 py-2 text-sm font-extrabold text-streamly-coal shadow-streamly-card outline-none focus:border-streamly-electric"
              onChange={(event) => {
                setStatusFilter(event.target.value as "all" | WorkspaceUserStatus);
                pagination.setPage(1);
              }}
              value={statusFilter}
            >
              <option value="all">All statuses</option>
              <option value="active">Active</option>
              <option value="invited">Invited</option>
              <option value="suspended">Suspended</option>
            </select>
          </label>
        </div>
      </div>

      {usersQuery.isLoading ? <LoadingState label="Loading users" /> : null}

      {usersQuery.isError ? (
        <ErrorState
          actionLabel="Retry"
          description="Users could not be loaded."
          onAction={() => void usersQuery.refetch()}
          title="Users unavailable"
        />
      ) : null}

      {!usersQuery.isLoading && !usersQuery.isError && users.length === 0 ? (
        <EmptyState
          description="Invite a teammate to populate the workspace user list."
          title="No users yet"
        />
      ) : null}

      {!usersQuery.isLoading && !usersQuery.isError && users.length > 0 ? (
        <div className="overflow-hidden rounded-streamly-xl border border-streamly-lavenderStrong bg-white shadow-streamly-card">
          <div className="hidden grid-cols-[minmax(0,1fr)_minmax(16rem,1fr)_8rem_18rem] border-b border-streamly-lavenderStrong px-4 py-3 text-xs font-extrabold uppercase text-streamly-purpleBlue xl:grid">
            <span>User</span>
            <span>Roles and permissions</span>
            <span>Status</span>
            <span>Actions</span>
          </div>
          {users.map((user) => (
            <UserRow
              key={user.id}
              onStatusChanged={onStatusChanged}
              roles={roles}
              user={user}
            />
          ))}
        </div>
      ) : null}

      {usersQuery.data ? (
        <Pagination
          hasNext={usersQuery.data.has_next}
          hasPrevious={usersQuery.data.has_previous}
          label="users"
          onPageChange={pagination.setPage}
          onPageSizeChange={pagination.setPageSize}
          page={usersQuery.data.page}
          pageSize={usersQuery.data.page_size}
          total={usersQuery.data.total}
          totalPages={usersQuery.data.total_pages}
        />
      ) : null}

      <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash/70 p-5">
        <div className="flex items-center gap-2">
          <Users aria-hidden className="h-4 w-4 text-streamly-electric" />
          <h3 className="font-streamly-platform text-lg font-extrabold text-streamly-coal">
            Recent invitations
          </h3>
        </div>
        <div className="mt-4 space-y-3">
          {invitations.length === 0 ? (
            <p className="text-sm font-bold text-[var(--streamly-text-muted)]">
              No invitations have been created yet.
            </p>
          ) : (
            invitations.map((invitation) => (
              <div
                className="flex flex-wrap items-center justify-between gap-3 rounded-streamly-lg border border-streamly-lavenderStrong bg-white px-3 py-3"
                key={invitation.id}
              >
                <span>
                  <span className="block text-sm font-extrabold text-streamly-coal">
                    {invitation.email}
                  </span>
                  <span className="mt-1 block text-xs font-bold text-streamly-purpleBlue">
                    {invitation.role.name} · {new Date(invitation.created_at).toLocaleString()}
                  </span>
                </span>
                <StatusBadge label={invitation.status} tone={invitation.status} />
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

function UserRow({
  onStatusChanged,
  roles,
  user
}: {
  onStatusChanged: (message: string) => void;
  roles: Role[];
  user: WorkspaceUser;
}) {
  const [selectedRoleId, setSelectedRoleId] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const updateStatus = useUpdateUserStatus();
  const assignRole = useAssignUserRole();
  const removeRole = useRemoveUserRole();
  const assignedRoleIds = new Set(user.roles.map((role) => role.id));
  const assignableRoles = roles.filter(
    (role) => role.is_assignable && !assignedRoleIds.has(role.id)
  );
  const effectivePermissions = user.effective_permissions.slice(0, 8);

  useEffect(() => {
    setSelectedRoleId(assignableRoles[0]?.id ?? "");
  }, [assignableRoles]);

  async function setStatus(userStatus: WorkspaceUserStatus) {
    setLocalError(null);
    try {
      await updateStatus.mutateAsync({ userId: user.id, payload: { status: userStatus } });
      onStatusChanged(`${user.email} is now ${userStatus}.`);
    } catch (error) {
      setLocalError(errorMessage(error));
    }
  }

  async function addRole() {
    if (!selectedRoleId) {
      return;
    }
    setLocalError(null);
    try {
      await assignRole.mutateAsync({ userId: user.id, payload: { role_id: selectedRoleId } });
      onStatusChanged(`Role assigned to ${user.email}.`);
    } catch (error) {
      setLocalError(errorMessage(error));
    }
  }

  async function removeAssignedRole(role: Role) {
    setLocalError(null);
    try {
      await removeRole.mutateAsync({ userId: user.id, roleId: role.id });
      onStatusChanged(`${role.name} removed from ${user.email}.`);
    } catch (error) {
      setLocalError(errorMessage(error));
    }
  }

  return (
    <div className="grid gap-4 border-b border-streamly-lavenderStrong px-4 py-4 last:border-b-0 xl:grid-cols-[minmax(0,1fr)_minmax(16rem,1fr)_8rem_18rem] xl:items-start">
      <span>
        <span className="block font-streamly-platform text-sm font-extrabold text-streamly-coal">
          {user.full_name || user.email}
        </span>
        <span className="mt-1 block text-xs font-bold text-[var(--streamly-text-muted)]">
          {user.email}
        </span>
      </span>

      <span>
        <span className="flex flex-wrap gap-2">
          {user.roles.map((role) => (
            <span
              className="inline-flex items-center gap-1 rounded-streamly-pill bg-streamly-lavender px-3 py-1 text-xs font-extrabold text-streamly-electric"
              key={role.id}
            >
              {role.name}
              <PermissionGuard permission="user.manage">
                <button
                  aria-label={`Remove ${role.name}`}
                  className="text-streamly-purpleBlue disabled:opacity-40"
                  disabled={user.roles.length <= 1 || removeRole.isPending}
                  onClick={() => void removeAssignedRole(role)}
                  type="button"
                >
                  <X aria-hidden className="h-3 w-3" />
                </button>
              </PermissionGuard>
            </span>
          ))}
        </span>
        <span className="mt-3 flex flex-wrap gap-1">
          {effectivePermissions.map((permission) => (
            <span
              className="rounded-streamly-pill bg-streamly-wash px-2 py-1 text-[11px] font-bold text-streamly-purpleBlue"
              key={permission}
            >
              {permission}
            </span>
          ))}
          {user.effective_permissions.length > effectivePermissions.length ? (
            <span className="rounded-streamly-pill bg-streamly-wash px-2 py-1 text-[11px] font-bold text-streamly-purpleBlue">
              +{user.effective_permissions.length - effectivePermissions.length}
            </span>
          ) : null}
        </span>
        {localError ? <MutationError error={localError} /> : null}
      </span>

      <StatusBadge label={user.status} tone={user.status} />

      <PermissionGuard permission="user.manage">
        <span className="grid gap-2">
          <span className="flex flex-wrap gap-2">
            <button
              className="streamly-button-secondary px-3 py-2 text-xs disabled:opacity-50"
              disabled={updateStatus.isPending || user.status === "active"}
              onClick={() => void setStatus("active")}
              type="button"
            >
              <UserCheck aria-hidden className="h-3.5 w-3.5" />
              Reactivate
            </button>
            <button
              className="streamly-button-secondary px-3 py-2 text-xs disabled:opacity-50"
              disabled={updateStatus.isPending || user.status === "suspended"}
              onClick={() => void setStatus("suspended")}
              type="button"
            >
              <UserMinus aria-hidden className="h-3.5 w-3.5" />
              Deactivate
            </button>
          </span>
          <span className="flex gap-2">
            <select
              className="streamly-search min-w-0 flex-1"
              disabled={assignableRoles.length === 0 || assignRole.isPending}
              onChange={(event) => setSelectedRoleId(event.target.value)}
              value={selectedRoleId}
            >
              {assignableRoles.length === 0 ? (
                <option value="">No roles left</option>
              ) : (
                assignableRoles.map((role) => (
                  <option key={role.id} value={role.id}>
                    {role.name}
                  </option>
                ))
              )}
            </select>
            <button
              aria-label="Assign role"
              className="streamly-button-primary px-3 py-2 disabled:opacity-50"
              disabled={!selectedRoleId || assignRole.isPending}
              onClick={() => void addRole()}
              type="button"
            >
              <Plus aria-hidden className="h-4 w-4" />
            </button>
          </span>
        </span>
      </PermissionGuard>
    </div>
  );
}

function RoleModal({
  isOpen,
  mode,
  onClose,
  onSubmit,
  role,
  saving
}: {
  isOpen: boolean;
  mode: RoleModalMode;
  onClose: () => void;
  onSubmit: (values: RoleFormValues) => Promise<void>;
  role?: Role;
  saving: boolean;
}) {
  const {
    formState: { errors, isValid },
    handleSubmit,
    register,
    reset
  } = useForm<RoleFormValues>({
    resolver: zodResolver(roleSchema),
    mode: "onChange",
    defaultValues: roleFormValues(mode, role)
  });

  useEffect(() => {
    reset(roleFormValues(mode, role));
  }, [mode, reset, role]);

  return (
    <Modal
      description="Role changes are auditable and enforced by backend permission dependencies."
      isOpen={isOpen}
      onClose={onClose}
      title={mode === "create" ? "Create Role" : mode === "clone" ? "Clone Role" : "Edit Role"}
    >
      <form className="space-y-4" onSubmit={(event) => void handleSubmit(onSubmit)(event)}>
        <Field label="Role key" message={errors.key?.message}>
          <input
            className="streamly-search w-full max-w-none"
            disabled={mode === "edit" && role?.is_system}
            {...register("key")}
          />
        </Field>
        <Field label="Role name" message={errors.name?.message}>
          <input className="streamly-search w-full max-w-none" {...register("name")} />
        </Field>
        <Field label="Description" message={errors.description?.message}>
          <textarea
            className="min-h-28 w-full rounded-streamly-xl border border-streamly-lavenderStrong bg-white px-4 py-3 font-streamly-body text-sm leading-6 outline-none transition focus:border-streamly-electric focus:ring-4 focus:ring-streamly-electric/15"
            {...register("description")}
          />
        </Field>
        <label className="flex items-center gap-2 text-sm font-bold text-streamly-purpleBlue">
          <input className="h-4 w-4 accent-streamly-electric" type="checkbox" {...register("is_assignable")} />
          Assignable to users
        </label>
        <div className="flex flex-wrap justify-end gap-3 border-t border-streamly-lavenderStrong pt-5">
          <button className="streamly-button-secondary" disabled={saving} onClick={onClose} type="button">
            Cancel
          </button>
          <button className="streamly-button-primary disabled:opacity-50" disabled={!isValid || saving} type="submit">
            <Save aria-hidden className="h-4 w-4" />
            {saving ? "Saving..." : "Save role"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function PermissionModal({
  isOpen,
  mode,
  onClose,
  onSubmit,
  permission,
  saving
}: {
  isOpen: boolean;
  mode: PermissionModalMode;
  onClose: () => void;
  onSubmit: (values: PermissionFormValues) => Promise<void>;
  permission?: Permission;
  saving: boolean;
}) {
  const {
    formState: { errors, isValid },
    handleSubmit,
    register,
    reset
  } = useForm<PermissionFormValues>({
    resolver: zodResolver(permissionSchema),
    mode: "onChange",
    defaultValues: permissionFormValues(permission)
  });

  useEffect(() => {
    reset(permissionFormValues(permission));
  }, [permission, reset]);

  return (
    <Modal
      description="Permission keys use module.action format and become available to role matrices."
      isOpen={isOpen}
      onClose={onClose}
      title={mode === "create" ? "Create Permission" : "Edit Permission"}
    >
      <form className="space-y-4" onSubmit={(event) => void handleSubmit(onSubmit)(event)}>
        <Field label="Permission key" message={errors.key?.message}>
          <input className="streamly-search w-full max-w-none" {...register("key")} />
        </Field>
        <Field label="Label" message={errors.label?.message}>
          <input className="streamly-search w-full max-w-none" {...register("label")} />
        </Field>
        <Field label="Description" message={errors.description?.message}>
          <textarea
            className="min-h-28 w-full rounded-streamly-xl border border-streamly-lavenderStrong bg-white px-4 py-3 font-streamly-body text-sm leading-6 outline-none transition focus:border-streamly-electric focus:ring-4 focus:ring-streamly-electric/15"
            {...register("description")}
          />
        </Field>
        <div className="flex flex-wrap justify-end gap-3 border-t border-streamly-lavenderStrong pt-5">
          <button className="streamly-button-secondary" disabled={saving} onClick={onClose} type="button">
            Cancel
          </button>
          <button className="streamly-button-primary disabled:opacity-50" disabled={!isValid || saving} type="submit">
            <KeyRound aria-hidden className="h-4 w-4" />
            {saving ? "Saving..." : "Save permission"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function Field({
  children,
  label,
  message
}: {
  children: ReactNode;
  label: string;
  message?: string;
}) {
  return (
    <label className="grid gap-2">
      <span className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
        {label}
      </span>
      {children}
      {message ? <span className="text-xs font-bold text-red-600">{message}</span> : null}
    </label>
  );
}

function MutationError({ error }: { error: unknown }) {
  return (
    <p className="mt-4 rounded-streamly-md bg-red-50 px-3 py-2 text-sm font-bold text-red-700">
      {errorMessage(error)}
    </p>
  );
}

function roleFormValues(mode: RoleModalMode, role?: Role): RoleFormValues {
  if (!role) {
    return { key: "", name: "", description: "", is_assignable: true };
  }
  if (mode === "clone") {
    return {
      key: `${role.key}_copy`,
      name: `${role.name} Copy`,
      description: role.description,
      is_assignable: true
    };
  }
  return {
    key: role.key,
    name: role.name,
    description: role.description,
    is_assignable: role.is_assignable
  };
}

function permissionFormValues(permission?: Permission): PermissionFormValues {
  return {
    key: permission?.key ?? "",
    label: permission?.label ?? "",
    description: permission?.description ?? ""
  };
}

function groupRowsByModule(rows: PermissionMatrixRow[]) {
  return rows.reduce<Record<string, PermissionMatrixRow[]>>((groups, row) => {
    groups[row.permission.module] = groups[row.permission.module] ?? [];
    groups[row.permission.module].push(row);
    return groups;
  }, {});
}

function setsEqual(first: Set<string>, second: Set<string>) {
  if (first.size !== second.size) {
    return false;
  }
  return [...first].every((item) => second.has(item));
}

function formatModule(module: string) {
  return module.replaceAll("_", " ");
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error || "Settings action failed.");
}
