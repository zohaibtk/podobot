import { createPortal } from "react-dom";
import { RotateCcw, X } from "lucide-react";

import { CursorPagination } from "@/design-system/components/CursorPagination";
import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { useBodyScrollLock } from "@/design-system/hooks/useBodyScrollLock";
import { useMCPRun, useRetryMCPRun } from "@/features/mcp/hooks";
import type { MCPToolRun } from "@/shared/types/mcp";

type MCPRunHistoryDrawerProps = {
  isOpen: boolean;
  runs: MCPToolRun[];
  isLoading?: boolean;
  isError?: boolean;
  selectedRunId?: string | null;
  title?: string;
  hasNext?: boolean;
  pageSize?: number;
  onClose: () => void;
  onLoadMore?: () => void;
  onReset?: () => void;
  onSelectRun?: (runId: string) => void;
};

export function MCPRunHistoryDrawer({
  isOpen,
  runs,
  isLoading = false,
  isError = false,
  selectedRunId,
  title = "MCP run history",
  hasNext = false,
  pageSize = 30,
  onClose,
  onLoadMore,
  onReset,
  onSelectRun
}: MCPRunHistoryDrawerProps) {
  useBodyScrollLock(isOpen);

  const activeRunId = selectedRunId ?? runs[0]?.id;
  const runQuery = useMCPRun(isOpen ? activeRunId : undefined);
  const retryMutation = useRetryMCPRun();

  if (!isOpen) {
    return null;
  }

  const drawer = (
    <div aria-modal="true" className="fixed inset-0 z-[1000] overflow-hidden bg-streamly-coal/30 backdrop-blur-sm" role="dialog">
      <aside className="ml-auto flex h-full w-full max-w-2xl flex-col border-l border-streamly-lavenderStrong bg-white shadow-streamly-soft">
        <div className="flex items-start justify-between gap-4 border-b border-streamly-lavenderStrong px-5 py-4">
          <div>
            <p className="streamly-kicker">MCP audit</p>
            <h2 className="font-streamly-platform text-xl font-extrabold text-streamly-coal">
              {title}
            </h2>
          </div>
          <button
            aria-label="Close MCP run history"
            className="grid h-9 w-9 place-items-center rounded-streamly-pill text-streamly-purpleBlue hover:bg-streamly-wash"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden className="h-4 w-4" />
          </button>
        </div>

        <div className="grid min-h-0 flex-1 md:grid-cols-[18rem_minmax(0,1fr)]">
          <div className="overflow-y-auto overscroll-contain border-r border-streamly-lavenderStrong p-4">
            {isLoading ? <LoadingState label="Loading MCP runs" /> : null}
            {isError ? (
              <ErrorState description="MCP run history could not be loaded." title="History unavailable" />
            ) : null}
            {!isLoading && !isError && runs.length === 0 ? (
              <EmptyState
                description="Tool calls will appear after workflows or agents execute through MCP."
                title="No MCP runs yet"
              />
            ) : null}
            <div className="space-y-2">
              {runs.map((run) => (
                <button
                  className={[
                    "w-full rounded-streamly-lg border px-3 py-3 text-left transition",
                    run.id === activeRunId
                      ? "border-streamly-electric bg-streamly-lavender"
                      : "border-streamly-lavenderStrong bg-white hover:bg-streamly-wash"
                  ].join(" ")}
                  key={run.id}
                  onClick={() => onSelectRun?.(run.id)}
                  type="button"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-sm font-extrabold text-streamly-coal">
                      {run.tool_key}
                    </p>
                    <StatusBadge label={run.status} tone={run.status} />
                  </div>
                  <p className="mt-1 text-xs font-bold text-streamly-purpleBlue">
                    {run.caller_type} · {new Date(run.created_at).toLocaleString()}
                  </p>
                </button>
              ))}
            </div>
            {runs.length ? (
              <div className="mt-4">
                <CursorPagination
                  hasNext={hasNext}
                  isLoading={isLoading}
                  label="MCP runs"
                  onLoadMore={() => onLoadMore?.()}
                  onReset={onReset}
                  pageSize={pageSize}
                />
              </div>
            ) : null}
          </div>

          <div className="min-w-0 overflow-y-auto overscroll-contain p-5">
            {runQuery.isLoading ? <LoadingState label="Loading MCP run detail" /> : null}
            {runQuery.isError ? (
              <ErrorState description="The selected MCP run could not be loaded." title="Run unavailable" />
            ) : null}
            {runQuery.data ? (
              <div className="space-y-5">
                <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash/70 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge label={runQuery.data.status} tone={runQuery.data.status} />
                    <StatusBadge label={runQuery.data.server_key} tone="neutral" />
                    <StatusBadge label={`attempt ${runQuery.data.attempt_number}`} tone="neutral" />
                  </div>
                  <h3 className="mt-3 font-streamly-platform text-lg font-extrabold text-streamly-coal">
                    {runQuery.data.tool_key}
                  </h3>
                  {runQuery.data.error_reason ? (
                    <p className="mt-2 text-sm font-bold text-red-700">
                      {runQuery.data.error_reason}
                    </p>
                  ) : null}
                  {runQuery.data.status === "failed" ? (
                    <button
                      className="mt-4 inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-electric px-3 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:opacity-50"
                      disabled={retryMutation.isPending}
                      onClick={() => retryMutation.mutate(runQuery.data.id)}
                      type="button"
                    >
                      <RotateCcw aria-hidden className="h-4 w-4" />
                      Retry run
                    </button>
                  ) : null}
                </section>

                <PayloadBlock label="Input" value={runQuery.data.input_payload} />
                <PayloadBlock label="Output" value={runQuery.data.output_payload ?? {}} />

                <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
                  <h4 className="font-streamly-platform text-base font-extrabold text-streamly-coal">
                    Audit timeline
                  </h4>
                  <div className="mt-4 space-y-3">
                    {runQuery.data.audit_logs.map((log) => (
                      <div
                        className="rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash/70 px-3 py-3"
                        key={log.id}
                      >
                        <p className="text-sm font-extrabold text-streamly-coal">
                          {log.action.replaceAll("_", " ")}
                        </p>
                        <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
                          {log.message}
                        </p>
                        <p className="mt-1 text-xs font-bold text-[var(--streamly-text-muted)]">
                          {new Date(log.created_at).toLocaleString()}
                        </p>
                      </div>
                    ))}
                  </div>
                </section>
              </div>
            ) : null}
          </div>
        </div>
      </aside>
    </div>
  );

  if (typeof document === "undefined") {
    return drawer;
  }

  return createPortal(drawer, document.body);
}

function PayloadBlock({ label, value }: { label: string; value: Record<string, unknown> }) {
  return (
    <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
      <h4 className="font-streamly-platform text-base font-extrabold text-streamly-coal">
        {label}
      </h4>
      <pre className="mt-3 max-h-56 overflow-auto rounded-streamly-lg bg-streamly-coal p-3 text-xs font-bold leading-5 text-white">
        {JSON.stringify(value, null, 2)}
      </pre>
    </section>
  );
}
