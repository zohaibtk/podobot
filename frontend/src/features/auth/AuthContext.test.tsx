import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getCurrentUser, logout as logoutRequest } from "@/features/auth/api";
import { AuthProvider } from "@/features/auth/AuthContext";
import { useAuth } from "@/features/auth/hooks";
import {
  clearAccessToken,
  readAccessToken,
  writeAccessToken
} from "@/features/auth/tokenStorage";
import type { CurrentUser } from "@/shared/types/settings";

vi.mock("@/features/auth/api", () => ({
  getCurrentUser: vi.fn(),
  login: vi.fn(),
  logout: vi.fn()
}));

const currentUser: CurrentUser = {
  id: "user-1",
  email: "admin@example.com",
  name: "Admin User",
  full_name: "Admin User",
  status: "active",
  roles: [],
  permissions: ["settings.manage"]
};

function LogoutProbe() {
  const { logout, status, user } = useAuth();

  return (
    <div>
      <p>{status}</p>
      <p>{user?.email ?? "No user"}</p>
      <button onClick={() => void logout()} type="button">
        Log out
      </button>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    clearAccessToken();
    vi.clearAllMocks();
  });

  it("clears the stored session on logout", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue(currentUser);
    vi.mocked(logoutRequest).mockResolvedValue({ success: true });
    writeAccessToken("access-token");

    render(
      <AuthProvider>
        <LogoutProbe />
      </AuthProvider>
    );

    expect(await screen.findByText("admin@example.com")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /log out/i }));

    await waitFor(() => {
      expect(readAccessToken()).toBeNull();
      expect(screen.getByText("unauthenticated")).toBeInTheDocument();
      expect(screen.getByText("No user")).toBeInTheDocument();
    });
  });
});
