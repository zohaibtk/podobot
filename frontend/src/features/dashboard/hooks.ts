import { useQuery } from "@tanstack/react-query";

import { getDashboardAnalytics } from "@/features/dashboard/api";
import type { DashboardAnalyticsQuery } from "@/shared/types/dashboard";

export function useDashboardAnalytics(query: DashboardAnalyticsQuery) {
  return useQuery({
    queryKey: ["dashboard-analytics", query],
    queryFn: () => getDashboardAnalytics(query)
  });
}
