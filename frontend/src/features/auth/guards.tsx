import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { LoadingState } from "@/design-system/components/LoadingState";
import { useAuth, usePermissions } from "@/features/auth/hooks";

type ProtectedRouteProps = {
  children: ReactNode;
  requiredPermission?: string;
  requiredRole?: string;
};

type GuardProps = {
  children: ReactNode;
  fallback?: ReactNode;
};

export function ProtectedRoute({
  children,
  requiredPermission,
  requiredRole
}: ProtectedRouteProps) {
  const { status, user } = useAuth();
  const { hasPermission, hasRole } = usePermissions();
  const location = useLocation();

  if (status === "loading") {
    return <LoadingState label="Checking permissions" />;
  }

  if (!user) {
    return <Navigate replace state={{ from: location }} to="/login" />;
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return <PermissionMessage permission={requiredPermission} title="Permission required" />;
  }

  if (requiredRole && !hasRole(requiredRole)) {
    return <PermissionMessage role={requiredRole} title="Role required" />;
  }

  return <>{children}</>;
}

export function PublicOnlyRoute({ children }: { children: ReactNode }) {
  const { status, user } = useAuth();

  if (status === "loading") {
    return <LoadingState label="Checking session" />;
  }

  if (user) {
    return <Navigate replace to="/dashboard" />;
  }

  return <>{children}</>;
}

export function PermissionGuard({
  children,
  fallback = null,
  permission
}: GuardProps & { permission: string }) {
  const { hasPermission } = usePermissions();
  return hasPermission(permission) ? <>{children}</> : <>{fallback}</>;
}

export function RoleGuard({
  children,
  fallback = null,
  role
}: GuardProps & { role: string }) {
  const { hasRole } = usePermissions();
  return hasRole(role) ? <>{children}</> : <>{fallback}</>;
}

function PermissionMessage({
  permission,
  role,
  title
}: {
  permission?: string;
  role?: string;
  title: string;
}) {
  return (
    <section className="rounded-streamly-xl border border-amber-100 bg-amber-50 p-6 text-amber-900 shadow-streamly-card">
      <p className="streamly-kicker">Access control</p>
      <h1 className="mt-2 font-streamly-platform text-2xl font-extrabold">{title}</h1>
      <p className="mt-2 max-w-2xl text-sm font-bold leading-6">
        {permission
          ? `You need the ${permission} permission to open this page.`
          : role
            ? `You need the ${role} role to open this page.`
            : "Please sign in with an authorized workspace account."}
      </p>
    </section>
  );
}
