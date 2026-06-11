import {
  AlertTriangle,
  Clock3,
  ExternalLink,
  Filter,
  RefreshCw,
  RotateCcw,
  Search,
  Signal,
  Siren,
  Trash2
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Pagination } from "@/design-system/components/Pagination";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import {
  usePublishingQueue,
  usePublishingWorkspace,
  useRetryPublishingRows,
  useStopPublishingRows,
  useSyncPublishingRows
} from "@/features/publishing/hooks";
import type {
  ChannelHealthCard,
  PublishingBulkActionResponse,
  PublishingQueue,
  PublishingQueueItem
} from "@/shared/types/publishing";
import type { CaptionPlatform, ScheduleStatus } from "@/shared/types/series";
import { usePaginationParams } from "@/shared/hooks/usePaginationParams";

const STATUS_OPTIONS: Array<"all" | ScheduleStatus> = [
  "all",
  "scheduled",
  "failed",
  "published",
  "cancelled"
];

const PLATFORM_OPTIONS: Array<"all" | CaptionPlatform> = [
  "all",
  "linkedin",
  "facebook",
  "youtube",
  "instagram",
  "tiktok",
  "x"
];

export function PublishingOperationsPage() {
  const workspaceQuery = usePublishingWorkspace();
  const pagination = usePaginationParams({
    defaultPageSize: 25,
    defaultSort: "scheduled_for",
    storageKey: "podobot.publishing.page_size"
  });
  const { updateParams } = pagination;
  const [statusFilter, setStatusFilter] = useState<"all" | ScheduleStatus>("all");
  const [platformFilter, setPlatformFilter] = useState<"all" | CaptionPlatform>("all");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [lastBulkResult, setLastBulkResult] = useState<PublishingBulkActionResponse | null>(null);

  const queueFilters = useMemo(
    () => ({
      statuses: statusFilter === "all" ? undefined : [statusFilter],
      platforms: platformFilter === "all" ? undefined : [platformFilter],
      query: pagination.search,
      limit: pagination.pageSize,
      page: pagination.page,
      pageSize: pagination.pageSize
    }),
    [pagination.page, pagination.pageSize, pagination.search, platformFilter, statusFilter]
  );
  const queueQuery = usePublishingQueue(queueFilters);
  const retryRows = useRetryPublishingRows();
  const syncRows = useSyncPublishingRows();
  const stopRows = useStopPublishingRows();
  const isMutating = retryRows.isPending || syncRows.isPending || stopRows.isPending;
  const actionError = retryRows.error ?? syncRows.error ?? stopRows.error;

  const workspace = workspaceQuery.data;
  const queue = queueQuery.data ?? workspace?.queue ?? null;
  const selectedItems = useMemo(
    () => (queue?.items ?? []).filter((item) => selectedIds.has(item.id)),
    [queue?.items, selectedIds]
  );
  const retryableSelection = selectedItems.filter((item) =>
    ["failed", "cancelled"].includes(item.status)
  );
  const syncableSelection = selectedItems.filter((item) =>
    ["scheduled", "failed"].includes(item.status)
  );
  const stoppableSelection = selectedItems.filter((item) => item.status !== "published");

  useEffect(() => {
    if (!queue) {
      return;
    }
    const visibleIds = new Set(queue.items.map((item) => item.id));
    setSelectedIds((current) => new Set([...current].filter((id) => visibleIds.has(id))));
  }, [queue]);

  useEffect(() => {
    updateParams({ page: 1 });
  }, [platformFilter, statusFilter, updateParams]);

  if (workspaceQuery.isLoading) {
    return <LoadingState label="Loading publishing operations" />;
  }

  if (workspaceQuery.isError || !workspace) {
    return (
      <ErrorState
        actionLabel="Retry"
        description="Publishing operations could not be loaded."
        onAction={() => void workspaceQuery.refetch()}
        title="Publishing unavailable"
      />
    );
  }

  async function retrySelected() {
    if (!retryableSelection.length) {
      return;
    }
    const result = await retryRows.mutateAsync({
      schedule_ids: retryableSelection.map((item) => item.id)
    });
    setLastBulkResult(result);
    setSelectedIds(new Set());
  }

  async function syncSelected() {
    if (!syncableSelection.length) {
      return;
    }
    const result = await syncRows.mutateAsync({
      schedule_ids: syncableSelection.map((item) => item.id)
    });
    setLastBulkResult(result);
    setSelectedIds(new Set());
  }

  async function stopSelected() {
    if (!stoppableSelection.length) {
      return;
    }
    const result = await stopRows.mutateAsync({
      schedule_ids: stoppableSelection.map((item) => item.id)
    });
    setLastBulkResult(result);
    setSelectedIds(new Set());
  }

  async function stopOne(item: PublishingQueueItem) {
    const result = await stopRows.mutateAsync({ schedule_ids: [item.id] });
    setLastBulkResult(result);
    setSelectedIds((current) => {
      const next = new Set(current);
      next.delete(item.id);
      return next;
    });
  }

  return (
    <main className="space-y-5">
      <PageHeader
        actions={
          <div className="flex flex-wrap gap-2">
            <StatusBadge
              label={workspace.buffer_account?.status ?? "not connected"}
              tone={workspace.buffer_account?.status === "connected" ? "ready" : "missing"}
            />
            <button
              className="inline-flex items-center gap-2 rounded-streamly-pill bg-white px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-wash disabled:cursor-not-allowed disabled:opacity-50"
              disabled={workspaceQuery.isFetching || queueQuery.isFetching}
              onClick={() => {
                void workspaceQuery.refetch();
                void queueQuery.refetch();
              }}
              type="button"
            >
              <RefreshCw aria-hidden className="h-4 w-4" />
              Refresh
            </button>
          </div>
        }
        description="Monitor scheduled posts across series, sync Buffer status, and keep publishing health visible from one focused operations surface."
        kicker="Publishing operations"
        title="Publishing"
      />

      <AnalyticsStrip analytics={workspace.analytics} />

      {workspace.analytics.warnings.length ? (
        <WarningBand warnings={workspace.analytics.warnings} />
      ) : null}

      {actionError ? (
        <ErrorState description={errorMessage(actionError)} title="Publishing action failed" />
      ) : null}

      {lastBulkResult ? <BulkResultBanner result={lastBulkResult} /> : null}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <section className="space-y-5">
          <QueueToolbar
            platformFilter={platformFilter}
            query={pagination.search}
            selectedCount={selectedIds.size}
            statusFilter={statusFilter}
            onPlatformFilterChange={setPlatformFilter}
            onQueryChange={pagination.setSearch}
            onRetrySelected={() => void retrySelected()}
            onStatusFilterChange={setStatusFilter}
            onStopSelected={() => void stopSelected()}
            onSyncSelected={() => void syncSelected()}
            retryableCount={retryableSelection.length}
            syncableCount={syncableSelection.length}
            stoppableCount={stoppableSelection.length}
            isMutating={isMutating}
          />

          <PublishingQueueTable
            isLoading={queueQuery.isLoading}
            queue={queue}
            selectedIds={selectedIds}
            onSelectedIdsChange={setSelectedIds}
            onStopItem={(item) => void stopOne(item)}
            isMutating={isMutating}
          />

          {queue?.items.length ? (
            <Pagination
              hasNext={queue.has_next ?? false}
              hasPrevious={queue.has_previous ?? false}
              label="publishing rows"
              onPageChange={pagination.setPage}
              onPageSizeChange={pagination.setPageSize}
              page={queue.page ?? pagination.page}
              pageSize={queue.page_size ?? pagination.pageSize}
              total={queue.total ?? queue.total_count ?? queue.items.length}
              totalPages={queue.total_pages ?? 1}
            />
          ) : null}
        </section>

        <aside className="space-y-5">
          <ChannelHealthPanel cards={workspace.channel_health} />
        </aside>
      </div>
    </main>
  );
}

