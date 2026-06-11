import { createContext } from "react";

import type { CurrentUser } from "@/shared/types/settings";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export type AuthContextValue = {
  user: CurrentUser | null;
  status: AuthStatus;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

export type PermissionContextValue = {
  permissions: Set<string>;
  roleKeys: Set<string>;
  hasPermission: (permission: string) => boolean;
  hasRole: (role: string) => boolean;
};

export const AuthContext = createContext<AuthContextValue | null>(null);
export const PermissionContext = createContext<PermissionContextValue | null>(null);
