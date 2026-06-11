import { requestJson } from "@/shared/api/httpClient";
import type { AuthTokenResponse, CurrentUser } from "@/shared/types/settings";

export function login(payload: { email: string; password: string }) {
  return requestJson<AuthTokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function logout() {
  return requestJson<{ success: boolean }>("/api/v1/auth/logout", {
    method: "POST"
  });
}

export function getCurrentUser() {
  return requestJson<CurrentUser>("/api/v1/auth/me");
}