function AnalyticsStrip({ analytics }: { analytics: PublishingOperationsPageData["analytics"] }) {
  const metrics = [
    {
      label: "Scheduled",
      value: analytics.scheduled_count,
      tone: "scheduled",
      icon: Clock3
    },
    {
      label: "Failed",
      value: analytics.failed_count,
      tone: analytics.failed_count ? "failed" : "neutral",
      icon: Siren
    },
    {
      label: "Retryable",
      value: analytics.retryable_count,
      tone: analytics.retryable_count ? "scheduled" : "neutral",
      icon: RotateCcw
    },
    {
      label: "Channels",
      value: analytics.active_channel_count,
      tone: analytics.unhealthy_channel_count ? "failed" : "ready",
      icon: Signal
    }
  ] as const;

  return (
    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => {
        const Icon = metric.icon;
        return (
          <div
            className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card"
            key={metric.label}
          >
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
                {metric.label}
              </p>
              <Icon aria-hidden className="h-4 w-4 text-streamly-violet" />
            </div>
            <div className="mt-3 flex items-end justify-between gap-3">
              <p className="font-streamly-platform text-3xl font-extrabold text-streamly-coal">
                {metric.value}
              </p>
              <StatusBadge label={metric.tone} tone={metric.tone} />
            </div>
          </div>
        );
      })}
    </section>
  );
}

