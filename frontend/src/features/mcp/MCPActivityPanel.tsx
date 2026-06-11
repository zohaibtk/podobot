import { History, Wrench } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { MCPRunHistoryDrawer } from "@/features/mcp/MCPRunHistoryDrawer";
import { useWorkflowMCPHistory } from "@/features/mcp/hooks";

type MCPActivityPanelProps = {
  entityType: string;
  entityId: string;
  title?: string;
};

export function MCPActivityPanel({
  entityType,
  entityId,
  title = "MCP tool activity"
}: MCPActivityPanelProps) {
  const historyQuery = useWorkflowMCPHistory(entityType, entityId, 8);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const runs = historyQuery.data?.items ?? [];

  return (
    <section className="streamly-panel p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric shadow-streamly-card">
            <Wrench aria-hidden className="h-4 w-4" />
          </div>
          <div>
            <p className="streamly-kicker">MCP</p>
            <h3 className="mt-1 font-streamly-platform text-base font-extrabold text-streamly-coal">
              {title}
            </h3>
          </div>
        </div>
        <button
          className="streamly-button-secondary"
          onClick={() => setIsHistoryOpen(true)}
          type="button"
        >
          <History aria-hidden className="h-3.5 w-3.5" />
          History
        </button>
      </div>

      <div className="mt-4">
        {historyQuery.isLoading ? <LoadingState label="Loading MCP activity" /> : null}
        {historyQuery.isError ? (
          <ErrorState description="MCP tool history could not be loaded." title="MCP unavailable" />
        ) : null}
        {!historyQuery.isLoading && !historyQuery.isError && runs.length === 0 ? (
          <EmptyState
            description="Tool calls will appear after Buffer, agents, or workflow services execute through MCP."
            title="No MCP tool calls yet"
          />
        ) : null}
        <div className="space-y-2">
          {runs.slice(0, 4).map((run) => (
            <button
              className="flex w-full items-center justify-between gap-3 rounded-streamly-card bg-white/86 px-3 py-3 text-left shadow-streamly-card transition hover:-translate-y-0.5 hover:bg-white hover:shadow-streamly-elevated"
              key={run.id}
              onClick={() => {
                setSelectedRunId(run.id);
                setIsHistoryOpen(true);
              }}
              type="button"
            >
              <span className="min-w-0">
                <span className="block truncate text-sm font-extrabold text-streamly-coal">
                  {run.tool_key}
                </span>
                <span className="mt-1 block text-xs font-bold text-streamly-purpleBlue">
                  {run.caller_type} · {new Date(run.created_at).toLocaleString()}
                </span>
              </span>
              <StatusBadge label={run.status} tone={run.status} />
            </button>
          ))}
        </div>
      </div>

      <MCPRunHistoryDrawer
        isError={historyQuery.isError}
        isLoading={historyQuery.isLoading}
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectRun={setSelectedRunId}
        runs={runs}
        selectedRunId={selectedRunId}
        title={title}
      />
    </section>
  );
}
