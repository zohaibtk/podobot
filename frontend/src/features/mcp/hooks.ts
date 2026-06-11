import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getMCPRun,
  getWorkflowMCPHistory,
  listMCPRuns,
  listMCPServers,
  listMCPTools,
  retryMCPRun,
  testMCPServer
} from "@/features/mcp/api";
import { mutationToast } from "@/shared/toasts/queryToast";

export const MCP_QUERY_KEY = ["mcp"] as const;

export function useMCPServers() {
  return useQuery({
    queryKey: [...MCP_QUERY_KEY, "servers"],
    queryFn: listMCPServers
  });
}

export function useMCPTools(serverKey?: string) {
  return useQuery({
    queryKey: [...MCP_QUERY_KEY, "tools", serverKey],
    queryFn: () => listMCPTools(serverKey)
  });
}

export function useMCPRuns(params: {
  entityType?: string;
  entityId?: string;
  toolKey?: string;
  serverKey?: string;
  limit?: number;
  cursor?: string | null;
} = {}) {
  return useQuery({
    queryKey: [...MCP_QUERY_KEY, "runs", params],
    queryFn: () => listMCPRuns(params)
  });
}

export function useMCPRun(runId: string | undefined) {
  return useQuery({
    queryKey: [...MCP_QUERY_KEY, "run", runId],
    queryFn: () => getMCPRun(runId as string),
    enabled: Boolean(runId)
  });
}

export function useWorkflowMCPHistory(
  entityType: string | undefined,
  entityId: string | undefined,
  limit = 20,
  cursor?: string | null
) {
  return useQuery({
    queryKey: [...MCP_QUERY_KEY, "workflow-history", entityType, entityId, limit, cursor],
    queryFn: () =>
      getWorkflowMCPHistory(entityType as string, entityId as string, limit, cursor),
    enabled: Boolean(entityType && entityId)
  });
}

export function useTestMCPServer() {
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Testing MCP server", "MCP server tested", "MCP test failed"),
    mutationFn: (serverKey: string) => testMCPServer(serverKey),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: [...MCP_QUERY_KEY, "servers"] }),
        queryClient.invalidateQueries({ queryKey: [...MCP_QUERY_KEY, "runs"] }),
        queryClient.invalidateQueries({ queryKey: [...MCP_QUERY_KEY, "workflow-history"] })
      ]);
    }
  });
}

export function useRetryMCPRun() {
  const queryClient = useQueryClient();

  return useMutation({
    meta: mutationToast("Retrying MCP run", "MCP retry started", "MCP retry failed"),
    mutationFn: (runId: string) => retryMCPRun(runId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: [...MCP_QUERY_KEY, "runs"] }),
        queryClient.invalidateQueries({ queryKey: [...MCP_QUERY_KEY, "run"] }),
        queryClient.invalidateQueries({ queryKey: [...MCP_QUERY_KEY, "workflow-history"] })
      ]);
    }
  });
}