type PublishingOperationsPageData = NonNullable<ReturnType<typeof usePublishingWorkspace>["data"]>;

function WarningBand({ warnings }: { warnings: string[] }) {
  return (
    <section className="rounded-streamly-xl border border-amber-100 bg-amber-50 px-4 py-3 text-amber-900">
      <div className="flex items-start gap-3">
        <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
        <div className="space-y-1">
          {warnings.map((warning) => (
            <p className="text-sm font-bold" key={warning}>
              {warning}
            </p>
          ))}
        </div>
      </div>
    </section>
  );
}

function QueueToolbar({
  isMutating,
  onPlatformFilterChange,
  onQueryChange,
  onRetrySelected,
  onStatusFilterChange,
  onStopSelected,
  onSyncSelected,
  platformFilter,
  query,
  retryableCount,
  selectedCount,
  statusFilter,
  stoppableCount,
  syncableCount
}: {
  isMutating: boolean;
  onPlatformFilterChange: (platform: "all" | CaptionPlatform) => void;
  onQueryChange: (query: string) => void;
  onRetrySelected: () => void;
  onStatusFilterChange: (status: "all" | ScheduleStatus) => void;
  onStopSelected: () => void;
  onSyncSelected: () => void;
  platformFilter: "all" | CaptionPlatform;
  query: string;
  retryableCount: number;
  selectedCount: number;
  statusFilter: "all" | ScheduleStatus;
  stoppableCount: number;
  syncableCount: number;
}) {
  return (
    <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-streamly-violet">
          <Filter aria-hidden className="h-4 w-4" />
          <p className="text-xs font-extrabold uppercase">Publishing queue</p>
          {selectedCount ? <StatusBadge label={`${selectedCount} selected`} tone="neutral" /> : null}
        </div>
        {selectedCount ? (
          <div className="flex flex-wrap gap-2">
            <button
              aria-label="Sync selected"
              className="inline-flex items-center gap-2 rounded-streamly-pill bg-white px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-wash disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!syncableCount || isMutating}
              onClick={onSyncSelected}
              type="button"
            >
              <RefreshCw aria-hidden className="h-4 w-4" />
              Sync
            </button>
            <button
              aria-label="Stop selected"
              className="inline-flex items-center gap-2 rounded-streamly-pill border border-red-100 bg-white px-3 py-2 text-sm font-extrabold text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!stoppableCount || isMutating}
              onClick={onStopSelected}
              type="button"
            >
              <Trash2 aria-hidden className="h-4 w-4" />
              Stop
            </button>
            <button
              aria-label="Retry selected"
              className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-electric px-3 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!retryableCount || isMutating}
              onClick={onRetrySelected}
              type="button"
            >
              <RotateCcw aria-hidden className="h-4 w-4" />
              Retry
            </button>
          </div>
        ) : null}
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="relative block sm:col-span-2">
          <span className="sr-only">Search publishing rows</span>
          <Search
            aria-hidden
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-streamly-violet"
          />
          <input
            className="w-full rounded-streamly-lg border border-streamly-lavenderStrong bg-white py-2 pl-9 pr-3 text-sm font-bold text-streamly-coal outline-none focus:border-streamly-electric"
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Search series, episode, Buffer ID"
            type="search"
            value={query}
          />
        </label>
        <label>
          <span className="sr-only">Filter status</span>
          <select
            className="w-full rounded-streamly-lg border border-streamly-lavenderStrong bg-white px-3 py-2 text-sm font-bold text-streamly-coal outline-none focus:border-streamly-electric"
            onChange={(event) => onStatusFilterChange(event.target.value as "all" | ScheduleStatus)}
            value={statusFilter}
          >
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {statusLabel(status)}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="sr-only">Filter platform</span>
          <select
            className="w-full rounded-streamly-lg border border-streamly-lavenderStrong bg-white px-3 py-2 text-sm font-bold text-streamly-coal outline-none focus:border-streamly-electric"
            onChange={(event) =>
              onPlatformFilterChange(event.target.value as "all" | CaptionPlatform)
            }
            value={platformFilter}
          >
            {PLATFORM_OPTIONS.map((platform) => (
              <option key={platform} value={platform}>
                {platformLabel(platform)}
              </option>
            ))}
          </select>
        </label>
      </div>
    </section>
  );
}

