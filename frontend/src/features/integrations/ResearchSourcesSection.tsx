import { useMemo, useState } from "react";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  FlaskConical,
  Globe2,
  Power,
  Search,
  ShieldAlert,
  SlidersHorizontal,
  TrendingUp
} from "lucide-react";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { Pagination } from "@/design-system/components/Pagination";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { usePermissions } from "@/features/auth/hooks";
import { ResearchSourceConfigDrawer } from "@/features/integrations/ResearchSourceConfigDrawer";
import {
  useDisableResearchSource,
  useEnableResearchSource,
  useResearchSourceList,
  useTestResearchSource
} from "@/features/integrations/hooks";
import { usePaginationParams } from "@/shared/hooks/usePaginationParams";
import type {
  ResearchSource,
  ResearchSourceCategory,
  ResearchSourceProviderType,
  ResearchSourceStatus
} from "@/shared/types/researchSources";

const categoryFilters = [
  { id: "all", label: "All" },
  { id: "discovery", label: "Discovery" },
  { id: "scraping", label: "Scraping" },
  { id: "trends", label: "Trends" },
  { id: "llm", label: "LLM" }
] as const;

const statusFilters = [
  { id: "all", label: "All" },
  { id: "healthy", label: "Healthy" },
  { id: "warning", label: "Warning" },
  { id: "failed", label: "Failed" },
  { id: "disabled", label: "Disabled" },
  { id: "unknown", label: "Unknown" }
] as const;

type CategoryFilter = (typeof categoryFilters)[number]["id"];
type StatusFilter = (typeof statusFilters)[number]["id"];

const sourceDetails: Record<
  ResearchSourceProviderType,
  { detail: string; role: string }
> = {
  reddit_json: {
    detail: "Public community posts and discussion threads.",
    role: "Community signal"
  },
  hn_algolia: {
    detail: "Hacker News stories and technical discussions.",
    role: "Technical signal"
  },
  youtube_data_api: {
    detail: "Official YouTube search for channels, videos, and topics.",
    role: "Video discovery"
  },
  exa: {
    detail: "Semantic web search for fresh research documents.",
    role: "Web discovery"
  },
  firecrawl: {
    detail: "Crawls pages and extracts readable web content.",
    role: "Web scraping"
  },
  serpapi: {
    detail: "Google SERP context and ranking signals.",
    role: "Search trends"
  },
  pytrends: {
    detail: "Google Trends interest and topic momentum.",
    role: "Trend signal"
  },
  openai: {
    detail: "Primary LLM for agent generation and workflow reasoning.",
    role: "AI primary"
  },
  grok_x: {
    detail: "Optional backup after OpenAI, Gemini, and Groq are unavailable.",
    role: "AI backup"
  },
  groq: {
    detail: "Third LLM fallback when OpenAI and Gemini are unavailable.",
    role: "AI third"
  },
  gemini: {
    detail: "Secondary fallback for classification, summaries, and synthesis.",
    role: "AI fallback"
  }
};

