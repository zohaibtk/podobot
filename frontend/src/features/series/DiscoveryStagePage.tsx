import { useEffect, useState } from "react";
import { ArrowRight, ChevronDown, Loader2, ShieldCheck } from "lucide-react";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { ScoreExplanationPopover } from "@/features/research/components/Scoring";
import {
  useDiscoveryWorkspace,
  useRunDiscovery
} from "@/features/series/hooks";
import { StageHeaderNextButton } from "@/features/series/StageHeaderNextButton";
import type { ScoreExplanation } from "@/shared/types/research";
import type {
  DiscoveryLedgerEntry,
  DiscoverySourceActivity
} from "@/shared/types/series";

type DiscoveryStagePageProps = {
  seriesId: string;
};

export function DiscoveryStagePage({ seriesId }: DiscoveryStagePageProps) {
  const { data, isLoading, isError, refetch } = useDiscoveryWorkspace(seriesId);
  const runDiscovery = useRunDiscovery(seriesId);

  if (isLoading) {
    return <LoadingState label="Loading discovery workspace" />;
  }

  if (isError || !data) {
    return (
      <ErrorState
        actionLabel="Retry"
        description="Discovery progress and narrative options could not be loaded."
        onAction={() => void refetch()}
        title="Discovery unavailable"
      />
    );
  }

  const hasLedger = data.ledger.length > 0;
  const shouldPromptDiscovery = !hasLedger && !runDiscovery.isPending;

  return (
    <div className="space-y-6">
      <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="streamly-kicker">Discovery</p>
            <h2 className="font-streamly-platform text-2xl font-extrabold text-streamly-coal">
              {hasLedger
                ? "Research mapped the strongest editorial signals"
                : "Ready to run discovery"}
            </h2>
            <p className="mt-2 max-w-2xl font-streamly-body text-sm leading-6 text-streamly-purpleBlue">
              {hasLedger
                ? "Discovery shows source ledger progress, extracted signals, and narrative options from the same evidence base."
                : "Discovery has not started yet. Click Run discovery to collect source signals and create narrative options for this series."}
            </p>
          </div>
          <div className="flex w-full flex-wrap justify-end gap-3 sm:w-auto">
            <button
              className={[
                "streamly-button-secondary",
                shouldPromptDiscovery ? "streamly-attention-button" : ""
              ]
                .filter(Boolean)
                .join(" ")}
              disabled={runDiscovery.isPending}
              onClick={() => runDiscovery.mutate()}
              type="button"
            >
              <ArrowRight
                aria-hidden
                className={[
                  "h-4 w-4",
                  shouldPromptDiscovery ? "streamly-attention-icon" : ""
                ]
                  .filter(Boolean)
                  .join(" ")}
              />
              {runDiscovery.isPending ? "Running discovery..." : hasLedger ? "Run again" : "Run discovery"}
            </button>
            <StageHeaderNextButton
              disabled={!hasLedger}
              disabledTitle="Run discovery before moving to Narrative."
              nextStage="narrative"
              seriesId={seriesId}
            />
          </div>
        </div>

        {runDiscovery.isPending || hasLedger ? (
          <ProgressTimeline
            isProcessing={runDiscovery.isPending}
            progressPercent={data.progress_percent}
          />
        ) : null}
      </section>

      <ResearchActivitySummary
        activity={data.research_activity}
        isProcessing={runDiscovery.isPending || data.series.discovery_status === "running"}
      />

      {hasLedger ? (
        <SourceLedgerTable entries={data.ledger} />
      ) : (
        <EmptyState
          description="Discovery has not started yet. Click Run discovery above to begin collecting source signals and narrative options."
          title="Discovery has not run yet"
        />
      )}

      {runDiscovery.error ? (
        <ErrorState
          description={runDiscovery.error.message || "Discovery failed. Existing research records are unchanged."}
          title="Discovery action failed"
        />
      ) : null}
    </div>
  );
}