function PublishingQueueTable({
  isMutating,
  isLoading,
  onStopItem,
  onSelectedIdsChange,
  queue,
  selectedIds
}: {
  isMutating: boolean;
  isLoading: boolean;
  onStopItem: (item: PublishingQueueItem) => void;
  onSelectedIdsChange: (ids: Set<string>) => void;
  queue: PublishingQueue | null;
  selectedIds: Set<string>;
}) {
  if (isLoading && !queue) {
    return <LoadingState label="Loading publishing queue" />;
  }
  if (!queue?.items.length) {
    return (
      <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <EmptyState
          description="No publishing rows match the current filters."
          title="Queue is clear"
        />
      </section>
    );
  }

  const allVisibleSelected = queue.items.every((item) => selectedIds.has(item.id));

  function toggleAll() {
    if (!queue) {
      return;
    }
    if (allVisibleSelected) {
      onSelectedIdsChange(new Set());
      return;
    }
    onSelectedIdsChange(new Set(queue.items.map((item) => item.id)));
  }

  function toggleOne(id: string) {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    onSelectedIdsChange(next);
  }

  return (
    <section className="overflow-hidden rounded-streamly-xl border border-streamly-lavenderStrong bg-white shadow-streamly-card">
      <div className="overflow-x-auto">
        <table className="min-w-[58rem] divide-y divide-streamly-lavenderStrong/70">
          <thead className="bg-white">
            <tr className="text-left text-xs font-extrabold uppercase text-streamly-purpleBlue">
              <th className="w-10 px-4 py-4">
                <input
                  checked={allVisibleSelected}
                  className="h-4 w-4 rounded border-streamly-lavenderStrong"
                  onChange={toggleAll}
                  type="checkbox"
                />
              </th>
              <th className="px-4 py-4">Content</th>
              <th className="px-4 py-4">Delivery</th>
              <th className="px-4 py-4">State</th>
              <th className="px-4 py-4">Channel</th>
              <th className="px-4 py-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-streamly-lavenderStrong/70">
            {queue.items.map((item) => (
              <tr className="align-top transition hover:bg-streamly-wash/35" key={item.id}>
                <td className="px-4 py-4">
                  <input
                    checked={selectedIds.has(item.id)}
                    className="h-4 w-4 rounded border-streamly-lavenderStrong"
                    onChange={() => toggleOne(item.id)}
                    type="checkbox"
                  />
                </td>
                <td className="max-w-[24rem] px-4 py-4">
                  <Link
                    className="font-streamly-platform text-sm font-extrabold text-streamly-coal hover:text-streamly-electric"
                    to={`/series/${item.series_id}/schedule`}
                  >
                    {item.series_name}
                  </Link>
                  <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
                    Ep {item.episode_number}: {item.episode_title}
                  </p>
                  <p className="mt-2 line-clamp-1 text-xs font-semibold leading-5 text-[var(--streamly-text-muted)]">
                    {item.scheduled_caption_text}
                  </p>
                  {item.failure_reason ? (
                    <p className="mt-2 line-clamp-1 rounded-streamly-lg bg-red-50 px-2 py-1 text-xs font-bold text-red-700">
                      {item.failure_reason}
                    </p>
                  ) : null}
                </td>
                <td className="min-w-[12rem] px-4 py-4">
                  <div className="flex items-center gap-2 text-sm font-extrabold text-streamly-coal">
                    <span className="h-2 w-2 rounded-streamly-pill bg-streamly-violet" />
                    {platformLabel(item.platform)}
                  </div>
                  <p className="mt-1 text-xs font-bold text-[var(--streamly-text-muted)]">
                    {item.video_kind === "short_clip" ? "Short clip" : "Full episode"}
                  </p>
                  <p className="mt-3 max-w-[11rem] text-sm font-bold leading-5 text-streamly-purpleBlue">
                    {formatDateTime(item.scheduled_for)}
                  </p>
                  {item.next_retry_at ? (
                    <p className="mt-1 text-xs text-amber-700">
                      Retry {formatDateTime(item.next_retry_at)}
                    </p>
                  ) : null}
                </td>
                <td className="min-w-[8rem] px-4 py-4">
                  <StatusBadge label={item.status} tone={item.status} />
                  <p className="mt-2 text-xs font-bold capitalize text-[var(--streamly-text-muted)]">
                    Buffer {item.buffer_status.replaceAll("_", " ")}
                  </p>
                </td>
                <td className="min-w-[11rem] px-4 py-4">
                  <p className="text-sm font-extrabold text-streamly-coal">
                    {item.channel?.display_name ?? "Unmapped"}
                  </p>
                  <p className="mt-1 max-w-[11rem] truncate text-xs font-bold text-[var(--streamly-text-muted)]">
                    {item.buffer_post_id ?? "No Buffer ID"}
                  </p>
                  {item.live_url ? (
                    <a
                      className="mt-2 inline-flex items-center gap-1 text-xs font-extrabold text-streamly-electric"
                      href={item.live_url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      <ExternalLink aria-hidden className="h-3 w-3" />
                      Live post
                    </a>
                  ) : null}
                </td>
                <td className="px-4 py-4 text-right">
                  {item.status !== "published" ? (
                    <button
                      aria-label="Stop publish"
                      className="inline-flex min-h-9 items-center gap-1.5 rounded-streamly-pill border border-red-100 bg-white px-3 py-2 text-xs font-extrabold text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={isMutating}
                      onClick={() => onStopItem(item)}
                      type="button"
                    >
                      <Trash2 aria-hidden className="h-3.5 w-3.5" />
                      Stop
                    </button>
                  ) : (
                    <span className="text-xs font-bold text-[var(--streamly-text-muted)]">
                      Published
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ChannelHealthPanel({ cards }: { cards: ChannelHealthCard[] }) {
  return (
    <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
      <div className="flex items-center gap-2 text-streamly-violet">
        <Signal aria-hidden className="h-4 w-4" />
        <p className="text-xs font-extrabold uppercase">Channel health</p>
      </div>
      <div className="mt-4 space-y-3">
        {cards.length ? (
          cards.map((card) => (
            <div className="rounded-streamly-lg border border-streamly-lavenderStrong p-3" key={card.channel.id}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-extrabold text-streamly-coal">
                    {card.channel.display_name}
                  </p>
                  <p className="mt-1 text-xs font-bold text-[var(--streamly-text-muted)]">
                    {card.mapped_platforms.map(platformLabel).join(", ") || "Unmapped"}
                  </p>
                </div>
                <StatusBadge label={card.health_status} tone={card.health_status} />
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs font-bold text-streamly-purpleBlue">
                <span>{card.scheduled_count} scheduled</span>
                <span>{card.published_count} live</span>
                <span>{card.failed_count} failed</span>
              </div>
              {card.warnings.length ? (
                <p className="mt-2 text-xs font-bold text-amber-700">{card.warnings.join(" ")}</p>
              ) : null}
            </div>
          ))
        ) : (
          <EmptyState
            description="Connect and sync Buffer channels to populate health cards."
            title="No channels synced"
          />
        )}
      </div>
    </section>
  );
}

function BulkResultBanner({ result }: { result: PublishingBulkActionResponse }) {
  return (
    <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white px-4 py-3 shadow-streamly-card">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge label={`${result.action} result`} tone="neutral" />
        <StatusBadge label={`${result.succeeded_count} succeeded`} tone="ready" />
        <StatusBadge
          label={`${result.failed_count} failed`}
          tone={result.failed_count ? "failed" : "neutral"}
        />
      </div>
      {result.results.length ? (
        <p className="mt-2 text-sm font-semibold text-streamly-purpleBlue">
          {result.results.map((item) => item.message).join(" ")}
        </p>
      ) : null}
    </section>
  );
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function platformLabel(platform: "all" | CaptionPlatform) {
  if (platform === "all") {
    return "All platforms";
  }
  if (platform === "x") {
    return "X";
  }
  return platform.charAt(0).toUpperCase() + platform.slice(1);
}

function statusLabel(status: "all" | ScheduleStatus) {
  if (status === "all") {
    return "All statuses";
  }
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Publishing operation failed.";
}
