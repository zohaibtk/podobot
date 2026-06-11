import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  convertStrategyIdea,
  createStrategyRun,
  dismissStrategyIdea,
  getStrategySummary,
  getStrategyWorkspace,
  listStrategyIdeas,
  listStrategyRuns,
  restoreStrategyIdea,
  reviewStrategyIdea
} from "@/features/strategy/api";
import type { StrategySummaryRange } from "@/features/strategy/api";
import type { StrategyIdeaStatus } from "@/shared/types/strategy";
import { mutationToast } from "@/shared/toasts/queryToast";

const STRATEGY_QUERY_KEY = ["strategy"] as const;

export function useStrategyWorkspace() {
  return useQuery({
    queryKey: STRATEGY_QUERY_KEY,
    queryFn: getStrategyWorkspace
  });
}

export function useStrategySummary(range: StrategySummaryRange = "30d") {
  return useQuery({
    queryKey: [...STRATEGY_QUERY_KEY, "summary", range],
    queryFn: () => getStrategySummary(range)
  });
}

export function useStrategyRuns(params: { limit?: number; cursor?: string | null } = {}) {
  return useQuery({
    queryKey: [...STRATEGY_QUERY_KEY, "runs", params],
    queryFn: () => listStrategyRuns(params)
  });
}

export function useStrategyIdeas(params: {
  limit?: number;
  cursor?: string | null;
  status?: StrategyIdeaStatus | "all";
  runId?: string | null;
  query?: string;
} = {}) {
  return useQuery({
    queryKey: [...STRATEGY_QUERY_KEY, "ideas", params],
    queryFn: () => listStrategyIdeas(params)
  });
}

function useStrategyInvalidation() {
  const queryClient = useQueryClient();

  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: STRATEGY_QUERY_KEY }),
      queryClient.invalidateQueries({ queryKey: [...STRATEGY_QUERY_KEY, "runs"] }),
      queryClient.invalidateQueries({ queryKey: [...STRATEGY_QUERY_KEY, "ideas"] }),
      queryClient.invalidateQueries({ queryKey: ["series"] })
    ]);
  };
}

export function useCreateStrategyRun() {
  const invalidate = useStrategyInvalidation();

  return useMutation({
    meta: mutationToast("Scanning strategy sources", "Strategy scan started", "Strategy scan failed"),
    mutationFn: createStrategyRun,
    onSuccess: invalidate
  });
}

export function useReviewStrategyIdea() {
  const invalidate = useStrategyInvalidation();

  return useMutation({
    meta: mutationToast("Marking for review", "Opportunity moved to review", "Review update failed"),
    mutationFn: (ideaId: string) => reviewStrategyIdea(ideaId),
    onSuccess: invalidate
  });
}

export function useDismissStrategyIdea() {
  const invalidate = useStrategyInvalidation();

  return useMutation({
    meta: mutationToast("Dismissing opportunity", "Opportunity dismissed", "Dismiss failed"),
    mutationFn: (ideaId: string) => dismissStrategyIdea(ideaId),
    onSuccess: invalidate
  });
}

export function useRestoreStrategyIdea() {
  const invalidate = useStrategyInvalidation();

  return useMutation({
    meta: mutationToast("Restoring opportunity", "Opportunity restored", "Restore failed"),
    mutationFn: (ideaId: string) => restoreStrategyIdea(ideaId),
    onSuccess: invalidate
  });
}

export function useConvertStrategyIdea() {
  const invalidate = useStrategyInvalidation();

  return useMutation({
    meta: mutationToast("Creating series workspace", "Series workspace created", "Conversion failed"),
    mutationFn: (ideaId: string) => convertStrategyIdea(ideaId),
    onSuccess: invalidate
  });
}