function ResearchActivitySummary({
  activity,
  isProcessing
}: {
  activity?: {
    run_count: number;
    sources_queried: number;
    sources_failed: number;
    sources_skipped: number;
    documents_found: number;
    documents_used: number;
    latest_run_status?: string | null;
    source_activity?: DiscoverySourceActivity[];
  };
  isProcessing: boolean;
}) {
  const [isCollapsed, setCollapsed] = useState(false);
  const safeActivity = activity ?? {
    run_count: 0,
    sources_queried: 0,
    sources_failed: 0,
    sources_skipped: 0,
    documents_found: 0,
    documents_used: 0,
    latest_run_status: null,
    source_activity: []
  };
  const sourceActivity = safeActivity.source_activity ?? [];
  const successfulSourceActivity = sourceActivity.filter(isSuccessfulSourceActivity);

  useEffect(() => {
    if (isProcessing) {
      setCollapsed(false);
    }
  }, [isProcessing]);

  return (
    <section className="rounded-streamly-xl bg-white p-5 shadow-streamly-card ring-1 ring-streamly-lavenderStrong">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="streamly-kicker">Research activity</p>
          <h2 className="font-streamly-platform text-lg font-extrabold text-streamly-coal">
            Source activity for this discovery stage
          </h2>
          <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
            Track each provider and the number of source items discovered for this series.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isProcessing ? (
            <StatusBadge label="processing" tone="running" />
          ) : (
            <StatusBadge label={`${safeActivity.run_count} run(s)`} tone="neutral" />
          )}
          <button
            aria-expanded={!isCollapsed}
            className="grid h-9 w-9 place-items-center rounded-streamly-pill bg-streamly-wash text-streamly-purpleBlue transition hover:bg-streamly-lavender"
            onClick={() => setCollapsed((value) => !value)}
            title={isCollapsed ? "Expand research activity" : "Collapse research activity"}
            type="button"
          >
            <ChevronDown
              aria-hidden
              className={[
                "h-4 w-4 transition-transform",
                isCollapsed ? "-rotate-90" : "rotate-0"
              ].join(" ")}
            />
          </button>
        </div>
      </div>

      {!isCollapsed ? (
        <div className="mt-5 overflow-hidden rounded-streamly-lg border border-streamly-lavenderStrong">
          {successfulSourceActivity.length > 0 ? (
            successfulSourceActivity.map((source) => (
              <ResearchSourceActivityRow
                isProcessing={isProcessing}
                key={source.id}
                source={source}
              />
            ))
          ) : isProcessing ? (
            <div className="flex items-center gap-3 bg-streamly-wash px-4 py-4">
              <Loader2
                aria-hidden
                className="h-4 w-4 animate-spin text-streamly-electric"
              />
              <div>
                <p className="text-sm font-extrabold text-streamly-coal">
                  Research sources are processing
                </p>
                <p className="mt-1 text-xs font-bold text-streamly-purpleBlue">
                  Source-level counts will appear as soon as the run completes.
                </p>
              </div>
            </div>
          ) : (
            <div className="bg-streamly-wash px-4 py-4 text-sm font-bold text-streamly-purpleBlue">
              No successful source activity recorded yet.
            </div>
          )}
        </div>
      ) : null}
    </section>
  );
}

function isSuccessfulSourceActivity(source: DiscoverySourceActivity) {
  return source.status === "used";
}

function ResearchSourceActivityRow({
  isProcessing,
  source
}: {
  isProcessing: boolean;
  source: DiscoverySourceActivity;
}) {
  const statusLabel = isProcessing ? "processing" : source.status;
  const statusTone = isProcessing ? "running" : source.status;
  const displayStatusLabel = statusLabel === "used" ? "complete" : statusLabel;
  const displayStatusTone = statusTone === "used" ? "complete" : statusTone;

  return (
    <div className="grid gap-4 border-b border-streamly-lavenderStrong bg-white px-4 py-4 last:border-b-0 md:grid-cols-[minmax(0,1.4fr)_9rem_9rem_9rem] md:items-center">
      <div className="flex min-w-0 items-center gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-streamly-pill bg-streamly-wash text-streamly-electric">
          {isProcessing ? (
            <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
          ) : (
            <ShieldCheck aria-hidden className="h-4 w-4" />
          )}
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-extrabold text-streamly-coal">
            {source.source_name}
          </p>
          <p className="mt-1 truncate text-xs font-bold text-streamly-purpleBlue">
            {source.source_key.replaceAll("_", " ")}
            {source.latency_ms ? ` · ${source.latency_ms.toLocaleString()} ms` : ""}
          </p>
          {source.failure_reason ? (
            <p className="mt-1 line-clamp-2 text-xs font-bold text-red-700">
              {source.failure_reason}
            </p>
          ) : null}
        </div>
      </div>
      <StatusBadge label={displayStatusLabel} tone={displayStatusTone} />
      <SourceCount label="Discovered" value={source.documents_found} />
      <SourceCount label="In ledger" value={source.documents_used} />
    </div>
  );
}

