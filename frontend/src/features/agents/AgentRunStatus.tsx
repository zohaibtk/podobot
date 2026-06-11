import { AlertTriangle, CheckCircle2, Clock3, RotateCcw, ShieldCheck } from "lucide-react";

import { StatusBadge } from "@/design-system/components/StatusBadge";
import type { AgentRun } from "@/shared/types/agents";

type AgentRunStatusProps = {
  run: AgentRun;
  compact?: boolean;
};

export function AgentRunStatus({ run, compact = false }: AgentRunStatusProps) {
  const Icon = run.status === "failed" ? AlertTriangle : run.status === "running" ? Clock3 : CheckCircle2;
  const promptLabel = run.prompt_key
    ? `${run.prompt_key} v${run.prompt_version_number ?? "?"}`
    : "Prompt pending";
  const mcpRunCount = Array.isArray(run.output_metadata?.mcp_run_ids)
    ? run.output_metadata.mcp_run_ids.length
    : 0;

  return (
    <article className="rounded-streamly-card bg-white/86 p-3 shadow-streamly-card transition duration-200 hover:-translate-y-0.5 hover:shadow-streamly-elevated">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <div
            className={[
              "grid h-9 w-9 shrink-0 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric",
              run.status === "running" ? "streamly-ai-pulse" : ""
            ].join(" ")}
          >
            <Icon aria-hidden className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-extrabold capitalize text-streamly-coal">
                {run.agent_key.replaceAll("_", " ")}
              </p>
              <StatusBadge label={run.status} tone={run.status} />
            </div>
            <p className="mt-1 truncate text-xs font-bold text-streamly-purpleBlue">
              {promptLabel}
            </p>
          </div>
        </div>
        {run.retry_of_run_id ? (
          <span className="inline-flex items-center gap-1 rounded-streamly-pill bg-streamly-wash px-2 py-1 text-xs font-extrabold text-streamly-purpleBlue">
            <RotateCcw aria-hidden className="h-3.5 w-3.5" />
            Retry
          </span>
        ) : null}
      </div>

      {!compact ? (
        <>
          <p className="mt-3 line-clamp-2 font-streamly-body text-sm leading-5 text-[var(--streamly-text-muted)]">
            {run.error_reason ??
              String(run.output_payload?.summary ?? "Run history captured for this workflow.")}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs font-bold text-streamly-purpleBlue">
            <span className="inline-flex items-center gap-1">
              <ShieldCheck aria-hidden className="h-3.5 w-3.5" />
              Approval gates preserved
            </span>
            <span>{run.workflow_stage ?? "workflow"}</span>
            {mcpRunCount ? <span>{mcpRunCount} MCP run(s)</span> : null}
            <span>{new Date(run.created_at).toLocaleString()}</span>
          </div>
        </>
      ) : null}
    </article>
  );
}
