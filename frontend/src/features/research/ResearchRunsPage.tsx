import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import {
  BookOpenText,
  Clock3,
  DatabaseZap,
  FileText,
  Filter,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  X
} from "lucide-react";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Pagination } from "@/design-system/components/Pagination";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { useBodyScrollLock } from "@/design-system/hooks/useBodyScrollLock";
import { usePermissions } from "@/features/auth/hooks";
import {
  CompositeScoreBadge,
  ConfidenceDistributionChart,
  ConfidenceLevelBadge,
  ScoreBreakdownPanel,
  ScoreExplanationPopover,
  TierBadge,
  TierDistributionChart,
  TrendScoreBadge,
  WeakEvidenceWarning
} from "@/features/research/components/Scoring";
import {
  useDiscoveryLedger,
  useRescoreResearchDocument,
  useResearchDocuments,
  useResearchRun,
  useResearchRuns,
  useResearchSourceUsage,
  useScoreResearchRunDocuments
} from "@/features/research/hooks";
import { usePaginationParams } from "@/shared/hooks/usePaginationParams";
import type {
  DiscoveryLedgerEntry,
  ResearchDocument,
  ResearchRun,
  ResearchRunDetail,
  ResearchRunStatus,
  ResearchRunType,
  ResearchScoreSummary,
  ResearchSourceUsage
} from "@/shared/types/research";

const runTypes: { value: "all" | ResearchRunType; label: string }[] = [
  { value: "all", label: "All run types" },
  { value: "discovery", label: "Discovery" },
  { value: "strategy", label: "Strategy" },
  { value: "narrative_regeneration", label: "Narrative regeneration" },
  { value: "topic_generation", label: "Topic generation" },
  { value: "brief_context", label: "Brief context" },
  { value: "manual_research", label: "Manual research" }
];

const statuses: { value: "all" | ResearchRunStatus; label: string }[] = [
  { value: "all", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "running", label: "Running" },
  { value: "completed", label: "Completed" },
  { value: "partial_success", label: "Partial success" },
  { value: "failed", label: "Failed" },
  { value: "cancelled", label: "Cancelled" }
];

