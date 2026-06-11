import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getCurrentUser, login as loginRequest, logout as logoutRequest } from "@/features/auth/api";
import { AuthContext, PermissionContext } from "@/features/auth/authState";
import { clearAccessToken, readAccessToken, writeAccessToken } from "@/features/auth/tokenStorage";
import type { CurrentUser } from "@/shared/types/settings";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const hydrationStartedRef = useRef(false);

  const hydrate = useCallback(async () => {
    setStatus("loading");
    try {
      if (readAccessToken()) {
        setUser(await getCurrentUser());
        setStatus("authenticated");
        return;
      }
      setUser(null);
      setStatus("unauthenticated");
    } catch {
      clearAccessToken();
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

  useEffect(() => {
    if (hydrationStartedRef.current) {
      return;
    }
    hydrationStartedRef.current = true;
    void hydrate();
  }, [hydrate]);

  useEffect(() => {
    function expireSession() {
      clearAccessToken();
      setUser(null);
      setStatus("unauthenticated");
    }

    window.addEventListener("podobot:auth-expired", expireSession);
    return () => window.removeEventListener("podobot:auth-expired", expireSession);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await loginRequest({ email, password });
    writeAccessToken(response.access_token);
    setUser(response.user);
    setStatus("authenticated");
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } finally {
      clearAccessToken();
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

  const authValue = useMemo(
    () => ({ user, status, login, logout, refresh: hydrate }),
    [hydrate, login, logout, status, user]
  );
  const permissionValue = useMemo(() => {
    const permissions = new Set(user?.permissions ?? []);
    const roleKeys = new Set(user?.roles.map((role) => role.key) ?? []);
    return {
      permissions,
      roleKeys,
      hasPermission: (permission: string) => permissions.has(permission),
      hasRole: (role: string) => roleKeys.has(role)
    };
  }, [user]);

  return (
    <AuthContext.Provider value={authValue}>
      <PermissionContext.Provider value={permissionValue}>
        {children}
      </PermissionContext.Provider>
    </AuthContext.Provider>
  );
}