export function ResearchSourcesSection() {
  const { hasPermission } = usePermissions();
  const canManage = hasPermission("integration.manage");
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const pagination = usePaginationParams({
    defaultPageSize: 20,
    defaultSort: "priority",
    storageKey: "podobot.integrations.sources.page_size"
  });
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ isSuccess: boolean; message: string } | null>(
    null
  );

  const filters = useMemo(
    () => ({
      page: pagination.page,
      pageSize: pagination.pageSize,
      category:
        categoryFilter === "all" ? undefined : (categoryFilter as ResearchSourceCategory),
      status: statusFilter === "all" ? undefined : (statusFilter as ResearchSourceStatus),
      search: pagination.search,
      sort: pagination.sort
    }),
    [
      categoryFilter,
      pagination.page,
      pagination.pageSize,
      pagination.search,
      pagination.sort,
      statusFilter
    ]
  );

  const sourcesQuery = useResearchSourceList(filters);
  const enableMutation = useEnableResearchSource();
  const disableMutation = useDisableResearchSource();
  const testMutation = useTestResearchSource();
  const sources = useMemo(() => sourcesQuery.data?.items ?? [], [sourcesQuery.data?.items]);
  const summary = useMemo(() => summarizeSources(sources), [sources]);
  const isMutating =
    enableMutation.isPending || disableMutation.isPending || testMutation.isPending;

  function resetToFirstPage() {
    if (pagination.page !== 1) {
      pagination.setPage(1);
    }
  }

  async function handleToggle(source: ResearchSource) {
    if (!canManage) {
      return;
    }
    setFeedback(null);
    try {
      if (source.enabled) {
        await disableMutation.mutateAsync(source.id);
        setFeedback({ isSuccess: true, message: `${source.name} disabled.` });
      } else {
        await enableMutation.mutateAsync(source.id);
        setFeedback({ isSuccess: true, message: `${source.name} enabled.` });
      }
    } catch (error) {
      setFeedback({ isSuccess: false, message: errorMessage(error) });
    }
  }

  async function handleTest(source: ResearchSource) {
    if (!canManage) {
      return;
    }
    setFeedback(null);
    try {
      const result = await testMutation.mutateAsync(source.id);
      setFeedback({ isSuccess: result.success, message: result.message });
    } catch (error) {
      setFeedback({ isSuccess: false, message: errorMessage(error) });
    }
  }

  return (
    <section className="space-y-4">
      <div className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <p className="streamly-kicker">Research sources</p>
            <h2 className="font-streamly-platform text-2xl font-extrabold text-streamly-coal">
              Source health registry
            </h2>
            <p className="mt-2 text-sm font-bold leading-6 text-streamly-purpleBlue">
              Active providers are used by Discovery. Disabled providers remain visible
              for admins but are skipped by future research runs.
            </p>
          </div>
          <div className="grid h-12 w-12 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric">
            <Globe2 aria-hidden className="h-5 w-5" />
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-4">
          <SourceMetric label="Sources" value={sourcesQuery.data?.total ?? sources.length} />
          <SourceMetric label="Active" value={summary.active} />
          <SourceMetric label="Missing keys" value={summary.missingKeys} />
          <SourceMetric label="Disabled" value={summary.disabled} />
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <label className="flex min-w-64 flex-1 items-center gap-2 rounded-streamly-pill border border-streamly-lavenderStrong bg-white px-3 py-2">
            <Search aria-hidden className="h-4 w-4 text-[var(--streamly-text-muted)]" />
            <input
              className="w-full bg-transparent text-sm font-bold text-streamly-coal outline-none placeholder:text-[var(--streamly-text-muted)]"
              onChange={(event) => pagination.setSearch(event.target.value)}
              placeholder="Search research sources"
              value={pagination.search}
            />
          </label>
          <FilterGroup
            filters={categoryFilters}
            selected={categoryFilter}
            onSelect={(value) => {
              setCategoryFilter(value);
              resetToFirstPage();
            }}
          />
          <FilterGroup
            filters={statusFilters}
            selected={statusFilter}
            onSelect={(value) => {
              setStatusFilter(value);
              resetToFirstPage();
            }}
          />
        </div>
      </div>

      {feedback ? (
        <div
          className={[
            "flex items-start gap-3 rounded-streamly-xl border px-4 py-3 text-sm font-bold",
            feedback.isSuccess
              ? "border-emerald-100 bg-emerald-50 text-emerald-700"
              : "border-red-100 bg-red-50 text-red-700"
          ].join(" ")}
        >
          {feedback.isSuccess ? (
            <CheckCircle2 aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
          ) : (
            <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
          )}
          <span>{feedback.message}</span>
        </div>
      ) : null}

      {sourcesQuery.isLoading ? <LoadingState label="Loading research sources" /> : null}

      {sourcesQuery.isError ? (
        <ErrorState
          actionLabel="Retry"
          description="Research source health could not be loaded."
          onAction={() => void sourcesQuery.refetch()}
          title="Source registry unavailable"
        />
      ) : null}

      {!sourcesQuery.isLoading && !sourcesQuery.isError && sources.length === 0 ? (
        <EmptyState
          description="Adjust filters or search terms. Research sources appear when the registry is available."
          title="No research sources match"
        />
      ) : null}

      {sources.length > 0 ? (
        <div className="grid items-stretch gap-4 md:grid-cols-2 xl:grid-cols-3">
          {sources.map((source) => (
            <SourceCard
              canManage={canManage}
              isBusy={isMutating}
              key={source.id}
              onConfigure={() => setSelectedSourceId(source.id)}
              onTest={() => void handleTest(source)}
              onToggle={() => void handleToggle(source)}
              source={source}
            />
          ))}
        </div>
      ) : null}

      {sourcesQuery.data && sourcesQuery.data.total_pages > 1 ? (
        <Pagination
          hasNext={sourcesQuery.data.has_next}
          hasPrevious={sourcesQuery.data.has_previous}
          label="sources"
          onPageChange={pagination.setPage}
          onPageSizeChange={pagination.setPageSize}
          page={sourcesQuery.data.page}
          pageSize={sourcesQuery.data.page_size}
          total={sourcesQuery.data.total}
          totalPages={sourcesQuery.data.total_pages}
        />
      ) : null}

      <ResearchSourceConfigDrawer
        canManage={canManage}
        isOpen={Boolean(selectedSourceId)}
        onClose={() => setSelectedSourceId(null)}
        sourceId={selectedSourceId}
      />
    </section>
  );
}

