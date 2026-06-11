import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/shell/AppShell";
import { AIStatsPage } from "@/features/ai-stats/AIStatsPage";
import { AuthProvider } from "@/features/auth/AuthContext";
import { LoginPage } from "@/features/auth/LoginPage";
import { ProtectedRoute, PublicOnlyRoute } from "@/features/auth/guards";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { ProfileLibraryPage } from "@/features/profiles/ProfileLibraryPage";
import { PublishingOperationsPage } from "@/features/publishing/PublishingOperationsPage";
import { ResearchRunsPage } from "@/features/research/ResearchRunsPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { SeriesDetailShell } from "@/features/series/SeriesDetailShell";
import { SeriesListPage } from "@/features/series/SeriesListPage";
import { StrategyPage } from "@/features/strategy/StrategyPage";
import { FoundationScreen } from "@/routes/FoundationScreen";
import { foundationRoutes } from "@/routes/routeRegistry";
import { Toaster } from "@/shared/toasts/Toaster";
import {
  handleMutationToastFailure,
  handleMutationToastStart,
  handleMutationToastSuccess
} from "@/shared/toasts/queryToast";

const queryClient = new QueryClient({
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      handleMutationToastFailure(mutation, error);
    },
    onMutate: (_variables, mutation) => {
      handleMutationToastStart(mutation);
    },
    onSuccess: (_data, _variables, _context, mutation) => {
      handleMutationToastSuccess(mutation);
    }
  }),
  defaultOptions: {
    queries: {
      staleTime: 20_000,
      retry: 1
    }
  }
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Routes>
          <Route
            path="/login"
            element={
              <PublicOnlyRoute>
                <LoginPage />
              </PublicOnlyRoute>
            }
          />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <AppShell>
                  <AuthenticatedRoutes />
                </AppShell>
              </ProtectedRoute>
            }
          />
        </Routes>
        <Toaster />
      </AuthProvider>
    </QueryClientProvider>
  );
}

function AuthenticatedRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate replace to="/dashboard" />} />
      <Route path="/command-center" element={<Navigate replace to="/dashboard" />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/ai-stats" element={<AIStatsPage />} />
      <Route path="/series" element={<SeriesListPage />} />
      <Route path="/series/:seriesId/:stage?" element={<SeriesDetailShell />} />
      <Route path="/strategy" element={<StrategyPage />} />
      <Route
        path="/research"
        element={
          <ProtectedRoute requiredPermission="research.view">
            <ResearchRunsPage />
          </ProtectedRoute>
        }
      />
      <Route path="/profiles" element={<ProfileLibraryPage />} />
      <Route path="/publishing" element={<PublishingOperationsPage />} />
      <Route path="/publishing/analytics" element={<Navigate replace to="/publishing" />} />
      <Route path="/media" element={<Navigate replace to="/dashboard" />} />
      <Route path="/ai-platform" element={<Navigate replace to="/dashboard" />} />
      <Route path="/ai-platform/evaluations" element={<Navigate replace to="/dashboard" />} />
      <Route path="/integrations" element={<Navigate replace to="/settings?tab=integrations" />} />
      <Route
        path="/settings"
        element={
          <ProtectedRoute requiredPermission="settings.manage">
            <SettingsPage />
          </ProtectedRoute>
        }
      />
      {foundationRoutes.map((route) => (
        <Route
          key={route.path}
          path={route.path}
          element={<FoundationScreen route={route} />}
        />
      ))}
    </Routes>
  );
}