export function ResearchRunsPage() {
  const pagination = usePaginationParams({
    defaultPageSize: 20,
    defaultSort: "-created_at",
    storageKey: "podobot.research.pageSize"
  });
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const status = searchParams.get("status") as ResearchRunStatus | null;
  const runType = searchParams.get("run_type") as ResearchRunType | null;
  const sourceId = searchParams.get("source_id") || undefined;

  const filters = useMemo(
    () => ({
      page: pagination.page,
      pageSize: pagination.pageSize,
      search: pagination.search,
      sort: pagination.sort,
      status: status ?? undefined,
      runType: runType ?? undefined,
      sourceId
    }),
    [pagination.page, pagination.pageSize, pagination.search, pagination.sort, runType, sourceId, status]
  );
  const runsQuery = useResearchRuns(filters);
  const runs = runsQuery.data?.items ?? [];

  function updateFilter(key: "status" | "run_type", value: string) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      if (!value || value === "all") {
        next.delete(key);
      } else {
        next.set(key, value);
      }
      next.set("page", "1");
      return next;
    });
  }

  function clearSourceFilter() {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.delete("source_id");
      next.set("page", "1");
      return next;
    });
  }

  return (
    <div className="space-y-6">
      <PageHeader
        aside={
          <div className="rounded-streamly-xl bg-streamly-lavender p-5 text-streamly-violet">
            <Sparkles aria-hidden className="h-5 w-5" />
            <p className="mt-4 text-sm font-extrabold uppercase">Transparency layer</p>
            <p className="mt-2 font-streamly-body text-sm leading-6 text-streamly-purpleBlue">
              Discovery is no longer a black box. Every persisted run keeps source,
              document, and ledger trails together.
            </p>
          </div>
        }
        description="Inspect which sources were queried, what documents were found, and how every research-backed workflow moved from query to evidence."
        kicker="Research runs"
        title="Evidence dashboard"
      />

      {runsQuery.data ? <ResearchRunStatsStrip stats={runsQuery.data.stats} /> : null}

      <section className="rounded-streamly-xl bg-white p-4 shadow-streamly-card ring-1 ring-streamly-lavenderStrong">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex min-w-72 flex-1 items-center gap-2 rounded-streamly-pill bg-streamly-wash px-4 py-3">
            <Search aria-hidden className="h-4 w-4 text-streamly-purpleBlue" />
            <input
              className="w-full bg-transparent text-sm font-bold text-streamly-coal outline-none placeholder:text-streamly-purpleBlue/70"
              onChange={(event) => pagination.setSearch(event.target.value)}
              placeholder="Search query or failure reason"
              value={pagination.search}
            />
          </label>
          <ResearchRunFilters
            runType={runType ?? "all"}
            sort={pagination.sort}
            status={status ?? "all"}
            onRunTypeChange={(value) => updateFilter("run_type", value)}
            onSortChange={pagination.setSort}
            onStatusChange={(value) => updateFilter("status", value)}
          />
          {sourceId ? (
            <button
              className="streamly-button-secondary px-3 py-2 text-xs"
              onClick={clearSourceFilter}
              type="button"
            >
              <X aria-hidden className="h-4 w-4" />
              Clear source filter
            </button>
          ) : null}
        </div>
      </section>

      {runsQuery.isLoading ? <LoadingState label="Loading research runs" /> : null}

      {runsQuery.isError ? (
        <ErrorState
          actionLabel="Retry"
          description="Research activity could not be loaded."
          onAction={() => void runsQuery.refetch()}
          title="Research unavailable"
        />
      ) : null}

      {!runsQuery.isLoading && !runsQuery.isError && runs.length === 0 ? (
        <EmptyState
          description="Run Discovery, Strategy, or a research MCP tool to create an auditable evidence trail."
          title="No research runs yet"
        />
      ) : null}

      {runs.length ? (
        <ResearchRunTable
          runs={runs}
          selectedRunId={selectedRunId}
          onSelectRun={setSelectedRunId}
        />
      ) : null}

      {runsQuery.data ? (
        <Pagination
          hasNext={runsQuery.data.has_next}
          hasPrevious={runsQuery.data.has_previous}
          label="research runs"
          onPageChange={pagination.setPage}
          onPageSizeChange={pagination.setPageSize}
          page={runsQuery.data.page}
          pageSize={runsQuery.data.page_size}
          total={runsQuery.data.total}
          totalPages={runsQuery.data.total_pages}
        />
      ) : null}

      <ResearchRunDetailDrawer
        onClose={() => setSelectedRunId(null)}
        runId={selectedRunId}
      />
    </div>
  );
}

function ResearchRunStatsStrip({
  stats
}: {
  stats: {
    total_runs: number;
    running_runs: number;
    failed_runs: number;
    total_documents_found: number;
    total_documents_used: number;
    average_duration_ms: number;
  };
}) {
  return (
    <div className="grid gap-3 md:grid-cols-5">
      <StatCard icon={DatabaseZap} label="Runs" value={stats.total_runs} />
      <StatCard icon={Clock3} label="Running" value={stats.running_runs} />
      <StatCard icon={FileText} label="Documents found" value={stats.total_documents_found} />
      <StatCard icon={ShieldCheck} label="Documents used" value={stats.total_documents_used} />
      <StatCard
        icon={BookOpenText}
        label="Avg duration"
        value={formatDuration(stats.average_duration_ms)}
      />
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value
}: {
  icon: typeof DatabaseZap;
  label: string;
  value: number | string;
}) {
  return (
    <div className="rounded-streamly-xl bg-white p-4 shadow-streamly-card ring-1 ring-streamly-lavenderStrong">
      <Icon aria-hidden className="h-4 w-4 text-streamly-electric" />
      <p className="mt-3 text-xs font-extrabold uppercase text-streamly-purpleBlue">{label}</p>
      <p className="mt-1 font-streamly-platform text-2xl font-extrabold text-streamly-coal">
        {typeof value === "number" ? value.toLocaleString() : value}
      </p>
    </div>
  );
}

