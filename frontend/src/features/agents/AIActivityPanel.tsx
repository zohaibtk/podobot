import { History, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { AgentHistoryDrawer } from "@/features/agents/AgentHistoryDrawer";
import { AgentRunStatus } from "@/features/agents/AgentRunStatus";
import { RegenerationReasonModal } from "@/features/agents/RegenerationReasonModal";
import {
  useAgentRuns,
  useRetryAgentRun,
  useWorkflowAgentHistory
} from "@/features/agents/hooks";
import type { AgentRun } from "@/shared/types/agents";

type AIActivityPanelProps = {
  title?: string;
  entityType?: string;
  entityId?: string;
  agentKey?: string;
  compact?: boolean;
};

export function AIActivityPanel({
  title = "AI activity",
  entityType,
  entityId,
  agentKey,
  compact = false
}: AIActivityPanelProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [historyCursor, setHistoryCursor] = useState<string | null>(null);
  const [historyPageSize] = useState(20);
  const [retryRun, setRetryRun] = useState<AgentRun | null>(null);
  const workflowQuery = useWorkflowAgentHistory(
    entityType,
    entityId,
    historyPageSize,
    historyCursor
  );
  const listQuery = useAgentRuns({ agentKey, limit: historyPageSize, cursor: historyCursor });
  const retryMutation = useRetryAgentRun();
  const query = entityType && entityId ? workflowQuery : listQuery;
  const runs = useMemo(() => query.data?.items ?? [], [query.data?.items]);
  const visibleRuns = useMemo(() => runs.slice(0, compact ? 2 : 4), [compact, runs]);

  async function confirmRetry(reason: string) {
    if (!retryRun) {
      return;
    }
    await retryMutation.mutateAsync({
      runId: retryRun.id,
      payload: { regeneration_reason: reason }
    });
    setRetryRun(null);
  }

  return (
    <section className="streamly-panel p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric shadow-streamly-card">
            <Sparkles aria-hidden className="h-4 w-4" />
          </div>
          <div>
            <p className="streamly-kicker">Controlled AI</p>
            <h2 className="mt-1 font-streamly-platform text-lg font-extrabold text-streamly-coal">
              {title}
            </h2>
            <p className="mt-1 max-w-2xl text-sm font-bold leading-6 text-streamly-purpleBlue">
              Prompt versions, failures, retries, and approval checkpoints are auditable.
            </p>
          </div>
        </div>
        <button
          className="streamly-button-secondary"
          onClick={() => setDrawerOpen(true)}
          type="button"
        >
          <History aria-hidden className="h-4 w-4" />
          History
        </button>
      </div>

      <div className="mt-4 space-y-3">
        {query.isLoading ? <LoadingState label="Loading AI activity" /> : null}
        {query.isError ? (
          <ErrorState description="AI activity history could not be loaded." title="AI history unavailable" />
        ) : null}
        {!query.isLoading && !query.isError && runs.length === 0 ? (
          <EmptyState
            description="Auditable runs appear when generation services execute."
            title="No AI runs recorded"
          />
        ) : null}
        {visibleRuns.map((run) => (
          <AgentRunStatus compact={compact} key={run.id} run={run} />
        ))}
      </div>

      <AgentHistoryDrawer
        isError={query.isError}
        isLoading={query.isLoading}
        isOpen={drawerOpen}
        hasNext={query.data?.has_next ?? false}
        onClose={() => setDrawerOpen(false)}
        onLoadMore={() => setHistoryCursor(query.data?.next_cursor ?? null)}
        onRetry={setRetryRun}
        onReset={() => setHistoryCursor(null)}
        pageSize={query.data?.page_size ?? historyPageSize}
        runs={runs}
        title={title}
      />
      <RegenerationReasonModal
        isOpen={retryRun !== null}
        isSubmitting={retryMutation.isPending}
        onClose={() => setRetryRun(null)}
        onConfirm={(reason) => void confirmRetry(reason)}
        title="Retry failed agent run"
      />
    </section>
  );
}