function SourceCount({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-streamly-lg bg-streamly-wash px-3 py-2">
      <p className="text-[0.68rem] font-extrabold uppercase text-streamly-purpleBlue">
        {label}
      </p>
      <p className="mt-1 font-streamly-platform text-lg font-extrabold text-streamly-coal">
        {value.toLocaleString()}
      </p>
    </div>
  );
}

function ProgressTimeline({
  isProcessing,
  progressPercent
}: {
  isProcessing: boolean;
  progressPercent: number;
}) {
  const displayedProgress = isProcessing ? Math.max(progressPercent, 28) : progressPercent;

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between text-sm font-bold text-streamly-purpleBlue">
        <span>Source progress</span>
        {isProcessing ? (
          <span className="inline-flex items-center gap-2 text-streamly-violet">
            <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
            Processing sources · {displayedProgress}%
          </span>
        ) : (
          <span>{progressPercent}%</span>
        )}
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-streamly-pill bg-streamly-wash">
        <div
          className={[
            "h-full rounded-streamly-pill bg-streamly-electric transition-all",
            isProcessing ? "animate-pulse" : ""
          ].join(" ")}
          style={{ width: `${displayedProgress}%` }}
        />
      </div>
      {isProcessing ? (
        <p className="mt-3 text-xs font-bold text-streamly-purpleBlue">
          Querying enabled research sources and ranking evidence for the ledger.
        </p>
      ) : null}
    </div>
  );
}

function SourceLedgerTable({ entries }: { entries: DiscoveryLedgerEntry[] }) {
  return (
    <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white shadow-streamly-card">
      <div className="flex items-center gap-2 border-b border-streamly-lavenderStrong px-5 py-4">
        <ShieldCheck aria-hidden className="h-4 w-4 text-streamly-electric" />
        <h2 className="font-streamly-platform text-lg font-extrabold text-streamly-coal">
          Research source ledger
        </h2>
      </div>
      <div className="grid grid-cols-[minmax(12rem,0.9fr)_8rem_minmax(0,1.6fr)_10rem] border-b border-streamly-lavenderStrong px-5 py-3 text-xs font-extrabold uppercase text-streamly-purpleBlue">
        <span>Source</span>
        <span>Status</span>
        <span>Signal</span>
        <span className="text-right">Confidence</span>
      </div>
      {entries.map((entry) => (
        <div
          key={entry.id}
          className="grid grid-cols-[minmax(12rem,0.9fr)_8rem_minmax(0,1.6fr)_10rem] items-start gap-4 border-b border-streamly-lavenderStrong px-5 py-4 text-left transition last:border-b-0 hover:bg-streamly-wash"
        >
          <div className="min-w-0">
            <a
              className="block break-words text-sm font-extrabold text-streamly-coal transition hover:text-streamly-electric"
              href={entry.source_url}
              rel="noreferrer"
              target="_blank"
            >
              {entry.source_name}
            </a>
            <span className="mt-1 block text-xs font-bold text-streamly-purpleBlue">
              {entry.source_type}
            </span>
          </div>
          <StatusBadge label={entry.status} tone={entry.status} />
          <div className="min-w-0">
            <a
              className="block break-words text-sm font-extrabold text-streamly-coal transition hover:text-streamly-electric"
              href={entry.source_url}
              rel="noreferrer"
              target="_blank"
            >
              {entry.signal_title}
            </a>
            <span className="mt-1 block font-streamly-body text-xs leading-5 text-[var(--streamly-text-muted)]">
              {entry.signal_summary}
            </span>
          </div>
          <LedgerConfidence entry={entry} />
        </div>
      ))}
    </section>
  );
}

function LedgerConfidence({ entry }: { entry: DiscoveryLedgerEntry }) {
  return (
    <div className="flex min-w-0 flex-wrap items-center justify-end gap-2 text-right">
      <span className="font-streamly-platform text-sm font-extrabold text-streamly-violet">
        {entry.confidence_score}%
      </span>
      <ScoreExplanationPopover
        explanation={entry.score_explanation_json ?? confidenceFallback(entry)}
        showFormula={false}
        showMessage={false}
      />
    </div>
  );
}

function confidenceFallback(entry: DiscoveryLedgerEntry): ScoreExplanation {
  const score = Math.max(0, Math.min(entry.confidence_score, 100));
  return {
    formula:
      "tier_score * 0.50 + engagement_score * 0.25 + freshness_score * 0.15 + author_score * 0.10",
    confidence_level: score >= 85 ? "High" : score >= 65 ? "Medium" : score >= 40 ? "Low" : "Weak",
    composite_score: score,
    explanation: `Confidence ${score}% is the ledger confidence captured for this source. Component scores were not available for this entry.`
  };
}
