import { useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  Eye,
  Flame,
  Gauge,
  Lightbulb,
  RotateCcw,
  Search,
  Sparkles,
  Target,
  XCircle
} from "lucide-react";

import { CursorPagination } from "@/design-system/components/CursorPagination";
import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { PageHeader } from "@/design-system/components/PageHeader";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { ConvertIdeaModal } from "@/features/strategy/ConvertIdeaModal";
import { IdeaReviewModal } from "@/features/strategy/IdeaReviewModal";
import {
  useConvertStrategyIdea,
  useCreateStrategyRun,
  useDismissStrategyIdea,
  useRestoreStrategyIdea,
  useReviewStrategyIdea,
  useStrategyIdeas,
  useStrategyRuns,
  useStrategySummary
} from "@/features/strategy/hooks";
import type {
  StrategyIdea,
  StrategyIdeaStatus,
  StrategyWorkspaceSummary
} from "@/shared/types/strategy";

const statusFilters = [
  { id: "new", label: "New" },
  { id: "converted", label: "Converted" },
  { id: "dismissed", label: "Dismissed" },
  { id: "all", label: "All" }
] as const;

type FilterId = (typeof statusFilters)[number]["id"];

type StrategyIdeaRunGroup = {
  run_id: string;
  run_date: string;
  run_topic: string;
  ideas: StrategyIdea[];
};

const secondaryButtonClass =
  "inline-flex items-center gap-2 rounded-streamly-pill border border-streamly-lavenderStrong bg-white px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue transition hover:bg-streamly-wash disabled:cursor-not-allowed disabled:opacity-50";

const darkButtonClass =
  "inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-coal px-3 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-50";

