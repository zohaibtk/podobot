import { useContext } from "react";

import { AuthContext, PermissionContext } from "@/features/auth/authState";

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}

export function useCurrentUser() {
  return useAuth().user;
}

export function usePermissions() {
  const context = useContext(PermissionContext);
  if (!context) {
    throw new Error("usePermissions must be used inside AuthProvider");
  }
  return context;
}
