import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AuthContext, PermissionContext } from "@/features/auth/authState";
import { PermissionGuard, ProtectedRoute } from "@/features/auth/guards";
import type { CurrentUser } from "@/shared/types/settings";

const role = {
  id: "role-1",
  key: "producer",
  name: "Producer",
  description: "Producer role.",
  is_system: true,
  is_assignable: true,
  created_at: "2026-06-06T00:00:00Z",
  updated_at: "2026-06-06T00:00:00Z"
};

const user: CurrentUser = {
  id: "user-1",
  email: "producer@example.com",
  name: "Producer",
  full_name: "Producer",
  status: "active",
  roles: [role],
  permissions: ["brief.approve", "settings.manage"]
};

function renderWithPermissions(children: ReactNode, permissions: string[]) {
  return renderWithAuth(children, permissions, user);
}

function renderWithAuth(
  children: ReactNode,
  permissions: string[],
  currentUser: CurrentUser | null
) {
  const permissionSet = new Set(permissions);
  return render(
    <MemoryRouter initialEntries={["/settings"]}>
      <AuthContext.Provider
        value={{
          user: currentUser,
          status: currentUser ? "authenticated" : "unauthenticated",
          login: async () => undefined,
          logout: async () => undefined,
          refresh: async () => undefined
        }}
      >
        <PermissionContext.Provider
          value={{
            permissions: permissionSet,
            roleKeys: new Set(currentUser?.roles.map((item) => item.key) ?? []),
            hasPermission: (permission) => permissionSet.has(permission),
            hasRole: (roleKey) => roleKey === "producer"
          }}
        >
          {children}
        </PermissionContext.Provider>
      </AuthContext.Provider>
    </MemoryRouter>
  );
}

describe("authorization guards", () => {
  it("renders children when permission is present", () => {
    renderWithPermissions(
      <PermissionGuard permission="brief.approve">
        <button type="button">Approve brief</button>
      </PermissionGuard>,
      ["brief.approve"]
    );

    expect(screen.getByRole("button", { name: "Approve brief" })).toBeInTheDocument();
  });

  it("hides children when permission is missing", () => {
    renderWithPermissions(
      <PermissionGuard permission="brief.approve">
        <button type="button">Approve brief</button>
      </PermissionGuard>,
      ["brief.generate"]
    );

    expect(screen.queryByRole("button", { name: "Approve brief" })).not.toBeInTheDocument();
  });

  it("shows a permission message for restricted routes", () => {
    renderWithPermissions(
      <ProtectedRoute requiredPermission="settings.manage">
        <div>Settings page</div>
      </ProtectedRoute>,
      ["series.view"]
    );

    expect(screen.getByText("Permission required")).toBeInTheDocument();
    expect(screen.getByText(/settings.manage/)).toBeInTheDocument();
    expect(screen.queryByText("Settings page")).not.toBeInTheDocument();
  });

  it("redirects unauthenticated users to login", () => {
    renderWithAuth(
      <Routes>
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <div>Settings page</div>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<div>Login route</div>} />
      </Routes>,
      [],
      null
    );

    expect(screen.getByText("Login route")).toBeInTheDocument();
    expect(screen.queryByText("Settings page")).not.toBeInTheDocument();
  });
});
