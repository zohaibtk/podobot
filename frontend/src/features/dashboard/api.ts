import { requestJson } from "@/shared/api/httpClient";
import type { DashboardAnalytics, DashboardAnalyticsQuery } from "@/shared/types/dashboard";

export function getDashboardAnalytics(query: DashboardAnalyticsQuery) {
  const params = new URLSearchParams();
  params.set("range", query.range);
  if (query.groupBy) {
    params.set("group_by", query.groupBy);
  }
  if (query.startDate) {
    params.set("start_date", query.startDate);
  }
  if (query.endDate) {
    params.set("end_date", query.endDate);
  }
  return requestJson<DashboardAnalytics>(`/api/v1/analytics/dashboard?${params.toString()}`);
}
