import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getResearchRun,
  getResearchRunScoreSummary,
  listDiscoveryLedger,
  listResearchDocuments,
  listResearchRuns,
  listResearchSourceUsage,
  rescoreResearchDocument,
  scoreResearchRunDocuments
} from "@/features/research/api";
import type { ResearchFilters } from "@/shared/types/research";
import { mutationToast } from "@/shared/toasts/queryToast";

export const RESEARCH_RUNS_QUERY_KEY = ["research-runs"] as const;

export function useResearchRuns(filters: ResearchFilters) {
  return useQuery({
    queryKey: [...RESEARCH_RUNS_QUERY_KEY, filters],
    queryFn: () => listResearchRuns(filters)
  });
}

export function useResearchRun(runId: string | null) {
  return useQuery({
    enabled: Boolean(runId),
    queryKey: ["research-run", runId],
    queryFn: () => getResearchRun(runId as string)
  });
}

export function useResearchRunScoreSummary(runId: string | null) {
  return useQuery({
    enabled: Boolean(runId),
    queryKey: ["research-run-score-summary", runId],
    queryFn: () => getResearchRunScoreSummary(runId as string)
  });
}

export function useScoreResearchRunDocuments() {
  const queryClient = useQueryClient();
  return useMutation({
    meta: mutationToast("Scoring research run", "Research scoring complete", "Research scoring failed"),
    mutationFn: scoreResearchRunDocuments,
    onSuccess: (_result, runId) => {
      void queryClient.invalidateQueries({ queryKey: ["research-run", runId] });
      void queryClient.invalidateQueries({ queryKey: ["research-run-score-summary", runId] });
      void queryClient.invalidateQueries({ queryKey: ["research-documents"] });
      void queryClient.invalidateQueries({ queryKey: ["research-ledger"] });
    }
  });
}

export function useRescoreResearchDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    meta: mutationToast("Rescoring document", "Document rescored", "Document rescore failed"),
    mutationFn: rescoreResearchDocument,
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["research-run", result.research_run_id] });
      void queryClient.invalidateQueries({
        queryKey: ["research-run-score-summary", result.research_run_id]
      });
      void queryClient.invalidateQueries({ queryKey: ["research-documents"] });
      void queryClient.invalidateQueries({ queryKey: ["research-ledger"] });
    }
  });
}

export function useResearchDocuments(filters: ResearchFilters, enabled = true) {
  return useQuery({
    enabled,
    queryKey: ["research-documents", filters],
    queryFn: () => listResearchDocuments(filters)
  });
}

export function useDiscoveryLedger(filters: ResearchFilters, enabled = true) {
  return useQuery({
    enabled,
    queryKey: ["research-ledger", filters],
    queryFn: () => listDiscoveryLedger(filters)
  });
}

export function useResearchSourceUsage(filters: ResearchFilters, enabled = true) {
  return useQuery({
    enabled,
    queryKey: ["research-source-usage", filters],
    queryFn: () => listResearchSourceUsage(filters)
  });
}
