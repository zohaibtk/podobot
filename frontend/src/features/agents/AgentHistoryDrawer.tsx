import { createPortal } from "react-dom";
import { X } from "lucide-react";

import { CursorPagination } from "@/design-system/components/CursorPagination";
import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { useBodyScrollLock } from "@/design-system/hooks/useBodyScrollLock";
import { AgentRunStatus } from "@/features/agents/AgentRunStatus";
import type { AgentRun } from "@/shared/types/agents";

type AgentHistoryDrawerProps = {
  isOpen: boolean;
  isLoading?: boolean;
  isError?: boolean;
  runs: AgentRun[];
  title?: string;
  hasNext?: boolean;
  pageSize?: number;
  onClose: () => void;
  onLoadMore?: () => void;
  onReset?: () => void;
  onRetry?: (run: AgentRun) => void;
};

export function AgentHistoryDrawer({
  isOpen,
  isLoading = false,
  isError = false,
  runs,
  title = "Agent history",
  hasNext = false,
  pageSize = 20,
  onClose,
  onLoadMore,
  onReset,
  onRetry
}: AgentHistoryDrawerProps) {
  useBodyScrollLock(isOpen);

  if (!isOpen) {
    return null;
  }

  const drawer = (
    <div aria-modal="true" className="fixed inset-0 z-[1000] overflow-hidden bg-streamly-coal/30 backdrop-blur-sm" role="dialog">
      <aside className="ml-auto flex h-full w-full max-w-xl flex-col border-l border-streamly-lavenderStrong bg-white shadow-streamly-soft">
        <div className="flex items-start justify-between gap-4 border-b border-streamly-lavenderStrong px-5 py-4">
          <div>
            <p className="streamly-kicker">AI audit</p>
            <h2 className="font-streamly-platform text-xl font-extrabold text-streamly-coal">
              {title}
            </h2>
          </div>
          <button
            aria-label="Close agent history"
            className="grid h-9 w-9 place-items-center rounded-streamly-pill text-streamly-purpleBlue hover:bg-streamly-wash"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden className="h-4 w-4" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-5">
          {isLoading ? <LoadingState label="Loading agent history" /> : null}
          {isError ? (
            <ErrorState description="Agent history could not be loaded." title="History unavailable" />
          ) : null}
          {!isLoading && !isError && runs.length === 0 ? (
            <EmptyState
              description="Agent runs will appear after AI actions execute inside a workflow."
              title="No agent runs yet"
            />
          ) : null}
          <div className="space-y-3">
            {runs.map((run) => (
              <div className="space-y-2" key={run.id}>
                <AgentRunStatus run={run} />
                {run.status === "failed" && onRetry ? (
                  <button
                    className="streamly-button-secondary"
                    onClick={() => onRetry(run)}
                    type="button"
                  >
                    Retry with reason
                  </button>
                ) : null}
              </div>
            ))}
          </div>
          {runs.length ? (
            <div className="mt-4">
              <CursorPagination
                hasNext={hasNext}
                isLoading={isLoading}
                label="agent runs"
                onLoadMore={() => onLoadMore?.()}
                onReset={onReset}
                pageSize={pageSize}
              />
            </div>
          ) : null}
        </div>
      </aside>
    </div>
  );

  if (typeof document === "undefined") {
    return drawer;
  }

  return createPortal(drawer, document.body);
}