export function StrategyPage() {
  const navigate = useNavigate();
  const [activeFilter, setActiveFilter] = useState<FilterId>("new");
  const [query, setQuery] = useState("");
  const [ideaCursor, setIdeaCursor] = useState<string | null>(null);
  const [runCursor, setRunCursor] = useState<string | null>(null);
  const [pageSize, setPageSize] = useState(() => storedPageSize("podobot.strategy.page_size", 20));
  const [reviewIdea, setReviewIdea] = useState<StrategyIdea | null>(null);
  const [convertIdea, setConvertIdea] = useState<StrategyIdea | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const summaryQuery = useStrategySummary();
  const runsQuery = useStrategyRuns({ limit: 8, cursor: runCursor });
  const ideaStatusFilter: StrategyIdeaStatus | "all" =
    activeFilter === "converted" || activeFilter === "dismissed" ? activeFilter : "all";
  const ideasQuery = useStrategyIdeas({
    limit: pageSize,
    cursor: ideaCursor,
    status: ideaStatusFilter,
    query
  });
  const createRunMutation = useCreateStrategyRun();
  const reviewMutation = useReviewStrategyIdea();
  const dismissMutation = useDismissStrategyIdea();
  const restoreMutation = useRestoreStrategyIdea();
  const convertMutation = useConvertStrategyIdea();

  const allIdeas = useMemo(() => ideasQuery.data?.items ?? [], [ideasQuery.data?.items]);
  const visibleIdeas = useMemo(
    () => filterIdeas(allIdeas, activeFilter),
    [activeFilter, allIdeas]
  );
  const groups = useMemo(() => groupIdeas(visibleIdeas), [visibleIdeas]);
  const summary = summaryQuery.data;
  const isLoading = summaryQuery.isLoading || runsQuery.isLoading || ideasQuery.isLoading;
  const isError = summaryQuery.isError || runsQuery.isError || ideasQuery.isError;

  function updateFilter(nextFilter: FilterId) {
    setActiveFilter(nextFilter);
    setIdeaCursor(null);
  }

  function updateQuery(nextQuery: string) {
    setQuery(nextQuery);
    setIdeaCursor(null);
  }

  function updatePageSize(nextPageSize: number) {
    setPageSize(nextPageSize);
    setIdeaCursor(null);
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem("podobot.strategy.page_size", String(nextPageSize));
    }
  }

  async function handleCreateRun() {
    setActionError(null);
    try {
      await createRunMutation.mutateAsync();
    } catch (error) {
      setActionError(errorMessage(error));
    }
  }

  async function handleReview(idea: StrategyIdea) {
    setActionError(null);
    try {
      await reviewMutation.mutateAsync(idea.id);
      setReviewIdea(null);
    } catch (error) {
      setActionError(errorMessage(error));
    }
  }

  async function handleDismiss(idea: StrategyIdea) {
    setActionError(null);
    try {
      await dismissMutation.mutateAsync(idea.id);
    } catch (error) {
      setActionError(errorMessage(error));
    }
  }

  async function handleRestore(idea: StrategyIdea) {
    setActionError(null);
    try {
      await restoreMutation.mutateAsync(idea.id);
    } catch (error) {
      setActionError(errorMessage(error));
    }
  }

  async function handleConvert(idea: StrategyIdea) {
    setActionError(null);
    try {
      const response = await convertMutation.mutateAsync(idea.id);
      const convertedSeriesId =
        response.converted_series?.id ?? response.idea.converted_series_id;
      setConvertIdea(null);
      if (convertedSeriesId) {
        navigate(`/series/${convertedSeriesId}/plan`);
      }
    } catch (error) {
      setActionError(errorMessage(error));
    }
  }

  return (
    <section className="space-y-6">
      <PageHeader
        actions={
          <button
            className="streamly-button-primary disabled:opacity-50"
            disabled={createRunMutation.isPending}
            onClick={() => void handleCreateRun()}
            type="button"
          >
            <Sparkles aria-hidden className="h-4 w-4" />
            {createRunMutation.isPending ? "Scanning sources" : "Run now"}
          </button>
        }
        description="Scheduled research drafts the next podcast series opportunities from source evidence, trend movement, audience fit, and season depth."
        kicker="Strategy"
        title="Content Opportunity Intelligence"
      />

      {actionError ? (
        <div className="rounded-streamly-lg border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700">
          {actionError}
        </div>
      ) : null}

      {isLoading ? <LoadingState label="Loading opportunity intelligence" /> : null}

      {isError ? (
        <ErrorState
          actionLabel="Retry"
          description="The strategy workspace could not load research runs or opportunities."
          onAction={() => {
            void summaryQuery.refetch();
            void runsQuery.refetch();
            void ideasQuery.refetch();
          }}
          title="Strategy unavailable"
        />
      ) : null}

      {!isLoading && !isError && summary ? (
        <>
          <div className="grid gap-4 md:grid-cols-5">
            <Metric
              icon={<Lightbulb aria-hidden className="h-4 w-4" />}
              label="New opportunities"
              value={summary.new_opportunities_count}
            />
            <Metric
              icon={<Target aria-hidden className="h-4 w-4" />}
              label="High confidence"
              value={summary.high_confidence_count}
            />
            <Metric
              icon={<Flame aria-hidden className="h-4 w-4" />}
              label="Hot trends"
              value={summary.hot_trends_count}
            />
            <Metric
              icon={<CheckCircle2 aria-hidden className="h-4 w-4" />}
              label="Converted this month"
              value={summary.converted_this_month_count}
            />
            <Metric
              icon={<Gauge aria-hidden className="h-4 w-4" />}
              label="Avg opportunity score"
              suffix="/100"
              value={summary.average_opportunity_score}
            />
          </div>

          <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex min-w-72 flex-1 items-center gap-2 rounded-streamly-pill bg-streamly-wash px-4 py-3">
                <Search aria-hidden className="h-4 w-4 text-streamly-purpleBlue" />
                <span className="sr-only">Search strategy opportunities</span>
                <input
                  className="w-full bg-transparent text-sm font-bold text-streamly-coal outline-none placeholder:text-streamly-purpleBlue/70"
                  onChange={(event) => updateQuery(event.target.value)}
                  placeholder="Search opportunities, audiences, narratives, or signals"
                  value={query}
                />
              </label>
              <div className="flex flex-wrap gap-2">
                {statusFilters.map((filter) => (
                  <button
                    className={[
                      "rounded-streamly-pill px-3 py-2 text-xs font-extrabold transition",
                      activeFilter === filter.id
                        ? "bg-streamly-electric text-white shadow-streamly-button"
                        : "bg-streamly-wash text-streamly-purpleBlue hover:bg-streamly-lavender"
                    ].join(" ")}
                    key={filter.id}
                    onClick={() => updateFilter(filter.id)}
                    type="button"
                  >
                    {filter.label} {filterCount(filter.id, summary)}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {visibleIdeas.length === 0 ? (
            <EmptyState
              description="Run strategy research or change the current filter."
              title="No opportunities in this view"
            />
          ) : (
            <div className="space-y-5">
              {groups.map((group) => (
                <IdeaGroupSection
                  group={group}
                  isActionPending={
                    dismissMutation.isPending ||
                    restoreMutation.isPending ||
                    convertMutation.isPending
                  }
                  key={group.run_id}
                  onConvert={setConvertIdea}
                  onDismiss={(idea) => void handleDismiss(idea)}
                  onOpenSeries={(seriesId) => navigate(`/series/${seriesId}/plan`)}
                  onRestore={(idea) => void handleRestore(idea)}
                  onReview={setReviewIdea}
                />
              ))}

              {ideasQuery.data && (ideasQuery.data.has_next || ideaCursor) ? (
                <CursorPagination
                  hasNext={ideasQuery.data.has_next}
                  isLoading={ideasQuery.isFetching}
                  label="strategy opportunities"
                  onLoadMore={() => setIdeaCursor(ideasQuery.data.next_cursor)}
                  onPageSizeChange={updatePageSize}
                  onReset={() => setIdeaCursor(null)}
                  pageSize={pageSize}
                />
              ) : null}

              {runsQuery.data && (runsQuery.data.has_next || runCursor) ? (
                <CursorPagination
                  hasNext={runsQuery.data.has_next}
                  isLoading={runsQuery.isFetching}
                  label="research runs"
                  onLoadMore={() => setRunCursor(runsQuery.data.next_cursor)}
                  onReset={() => setRunCursor(null)}
                  pageSize={runsQuery.data.page_size}
                />
              ) : null}
            </div>
          )}
        </>
      ) : null}

      <IdeaReviewModal
        idea={reviewIdea}
        isOpen={Boolean(reviewIdea)}
        isReviewing={reviewMutation.isPending}
        onClose={() => setReviewIdea(null)}
        onMarkReview={(idea) => void handleReview(idea)}
      />

      <ConvertIdeaModal
        errorMessage={actionError}
        idea={convertIdea}
        isConverting={convertMutation.isPending}
        isOpen={Boolean(convertIdea)}
        onClose={() => setConvertIdea(null)}
        onConfirm={(idea) => void handleConvert(idea)}
      />
    </section>
  );
}

function IdeaGroupSection({
  group,
  isActionPending,
  onConvert,
  onDismiss,
  onOpenSeries,
  onRestore,
  onReview
}: {
  group: StrategyIdeaRunGroup;
  isActionPending: boolean;
  onConvert: (idea: StrategyIdea) => void;
  onDismiss: (idea: StrategyIdea) => void;
  onOpenSeries: (seriesId: string) => void;
  onRestore: (idea: StrategyIdea) => void;
  onReview: (idea: StrategyIdea) => void;
}) {
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="font-streamly-platform text-lg font-extrabold text-streamly-coal">
          {formatDate(group.run_date)}
        </h2>
        <div className="h-px min-w-12 flex-1 bg-streamly-lavenderStrong" />
        <p className="text-sm font-bold text-streamly-purpleBlue">
          {group.ideas.length} opportunities from this run
        </p>
      </div>
      <div className="space-y-3">
        {group.ideas.map((idea) => (
          <IdeaCard
            idea={idea}
            isActionPending={isActionPending}
            key={idea.id}
            onConvert={onConvert}
            onDismiss={onDismiss}
            onOpenSeries={onOpenSeries}
            onRestore={onRestore}
            onReview={onReview}
          />
        ))}
      </div>
    </section>
  );
}

function IdeaCard({
  idea,
  isActionPending,
  onConvert,
  onDismiss,
  onOpenSeries,
  onRestore,
  onReview
}: {
  idea: StrategyIdea;
  isActionPending: boolean;
  onConvert: (idea: StrategyIdea) => void;
  onDismiss: (idea: StrategyIdea) => void;
  onOpenSeries: (seriesId: string) => void;
  onRestore: (idea: StrategyIdea) => void;
  onReview: (idea: StrategyIdea) => void;
}) {
  const canDismiss = idea.status === "proposed" || idea.status === "in_review";
  const canConvert = idea.status === "proposed" || idea.status === "in_review";
  const canRestore = idea.status === "dismissed";
  const isConverted = idea.status === "converted" && idea.converted_series_id;
  const isDismissed = idea.status === "dismissed";
  const sourceEvidence = sourceEvidenceCounts(idea);
  const trend = idea.trend_intelligence;

  return (
    <article
      className={[
        "rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card transition hover:-translate-y-0.5 hover:shadow-streamly-soft",
        isDismissed ? "opacity-60" : ""
      ].join(" ")}
    >
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-streamly-pill bg-streamly-wash px-3 py-1 text-xs font-extrabold text-streamly-purpleBlue">
              {idea.audience}
            </span>
            <LifecycleBadge value={idea.lifecycle_stage} />
            <StatusBadge label={idea.status} tone={idea.status} />
          </div>
          <h3 className="mt-3 font-streamly-platform text-xl font-extrabold text-streamly-coal">
            {idea.title}
          </h3>
          <p className="mt-2 max-w-5xl text-sm font-bold leading-6 text-streamly-purpleBlue">
            {idea.description}
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-xs font-extrabold text-streamly-purpleBlue">
            <MetaPill label="confidence" value={`${idea.confidence_score}%`} />
            <MetaPill
              label="trend"
              value={
                trend.trend_available
                  ? `${trend.current_trend ?? 0}% · ${trend.velocity_label ?? "Stable"}`
                  : "not available"
              }
            />
            <MetaPill
              label="episodes"
              value={String(idea.potential_episode_count || idea.season_potential.potential_episodes || 0)}
            />
            <MetaPill label="sources" value={String(sourceEvidence.sourcesFound)} />
            <MetaPill label="generated" value={formatRelativeTime(idea.generated_at ?? idea.created_at)} />
          </div>
        </div>

        <div className="min-w-40 rounded-streamly-lg bg-streamly-wash px-4 py-3 text-center">
          <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
            Opportunity score
          </p>
          <p className="mt-1 font-streamly-platform text-4xl font-extrabold text-streamly-electric">
            {idea.opportunity_score}
          </p>
          <p className="text-xs font-extrabold text-streamly-purpleBlue">/100</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <EvidenceStat label="Sources found" value={sourceEvidence.sourcesFound} />
        <EvidenceStat label="Sources used" value={sourceEvidence.sourcesUsed} />
        <EvidenceStat label="Signals extracted" value={sourceEvidence.signalsExtracted} />
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-streamly-lavenderStrong pt-4">
        <button className={darkButtonClass} onClick={() => onReview(idea)} type="button">
          <Eye aria-hidden className="h-4 w-4" />
          Review
        </button>

        <div className="flex flex-wrap gap-2">
          {canDismiss ? (
            <button
              className={secondaryButtonClass}
              disabled={isActionPending}
              onClick={() => onDismiss(idea)}
              type="button"
            >
              <XCircle aria-hidden className="h-4 w-4" />
              Dismiss
            </button>
          ) : null}

          {canRestore ? (
            <button
              className={secondaryButtonClass}
              disabled={isActionPending}
              onClick={() => onRestore(idea)}
              type="button"
            >
              <RotateCcw aria-hidden className="h-4 w-4" />
              Restore
            </button>
          ) : null}

          {canConvert ? (
            <button
              className={secondaryButtonClass}
              disabled={isActionPending}
              onClick={() => onConvert(idea)}
              type="button"
            >
              <Sparkles aria-hidden className="h-4 w-4" />
              Convert
            </button>
          ) : null}

          {isConverted ? (
            <button
              className={darkButtonClass}
              onClick={() => onOpenSeries(idea.converted_series_id as string)}
              type="button"
            >
              <ArrowRight aria-hidden className="h-4 w-4" />
              Open Series
            </button>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function Metric({
  icon,
  label,
  suffix,
  value
}: {
  icon: ReactNode;
  label: string;
  suffix?: string;
  value: number;
}) {
  return (
    <div className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">{label}</p>
        <span className="grid h-8 w-8 place-items-center rounded-streamly-pill bg-streamly-wash text-streamly-electric">
          {icon}
        </span>
      </div>
      <p className="mt-2 font-streamly-platform text-3xl font-extrabold text-streamly-coal">
        {value}
        {suffix ? <span className="text-lg text-streamly-purpleBlue">{suffix}</span> : null}
      </p>
    </div>
  );
}

function EvidenceStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-streamly-lg bg-streamly-wash px-4 py-3">
      <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">{label}</p>
      <p className="mt-1 font-streamly-platform text-2xl font-extrabold text-streamly-coal">
        {value}
      </p>
    </div>
  );
}

function LifecycleBadge({ value }: { value: string }) {
  const normalized = value || "emerging";
  const isHot = normalized === "hot";
  return (
    <span
      className={[
        "rounded-streamly-pill px-3 py-1 text-xs font-extrabold capitalize",
        isHot
          ? "bg-red-50 text-red-700"
          : "bg-streamly-wash text-streamly-purpleBlue"
      ].join(" ")}
    >
      {isHot ? <Flame aria-hidden className="mr-1 inline h-3.5 w-3.5" /> : null}
      {normalized}
    </span>
  );
}

function MetaPill({ label, value }: { label: string; value: string }) {
  return (
    <span className="rounded-streamly-pill bg-streamly-wash px-2.5 py-1">
      {label}: <span className="text-streamly-coal">{value}</span>
    </span>
  );
}

function filterIdeas(ideas: StrategyIdea[], filter: FilterId) {
  if (filter === "new") {
    return ideas.filter((idea) => idea.status === "proposed" || idea.status === "in_review");
  }
  if (filter === "all") {
    return ideas;
  }
  return ideas.filter((idea) => idea.status === filter);
}

function groupIdeas(ideas: StrategyIdea[]): StrategyIdeaRunGroup[] {
  const groups = new Map<string, StrategyIdeaRunGroup>();
  ideas.forEach((idea) => {
    const existing = groups.get(idea.run_id);
    if (existing) {
      existing.ideas.push(idea);
      return;
    }
    groups.set(idea.run_id, {
      run_id: idea.run_id,
      run_date: idea.run_date,
      run_topic: idea.run_topic,
      ideas: [idea]
    });
  });
  return [...groups.values()];
}

function filterCount(filter: FilterId, summary: StrategyWorkspaceSummary) {
  if (filter === "new") {
    return summary.new_opportunities_count;
  }
  if (filter === "converted") {
    return summary.converted_count;
  }
  if (filter === "dismissed") {
    return summary.dismissed_count;
  }
  return (
    summary.new_opportunities_count +
    summary.converted_count +
    summary.dismissed_count
  );
}

function sourceEvidenceCounts(idea: StrategyIdea) {
  const intelligence = idea.source_proposal.opportunity_intelligence;
  return {
    sourcesFound: Number(intelligence?.sources_found ?? idea.source_count ?? 0),
    sourcesUsed: Number(intelligence?.sources_used ?? idea.source_count ?? 0),
    signalsExtracted: Number(intelligence?.signals_extracted ?? idea.evidence_signals.length)
  };
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    weekday: "long",
    month: "short",
    day: "numeric"
  }).format(new Date(`${value}T00:00:00`));
}

function formatRelativeTime(value: string) {
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) {
    return "recently";
  }
  const seconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
  if (seconds < 60) {
    return "just now";
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Strategy action failed.";
}

function storedPageSize(storageKey: string, fallback: number) {
  if (typeof window === "undefined" || !window.localStorage) {
    return fallback;
  }
  const raw = window.localStorage.getItem(storageKey);
  const parsed = raw ? Number(raw) : Number.NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}