function ResearchRunFilters({
  onRunTypeChange,
  onSortChange,
  onStatusChange,
  runType,
  sort,
  status
}: {
  onRunTypeChange: (value: string) => void;
  onSortChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  runType: string;
  sort: string;
  status: string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Filter aria-hidden className="h-4 w-4 text-streamly-purpleBlue" />
      <Select label="Status" onChange={onStatusChange} value={status}>
        {statuses.map((item) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
      </Select>
      <Select label="Run type" onChange={onRunTypeChange} value={runType}>
        {runTypes.map((item) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
      </Select>
      <Select label="Sort" onChange={onSortChange} value={sort}>
        <option value="-created_at">Newest</option>
        <option value="created_at">Oldest</option>
        <option value="-duration_ms">Longest</option>
        <option value="duration_ms">Shortest</option>
        <option value="status">Status</option>
      </Select>
    </div>
  );
}

function Select({
  children,
  label,
  onChange,
  value
}: {
  children: ReactNode;
  label: string;
  onChange: (value: string) => void;
  value: string;
}) {
  return (
    <label className="flex items-center gap-2 rounded-streamly-pill bg-streamly-wash px-3 py-2 text-xs font-extrabold uppercase text-streamly-purpleBlue">
      {label}
      <select
        className="bg-transparent text-sm font-extrabold normal-case text-streamly-coal outline-none"
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        {children}
      </select>
    </label>
  );
}

function ResearchRunTable({
  onSelectRun,
  runs,
  selectedRunId
}: {
  onSelectRun: (runId: string) => void;
  runs: ResearchRun[];
  selectedRunId: string | null;
}) {
  return (
    <section className="overflow-hidden rounded-streamly-xl bg-white shadow-streamly-card ring-1 ring-streamly-lavenderStrong">
      <div className="grid grid-cols-[1.4fr_10rem_9rem_10rem_10rem] gap-4 border-b border-streamly-lavenderStrong px-5 py-3 text-xs font-extrabold uppercase text-streamly-purpleBlue max-xl:hidden">
        <span>Run</span>
        <span>Status</span>
        <span>Sources</span>
        <span>Documents</span>
        <span>Started</span>
      </div>
      {runs.map((run) => (
        <button
          className={[
            "grid w-full grid-cols-1 gap-3 border-b border-streamly-lavenderStrong px-5 py-4 text-left transition last:border-b-0 hover:bg-streamly-wash xl:grid-cols-[1.4fr_10rem_9rem_10rem_10rem]",
            selectedRunId === run.id ? "bg-streamly-lavender/70" : "bg-white"
          ].join(" ")}
          key={run.id}
          onClick={() => onSelectRun(run.id)}
          type="button"
        >
          <span>
            <span className="block text-sm font-extrabold text-streamly-coal">
              {run.query_text}
            </span>
            <span className="mt-1 block text-xs font-bold uppercase text-streamly-purpleBlue">
              {formatLabel(run.run_type)}
            </span>
          </span>
          <StatusBadge label={run.status} tone={run.status} />
          <span className="text-sm font-extrabold text-streamly-coal">
            {run.successful_source_count}/{run.enabled_source_count}
          </span>
          <span className="text-sm font-extrabold text-streamly-coal">
            {run.total_documents_used}/{run.total_documents_found}
          </span>
          <span className="text-sm font-bold text-streamly-purpleBlue">
            {formatDate(run.started_at ?? run.created_at)}
          </span>
        </button>
      ))}
    </section>
  );
}

function ResearchRunDetailDrawer({
  onClose,
  runId
}: {
  onClose: () => void;
  runId: string | null;
}) {
  const { hasPermission } = usePermissions();
  const canManageResearch = hasPermission("research.manage");
  useBodyScrollLock(Boolean(runId));
  const scoreRunMutation = useScoreResearchRunDocuments();
  const [selectedDocument, setSelectedDocument] = useState<ResearchDocument | null>(null);
  const [sourceUsagePage, setSourceUsagePage] = useState(1);
  const [documentsPage, setDocumentsPage] = useState(1);
  const [ledgerPage, setLedgerPage] = useState(1);
  const [detailPageSize, setDetailPageSize] = useState(25);
  const runQuery = useResearchRun(runId);
  const sourceUsageQuery = useResearchSourceUsage({
    researchRunId: runId ?? undefined,
    page: sourceUsagePage,
    pageSize: detailPageSize,
    sort: "started_at"
  }, Boolean(runId));
  const documentsQuery = useResearchDocuments({
    researchRunId: runId ?? undefined,
    page: documentsPage,
    pageSize: detailPageSize,
    sort: "-created_at"
  }, Boolean(runId));
  const ledgerQuery = useDiscoveryLedger({
    researchRunId: runId ?? undefined,
    page: ledgerPage,
    pageSize: detailPageSize,
    sort: "-created_at"
  }, Boolean(runId));

  useEffect(() => {
    setSourceUsagePage(1);
    setDocumentsPage(1);
    setLedgerPage(1);
  }, [runId]);

  function handleDetailPageSizeChange(nextPageSize: number) {
    setDetailPageSize(nextPageSize);
    setSourceUsagePage(1);
    setDocumentsPage(1);
    setLedgerPage(1);
  }

  if (!runId) return null;

  const run = runQuery.data;
  const sourceUsage = sourceUsageQuery.data?.items ?? run?.source_usage ?? [];
  const documents = documentsQuery.data?.items ?? run?.documents ?? [];
  const ledgerEntries = ledgerQuery.data?.items ?? run?.ledger_entries ?? [];
  const scoreSummary = run?.score_summary;

  async function handleScoreRun() {
    if (!runId) {
      return;
    }
    await scoreRunMutation.mutateAsync(runId);
  }

  return (
    <div
      aria-modal="true"
      className="fixed inset-0 z-50 overflow-hidden bg-streamly-coal/35 backdrop-blur-sm"
      role="dialog"
    >
      <button
        aria-label="Close research run detail"
        className="absolute inset-0 h-full w-full cursor-default"
        onClick={onClose}
        type="button"
      />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-4xl flex-col bg-white shadow-streamly-soft">
        <div className="border-b border-streamly-lavenderStrong p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="streamly-kicker">Run detail</p>
              <h2 className="mt-2 font-streamly-platform text-2xl font-extrabold text-streamly-coal">
                {run?.query_text ?? "Research run"}
              </h2>
              {run ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  <StatusBadge label={run.status} tone={run.status} />
                  <StatusBadge label={formatLabel(run.run_type)} tone="neutral" />
                  <StatusBadge
                    label={`${run.total_documents_found} documents`}
                    tone="neutral"
                  />
                  <CompositeScoreBadge score={run.score_summary.composite_score} />
                  <ConfidenceLevelBadge level={run.score_summary.confidence_level} />
                </div>
              ) : null}
            </div>
            <button
              aria-label="Close research run detail"
              className="grid h-9 w-9 place-items-center rounded-streamly-pill text-streamly-purpleBlue hover:bg-streamly-wash"
              onClick={onClose}
              type="button"
            >
              <X aria-hidden className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-5">
          {runQuery.isLoading ? <LoadingState label="Loading research run" /> : null}
          {runQuery.isError ? (
            <ErrorState
              actionLabel="Retry"
              description="Research run details could not be loaded."
              onAction={() => void runQuery.refetch()}
              title="Run detail unavailable"
            />
          ) : null}
          {run ? (
            <div className="space-y-5">
              <RunSummary run={run} />
              {scoreSummary ? (
                <ResearchRunScoreSummaryPanel
                  canScore={canManageResearch}
                  isScoring={scoreRunMutation.isPending}
                  onScore={() => void handleScoreRun()}
                  summary={scoreSummary}
                />
              ) : null}
              <SourceUsageTimeline entries={sourceUsage} />
              {sourceUsageQuery.data && sourceUsageQuery.data.total_pages > 1 ? (
                <Pagination
                  hasNext={sourceUsageQuery.data.has_next}
                  hasPrevious={sourceUsageQuery.data.has_previous}
                  label="source usage entries"
                  onPageChange={setSourceUsagePage}
                  onPageSizeChange={handleDetailPageSizeChange}
                  page={sourceUsageQuery.data.page}
                  pageSize={sourceUsageQuery.data.page_size}
                  total={sourceUsageQuery.data.total}
                  totalPages={sourceUsageQuery.data.total_pages}
                />
              ) : null}
              <ResearchDocumentTable
                documents={documents}
                onSelectDocument={setSelectedDocument}
              />
              {documentsQuery.data && documentsQuery.data.total_pages > 1 ? (
                <Pagination
                  hasNext={documentsQuery.data.has_next}
                  hasPrevious={documentsQuery.data.has_previous}
                  label="research documents"
                  onPageChange={setDocumentsPage}
                  onPageSizeChange={handleDetailPageSizeChange}
                  page={documentsQuery.data.page}
                  pageSize={documentsQuery.data.page_size}
                  total={documentsQuery.data.total}
                  totalPages={documentsQuery.data.total_pages}
                />
              ) : null}
              <DiscoveryLedgerTable entries={ledgerEntries} />
              {ledgerQuery.data && ledgerQuery.data.total_pages > 1 ? (
                <Pagination
                  hasNext={ledgerQuery.data.has_next}
                  hasPrevious={ledgerQuery.data.has_previous}
                  label="ledger entries"
                  onPageChange={setLedgerPage}
                  onPageSizeChange={handleDetailPageSizeChange}
                  page={ledgerQuery.data.page}
                  pageSize={ledgerQuery.data.page_size}
                  total={ledgerQuery.data.total}
                  totalPages={ledgerQuery.data.total_pages}
                />
              ) : null}
            </div>
          ) : null}
        </div>
      </aside>
      <ResearchDocumentDetailDrawer
        canRescore={canManageResearch}
        document={selectedDocument}
        onClose={() => setSelectedDocument(null)}
      />
    </div>
  );
}

function RunSummary({ run }: { run: ResearchRunDetail }) {
  return (
    <section className="grid gap-3 md:grid-cols-5">
      <MiniMetric label="Duration" value={formatDuration(run.duration_ms)} />
      <MiniMetric label="Sources used" value={`${run.successful_source_count}`} />
      <MiniMetric label="Sources failed" value={`${run.failed_source_count}`} />
      <MiniMetric label="Documents used" value={`${run.total_documents_used}`} />
      <MiniMetric label="Composite" value={`${run.score_summary.composite_score}`} />
    </section>
  );
}

function ResearchRunScoreSummaryPanel({
  canScore,
  isScoring,
  onScore,
  summary
}: {
  canScore: boolean;
  isScoring: boolean;
  onScore: () => void;
  summary: ResearchScoreSummary;
}) {
  return (
    <section className="rounded-streamly-xl bg-white p-5 shadow-streamly-card ring-1 ring-streamly-lavenderStrong">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="streamly-kicker">Score summary</p>
          <h3 className="font-streamly-platform text-lg font-extrabold text-streamly-coal">
            Evidence quality at a glance
          </h3>
          <p className="mt-2 text-sm font-bold leading-6 text-streamly-purpleBlue">
            {summary.explanation}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <CompositeScoreBadge score={summary.composite_score} />
          <ConfidenceLevelBadge level={summary.confidence_level} />
          <TrendScoreBadge
            available={summary.trend_available}
            score={summary.trend_score}
          />
        </div>
      </div>
      {summary.confidence_level === "Weak" ? <WeakEvidenceWarning /> : null}
      {!summary.trend_available ? (
        <p className="mt-4 rounded-streamly-lg bg-zinc-100 px-4 py-3 text-sm font-bold text-zinc-600">
          Trend not available. This does not block generation.
        </p>
      ) : null}
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <ConfidenceDistributionChart distribution={summary.confidence_distribution} />
        <TierDistributionChart distribution={summary.tier_distribution} />
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-4">
        <MiniMetric label="Tier avg" value={`${summary.tier_score_avg}`} />
        <MiniMetric label="Engagement avg" value={`${summary.engagement_score_avg}`} />
        <MiniMetric label="Freshness avg" value={`${summary.freshness_score_avg}`} />
        <MiniMetric label="Author avg" value={`${summary.author_score_avg}`} />
      </div>
      {canScore ? (
        <button
          className="streamly-button-secondary mt-5 disabled:opacity-50"
          disabled={isScoring}
          onClick={onScore}
          type="button"
        >
          <RefreshCw aria-hidden className={isScoring ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
          {isScoring ? "Scoring documents" : "Score documents"}
        </button>
      ) : null}
    </section>
  );
}

function SourceUsageTimeline({ entries }: { entries: ResearchSourceUsage[] }) {
  return (
    <section className="rounded-streamly-xl bg-streamly-wash/70 p-5">
      <h3 className="font-streamly-platform text-lg font-extrabold text-streamly-coal">
        Source timeline
      </h3>
      <div className="mt-4 space-y-3">
        {entries.map((entry) => (
          <div
            className="grid gap-3 rounded-streamly-lg bg-white p-4 shadow-streamly-card md:grid-cols-[1fr_9rem_8rem_8rem]"
            key={entry.id}
          >
            <div>
              <p className="text-sm font-extrabold text-streamly-coal">{entry.source_name}</p>
              <p className="mt-1 text-xs font-bold uppercase text-streamly-purpleBlue">
                {formatLabel(entry.provider_type)}
              </p>
              {entry.failure_reason ? (
                <p className="mt-2 text-xs font-bold leading-5 text-red-700">
                  {entry.failure_reason}
                </p>
              ) : null}
            </div>
            <StatusBadge label={entry.status} tone={entry.status} />
            <MiniInline label="Found" value={entry.documents_found} />
            <MiniInline label="Latency" value={`${entry.latency_ms}ms`} />
          </div>
        ))}
      </div>
    </section>
  );
}

function ResearchDocumentTable({
  documents,
  onSelectDocument
}: {
  documents: ResearchDocument[];
  onSelectDocument: (document: ResearchDocument) => void;
}) {
  return (
    <section className="rounded-streamly-xl bg-white p-5 shadow-streamly-card ring-1 ring-streamly-lavenderStrong">
      <h3 className="font-streamly-platform text-lg font-extrabold text-streamly-coal">
        Documents
      </h3>
      <div className="mt-4 space-y-3">
        {documents.map((document) => (
          <article
            className="rounded-streamly-lg bg-streamly-wash p-4"
            key={document.id}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-sm font-extrabold text-streamly-coal">{document.title}</p>
                <p className="mt-1 text-xs font-bold uppercase text-streamly-purpleBlue">
                  {document.source_name} · {formatLabel(document.resource_type)}
                </p>
              </div>
              {document.url ? (
                <a
                  className="streamly-button-secondary px-3 py-2 text-xs"
                  href={document.url}
                  rel="noreferrer"
                  target="_blank"
                >
                  Open
                </a>
              ) : null}
              <button
                className="streamly-button-secondary px-3 py-2 text-xs"
                onClick={() => onSelectDocument(document)}
                type="button"
              >
                Score details
              </button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <TierBadge tier={document.tier} />
              <CompositeScoreBadge score={document.composite_score} />
              <ConfidenceLevelBadge level={document.confidence_level} />
              <TrendScoreBadge
                available={document.trend_available}
                score={document.trend_score}
              />
              <ScoreExplanationPopover explanation={document.score_explanation_json} />
            </div>
            {document.confidence_level === "Weak" ? <WeakEvidenceWarning /> : null}
            {document.content_excerpt ? (
              <p className="mt-3 font-streamly-body text-sm leading-6 text-streamly-purpleBlue">
                {document.content_excerpt}
              </p>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}

function DiscoveryLedgerTable({ entries }: { entries: DiscoveryLedgerEntry[] }) {
  return (
    <section className="rounded-streamly-xl bg-white p-5 shadow-streamly-card ring-1 ring-streamly-lavenderStrong">
      <h3 className="font-streamly-platform text-lg font-extrabold text-streamly-coal">
        Discovery ledger
      </h3>
      <div className="mt-4 space-y-3">
        {entries.map((entry) => (
          <article className="rounded-streamly-lg bg-streamly-wash p-4" key={entry.id}>
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge label={entry.ledger_type} tone="neutral" />
              <span className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
                {entry.source_name}
              </span>
            </div>
            <p className="mt-3 text-sm font-bold leading-6 text-streamly-coal">
              {entry.evidence_summary}
            </p>
            {entry.document_title ? (
              <p className="mt-2 text-xs font-bold text-streamly-purpleBlue">
                Document: {entry.document_title}
              </p>
            ) : null}
            {entry.document_id ? (
              <div className="mt-3 grid gap-2 md:grid-cols-[5rem_5rem_7rem_7rem_6rem_7rem_7rem_auto]">
                <TierBadge tier={entry.document_tier} />
                <MiniInline label="Tier" value={entry.document_tier_score ?? 0} />
                <MiniInline
                  label="Engagement"
                  value={entry.document_engagement_score ?? 0}
                />
                <MiniInline
                  label="Freshness"
                  value={entry.document_freshness_score ?? 0}
                />
                <MiniInline label="Author" value={entry.document_author_score ?? 0} />
                <CompositeScoreBadge score={entry.document_composite_score} />
                <ConfidenceLevelBadge level={entry.document_confidence_level} />
                <div>
                  <TrendScoreBadge
                    available={entry.document_trend_available}
                    score={entry.document_trend_score}
                  />
                </div>
                <ScoreExplanationPopover
                  explanation={entry.document_score_explanation_json}
                />
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}

function ResearchDocumentDetailDrawer({
  canRescore,
  document,
  onClose
}: {
  canRescore: boolean;
  document: ResearchDocument | null;
  onClose: () => void;
}) {
  const rescoreMutation = useRescoreResearchDocument();
  useBodyScrollLock(Boolean(document));
  if (!document) {
    return null;
  }
  const score = {
    tier: document.tier,
    tier_score: document.tier_score,
    engagement_score: document.engagement_score,
    freshness_score: document.freshness_score,
    author_score: document.author_score,
    composite_score: document.composite_score,
    confidence_level: document.confidence_level,
    trend_score: document.trend_score,
    trend_available: document.trend_available,
    score_explanation_json: document.score_explanation_json
  };
  return (
    <div
      aria-modal="true"
      className="fixed inset-0 z-[60] overflow-hidden bg-streamly-coal/35 backdrop-blur-sm"
      role="dialog"
    >
      <button
        aria-label="Close research document detail"
        className="absolute inset-0 h-full w-full cursor-default"
        onClick={onClose}
        type="button"
      />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-2xl flex-col bg-white shadow-streamly-soft">
        <div className="border-b border-streamly-lavenderStrong p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="streamly-kicker">Research document</p>
              <h2 className="mt-2 font-streamly-platform text-2xl font-extrabold text-streamly-coal">
                {document.title}
              </h2>
              <div className="mt-3 flex flex-wrap gap-2">
                <TierBadge tier={document.tier} />
                <CompositeScoreBadge score={document.composite_score} />
                <ConfidenceLevelBadge level={document.confidence_level} />
              </div>
            </div>
            <button
              aria-label="Close research document detail"
              className="grid h-9 w-9 place-items-center rounded-streamly-pill text-streamly-purpleBlue hover:bg-streamly-wash"
              onClick={onClose}
              type="button"
            >
              <X aria-hidden className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-5">
          <div className="space-y-5">
            <ScoreBreakdownPanel score={score} title="Document score breakdown" />
            <section className="rounded-streamly-xl bg-streamly-wash/70 p-5">
              <h3 className="font-streamly-platform text-lg font-extrabold text-streamly-coal">
                Metadata used for scoring
              </h3>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <MiniMetric label="Provider" value={formatLabel(document.provider_type)} />
                <MiniMetric label="Source" value={document.source_name} />
                <MiniMetric label="Author" value={document.author ?? "Unknown"} />
                <MiniMetric
                  label="Published"
                  value={document.published_at ? formatDate(document.published_at) : "Unknown"}
                />
              </div>
              <p className="mt-4 text-sm font-bold leading-6 text-streamly-purpleBlue">
                {document.score_explanation_json.explanation ??
                  "Score explanation will appear after scoring."}
              </p>
            </section>
            {!document.trend_available ? (
              <p className="rounded-streamly-lg bg-zinc-100 px-4 py-3 text-sm font-bold text-zinc-600">
                Trend not available. This does not block generation.
              </p>
            ) : null}
          </div>
        </div>
        {canRescore ? (
          <div className="border-t border-streamly-lavenderStrong p-5">
            <button
              className="streamly-button-primary disabled:opacity-50"
              disabled={rescoreMutation.isPending}
              onClick={() => void rescoreMutation.mutateAsync(document.id)}
              type="button"
            >
              <RefreshCw
                aria-hidden
                className={rescoreMutation.isPending ? "h-4 w-4 animate-spin" : "h-4 w-4"}
              />
              {rescoreMutation.isPending ? "Rescoring" : "Rescore document"}
            </button>
          </div>
        ) : null}
      </aside>
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-streamly-xl bg-white p-4 shadow-streamly-card ring-1 ring-streamly-lavenderStrong">
      <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">{label}</p>
      <p className="mt-1 text-lg font-extrabold text-streamly-coal">{value}</p>
    </div>
  );
}

function MiniInline({ label, value }: { label: string; value: number | string }) {
  return (
    <span>
      <span className="block text-xs font-extrabold uppercase text-streamly-purpleBlue">
        {label}
      </span>
      <span className="mt-1 block text-sm font-extrabold text-streamly-coal">{value}</span>
    </span>
  );
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ");
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString() : "Not started";
}

function formatDuration(value: number | null) {
  if (!value) return "0ms";
  if (value < 1000) return `${value}ms`;
  return `${(value / 1000).toFixed(1)}s`;
}
