import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ComponentProps } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { LoginPage } from "@/features/auth/LoginPage";
import { AuthContext, PermissionContext } from "@/features/auth/authState";

function renderLoginPage(
  login = vi.fn(async () => undefined),
  initialEntries: ComponentProps<typeof MemoryRouter>["initialEntries"] = ["/login"]
) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <AuthContext.Provider
        value={{
          user: null,
          status: "unauthenticated",
          login,
          logout: async () => undefined,
          refresh: async () => undefined
        }}
      >
        <PermissionContext.Provider
          value={{
            permissions: new Set(),
            roleKeys: new Set(),
            hasPermission: () => false,
            hasRole: () => false
          }}
        >
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/dashboard" element={<div>Dashboard destination</div>} />
          </Routes>
        </PermissionContext.Provider>
      </AuthContext.Provider>
    </MemoryRouter>
  );
}

describe("LoginPage", () => {
  it("shows required field validation", async () => {
    renderLoginPage();

    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("A valid email address is required")).toBeInTheDocument();
    expect(screen.getByText("Password is required")).toBeInTheDocument();
  });

  it("shows invalid credentials from the backend", async () => {
    const login = vi.fn(async () => {
      throw new Error("Invalid email or password");
    });
    renderLoginPage(login, [
      {
        pathname: "/login",
        state: { from: { pathname: "/settings" } }
      }
    ]);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "admin@example.com" }
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "wrong-password" }
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("Invalid email or password")).toBeInTheDocument();
    expect(login).toHaveBeenCalledWith("admin@example.com", "wrong-password");
  });

  it("redirects to the dashboard after successful login", async () => {
    const login = vi.fn(async () => undefined);
    renderLoginPage(login);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "admin@example.com" }
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password" }
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText("Dashboard destination")).toBeInTheDocument();
    });
    expect(login).toHaveBeenCalledWith("admin@example.com", "password");
  });
});