function SourceCard({
  canManage,
  isBusy,
  onConfigure,
  onTest,
  onToggle,
  source
}: {
  canManage: boolean;
  isBusy: boolean;
  onConfigure: () => void;
  onTest: () => void;
  onToggle: () => void;
  source: ResearchSource;
}) {
  const Icon = iconForCategory(source.category);
  const sourceDetail = sourceDetails[source.provider_type];
  const notice = sourceNotice(source);
  const NoticeIcon = notice.isSuccess ? CheckCircle2 : ShieldAlert;

  return (
    <article
      className={[
        "flex h-[25rem] min-w-0 flex-col overflow-hidden rounded-streamly-xl border bg-white p-4 shadow-streamly-card transition hover:-translate-y-0.5 hover:shadow-streamly-soft sm:p-5",
        source.status === "failed"
          ? "border-red-100"
          : source.status === "warning"
            ? "border-amber-100"
            : "border-streamly-lavenderStrong",
        !source.enabled ? "opacity-75" : ""
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric">
            <Icon aria-hidden className="h-5 w-5" />
          </span>
          <div>
            <h3 className="font-streamly-platform text-base font-extrabold text-streamly-coal">
              {source.name}
            </h3>
            <p className="mt-1 text-xs font-bold uppercase tracking-normal text-streamly-purpleBlue">
              {formatLabel(source.provider_type)} · Priority {source.priority}
            </p>
          </div>
        </div>
        <StatusBadge label={source.status} tone={source.status} />
      </div>

      <div className="mt-4 space-y-1.5 px-1 pb-1">
        <p className="line-clamp-1 text-sm font-bold leading-5 text-streamly-coal">
          {sourceDetail.detail}
        </p>
        <p className="text-xs font-extrabold uppercase tracking-normal text-streamly-purpleBlue">
          {sourceDetail.role}
        </p>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <SourceChip label={source.category} tone="neutral" />
        <SourceChip
          label={source.enabled ? "enabled" : "disabled"}
          tone={source.enabled ? "ready" : "disabled"}
        />
        <SourceChip
          label={`${source.provider_mode} mode`}
          tone={source.provider_mode === "real" ? "ready" : "warning"}
        />
        <SourceChip
          label={source.critical ? "critical" : "optional"}
          tone={source.critical ? "broken" : "neutral"}
        />
      </div>

      <div
        className={[
          "mt-3 flex min-h-12 items-start gap-2 rounded-streamly-lg px-3 py-2.5 text-xs font-bold leading-5",
          notice.isSuccess ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"
        ].join(" ")}
      >
        <NoticeIcon aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <span className="line-clamp-2">{notice.message}</span>
      </div>

      <div
        className={["mt-auto grid gap-2 pt-3", canManage ? "grid-cols-3" : "grid-cols-1"].join(
          " "
        )}
      >
        <button
          aria-label={`Configure ${source.name}`}
          className="streamly-button-secondary !min-h-9 !gap-1.5 !px-2 !py-2 text-[0.68rem]"
          onClick={onConfigure}
          type="button"
        >
          <SlidersHorizontal aria-hidden className="h-4 w-4" />
          Config
        </button>
        {canManage ? (
          <>
            <button
              className="streamly-button-secondary !min-h-9 !gap-1.5 !px-2 !py-2 text-[0.68rem] disabled:opacity-50"
              disabled={isBusy || !source.enabled}
              onClick={onTest}
              type="button"
            >
              <FlaskConical aria-hidden className="h-4 w-4" />
              Test
            </button>
            <button
              className="streamly-button-secondary !min-h-9 !gap-1.5 !px-2 !py-2 text-[0.68rem] disabled:opacity-50"
              disabled={isBusy}
              onClick={onToggle}
              type="button"
            >
              <Power aria-hidden className="h-4 w-4" />
              {source.enabled ? "Disable" : "Enable"}
            </button>
          </>
        ) : null}
      </div>
    </article>
  );
}

function FilterGroup<T extends string>({
  filters,
  onSelect,
  selected
}: {
  filters: readonly { id: T; label: string }[];
  onSelect: (value: T) => void;
  selected: T;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {filters.map((filter) => (
        <button
          className={[
            "rounded-streamly-pill px-3 py-2 text-xs font-extrabold transition",
            selected === filter.id
              ? "bg-streamly-electric text-white shadow-streamly-button"
              : "bg-streamly-wash text-streamly-purpleBlue hover:bg-streamly-lavender"
          ].join(" ")}
          key={filter.id}
          onClick={() => onSelect(filter.id)}
          type="button"
        >
          {filter.label}
        </button>
      ))}
    </div>
  );
}

function SourceMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-streamly-xl bg-streamly-wash px-4 py-3">
      <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">{label}</p>
      <p className="mt-1 font-streamly-platform text-2xl font-extrabold text-streamly-coal">
        {value.toLocaleString()}
      </p>
    </div>
  );
}

