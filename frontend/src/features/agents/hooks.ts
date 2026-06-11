import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createPromptVersion,
  getAgentTokenStats,
  getWorkflowAgentHistory,
  listAgentRuns,
  listAgents,
  listPrompts,
  retryAgentRun,
  runAgent
} from "@/features/agents/api";
import type {
  AgentRunPayload,
  AgentRunRetryPayload,
  AgentTokenStatsPeriod,
  PromptVersionPayload
} from "@/shared/types/agents";
import { mutationToast } from "@/shared/toasts/queryToast";

export function useAgents() {
  return useQuery({
    queryKey: ["agents"],
    queryFn: listAgents
  });
}

export function usePrompts() {
  return useQuery({
    queryKey: ["prompts"],
    queryFn: listPrompts
  });
}

export function useAgentRuns(params: {
  entityType?: string;
  entityId?: string;
  agentKey?: string;
  limit?: number;
  cursor?: string | null;
} = {}) {
  return useQuery({
    queryKey: ["agent-runs", params],
    queryFn: () => listAgentRuns(params)
  });
}

export function useAgentTokenStats(period: AgentTokenStatsPeriod) {
  return useQuery({
    queryKey: ["agent-token-stats", period],
    queryFn: () => getAgentTokenStats(period)
  });
}

export function useWorkflowAgentHistory(
  entityType: string | undefined,
  entityId: string | undefined,
  limit = 20,
  cursor?: string | null
) {
  return useQuery({
    queryKey: ["workflow-agent-history", entityType, entityId, limit, cursor],
    queryFn: () =>
      getWorkflowAgentHistory(entityType as string, entityId as string, limit, cursor),
    enabled: Boolean(entityType && entityId)
  });
}

export function useRunAgent(agentKey: string | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Running agent", "Agent run started", "Agent run failed"),
    mutationFn: (payload: AgentRunPayload) => runAgent(agentKey as string, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["agent-runs"] }),
        queryClient.invalidateQueries({ queryKey: ["workflow-agent-history"] })
      ]);
    }
  });
}

export function useRetryAgentRun() {
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Retrying agent run", "Agent retry started", "Agent retry failed"),
    mutationFn: ({ runId, payload }: { runId: string; payload: AgentRunRetryPayload }) =>
      retryAgentRun(runId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["agent-runs"] }),
        queryClient.invalidateQueries({ queryKey: ["workflow-agent-history"] })
      ]);
    }
  });
}

export function useCreatePromptVersion(promptKey: string | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Saving prompt version", "Prompt version saved", "Prompt save failed"),
    mutationFn: (payload: PromptVersionPayload) =>
      createPromptVersion(promptKey as string, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["prompts"] }),
        queryClient.invalidateQueries({ queryKey: ["agents"] })
      ]);
    }
  });
}