function SourceChip({
  label,
  tone
}: {
  label: string;
  tone: "broken" | "disabled" | "neutral" | "ready" | "warning";
}) {
  const toneClass = {
    broken: "bg-red-50 text-red-700",
    disabled: "bg-zinc-100 text-zinc-600",
    neutral: "bg-white text-streamly-purpleBlue",
    ready: "bg-emerald-50 text-emerald-700",
    warning: "bg-amber-50 text-amber-800"
  }[tone];

  return (
    <span
      className={[
        "inline-flex min-w-0 items-center gap-1 rounded-streamly-pill px-2 py-1 text-[0.68rem] font-extrabold capitalize leading-4",
        toneClass
      ].join(" ")}
    >
      <span className="h-1 w-1 shrink-0 rounded-streamly-pill bg-current opacity-70" />
      <span className="truncate">{formatLabel(label)}</span>
    </span>
  );
}

function summarizeSources(sources: ResearchSource[]) {
  return {
    active: sources.filter((source) => source.enabled && source.status !== "disabled").length,
    missingKeys: sources.filter((source) => source.missing_configuration).length,
    disabled: sources.filter((source) => !source.enabled || source.status === "disabled").length
  };
}

function iconForCategory(category: ResearchSourceCategory) {
  if (category === "llm") {
    return Bot;
  }
  if (category === "trends") {
    return TrendingUp;
  }
  if (category === "scraping") {
    return Globe2;
  }
  return Search;
}

function sourceNotice(source: ResearchSource) {
  if (!source.enabled || source.status === "disabled") {
    return { isSuccess: false, message: "Disabled sources are visible here but skipped by future discovery runs." };
  }
  if (source.last_failure_reason) {
    return { isSuccess: false, message: source.last_failure_reason };
  }
  if (source.missing_configuration) {
    return { isSuccess: false, message: formatLabel(source.configuration_status) };
  }
  return { isSuccess: true, message: "Ready for scheduled research runs." };
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ");
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Research source action failed.";
}
