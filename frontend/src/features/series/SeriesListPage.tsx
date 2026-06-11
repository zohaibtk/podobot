import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Layers3, Plus, Search, Sparkles, Trash2 } from "lucide-react";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Pagination } from "@/design-system/components/Pagination";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { usePermissions } from "@/features/auth/hooks";
import { CreateSeriesModal } from "@/features/series/CreateSeriesModal";
import { useDeleteSeries, useSeriesList } from "@/features/series/hooks";
import { currentSeriesStage, seriesStageLabel } from "@/features/series/stageProgress";
import { usePaginationParams } from "@/shared/hooks/usePaginationParams";
import type { Series } from "@/shared/types/series";

export function SeriesListPage() {
  const navigate = useNavigate();
  const [isCreateOpen, setCreateOpen] = useState(false);
  const { hasPermission } = usePermissions();
  const pagination = usePaginationParams({
    defaultPageSize: 20,
    defaultSort: "-created_at",
    storageKey: "podobot.series.page_size"
  });
  const { data, isLoading, isError, refetch } = useSeriesList({
    ...pagination.params,
    sort: "-created_at"
  });
  const deleteSeries = useDeleteSeries();
  const series = data?.items ?? [];
  const canDeleteSeries = hasPermission("series.delete");

  function openSeries(created: Series) {
    setCreateOpen(false);
    navigate(`/series/${created.id}/${currentSeriesStage(created)}`);
  }

  function handleDeleteSeries(seriesToDelete: Series) {
    if (deleteSeries.isPending) {
      return;
    }
    const confirmed = window.confirm(
      `Delete "${seriesToDelete.name}"? This removes the series from the workspace.`
    );
    if (!confirmed) {
      return;
    }
    deleteSeries.mutate(seriesToDelete.id);
  }

  return (
    <section className="streamly-page">
      <PageHeader
        actions={
          <button
            className="streamly-button-primary"
            onClick={() => setCreateOpen(true)}
            type="button"
          >
            <Plus aria-hidden className="h-4 w-4" />
            Create Series
          </button>
        }
        description="Start, inspect, and resume executive podcast series from a staged, evidence-led workspace."
        kicker="Series"
        title="Production pipeline"
      />

      <label className="flex max-w-2xl items-center gap-3 rounded-streamly-pill border border-streamly-lavenderStrong/80 bg-white/88 px-4 py-3 shadow-streamly-card transition focus-within:ring-2 focus-within:ring-streamly-electric">
        <Search aria-hidden className="h-4 w-4 text-streamly-electric" />
        <span className="sr-only">Search series</span>
        <input
          className="w-full bg-transparent text-sm font-bold text-streamly-coal outline-none placeholder:text-[var(--streamly-text-muted)]"
          onChange={(event) => pagination.setSearch(event.target.value)}
          placeholder="Search series, audiences, descriptions, or guests"
          value={pagination.search}
        />
      </label>

      {isLoading ? <LoadingState label="Loading series" /> : null}

      {isError ? (
        <ErrorState
          actionLabel="Retry"
          description="The series list could not be loaded."
          onAction={() => void refetch()}
          title="Series list unavailable"
        />
      ) : null}

      {deleteSeries.error ? (
        <ErrorState
          description={deleteSeries.error.message || "The series could not be deleted."}
          title="Delete failed"
        />
      ) : null}

      {!isLoading && !isError && series.length === 0 ? (
        <EmptyState
          description="Create the first executive podcast series to open the staged workspace."
          title="No series yet"
        />
      ) : null}

      {!isLoading && !isError && series.length > 0 ? (
        <>
          <div className="grid gap-5 lg:grid-cols-2">
            {series.map((item) => (
              <SeriesPipelineCard
                canDelete={canDeleteSeries}
                isDeleting={deleteSeries.isPending && deleteSeries.variables === item.id}
                key={item.id}
                onDelete={() => handleDeleteSeries(item)}
                series={item}
                onOpen={() => navigate(`/series/${item.id}/${currentSeriesStage(item)}`)}
              />
            ))}
          </div>
          <Pagination
            hasNext={data?.has_next ?? false}
            hasPrevious={data?.has_previous ?? false}
            label="series"
            onPageChange={pagination.setPage}
            onPageSizeChange={pagination.setPageSize}
            page={data?.page ?? pagination.page}
            pageSize={data?.page_size ?? pagination.pageSize}
            total={data?.total ?? series.length}
            totalPages={data?.total_pages ?? 1}
          />
        </>
      ) : null}

      <CreateSeriesModal
        isOpen={isCreateOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={openSeries}
      />
    </section>
  );
}

function SeriesPipelineCard({
  canDelete,
  isDeleting,
  onDelete,
  onOpen,
  series
}: {
  canDelete: boolean;
  isDeleting: boolean;
  onDelete: () => void;
  onOpen: () => void;
  series: Series;
}) {
  const stage = currentSeriesStage(series);
  const stageLabel = seriesStageLabel(stage);

  return (
    <article
      className="group streamly-premium-card min-h-[18rem] overflow-hidden p-0 text-left"
    >
      <div className="flex h-full flex-col p-5 md:p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex min-w-0 items-center gap-4">
            <span className="grid h-14 w-14 shrink-0 place-items-center rounded-streamly-panel bg-streamly-wash text-streamly-electric shadow-streamly-card">
              <Layers3 aria-hidden className="h-6 w-6" />
            </span>
            <button
              className="min-w-0 text-left"
              onClick={onOpen}
              type="button"
            >
              <span className="block truncate font-streamly-platform text-xl font-extrabold text-streamly-coal">
                {series.name}
              </span>
              <span className="mt-1 block truncate text-sm font-bold text-streamly-purpleBlue">
                {series.audience}
              </span>
            </button>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {canDelete ? (
              <button
                aria-label={`Delete ${series.name}`}
                className="grid h-9 w-9 place-items-center rounded-streamly-pill bg-red-50 text-red-700 shadow-streamly-card transition hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isDeleting}
                onClick={onDelete}
                title="Delete series"
                type="button"
              >
                <Trash2 aria-hidden className="h-4 w-4" />
              </button>
            ) : null}
            <button
              aria-label={`Open ${series.name}`}
              className="grid h-9 w-9 place-items-center rounded-streamly-pill bg-white text-streamly-electric shadow-streamly-card transition hover:-translate-y-0.5 hover:bg-streamly-wash"
              onClick={onOpen}
              type="button"
            >
              <ArrowRight
                aria-hidden
                className="h-5 w-5 transition group-hover:translate-x-1"
              />
            </button>
          </div>
        </div>

        <p className="mt-5 line-clamp-3 font-streamly-body text-sm leading-6 text-[var(--streamly-text-muted)]">
          {series.description}
        </p>

        <div className="mt-5 flex flex-wrap gap-2">
          <StatusBadge label={`Current Stage: ${stageLabel}`} tone="neutral" />
        </div>

        <div className="mt-auto pt-6">
          <button
            className="w-full rounded-streamly-panel bg-streamly-wash/70 p-4 text-left transition hover:bg-streamly-lavender/70"
            onClick={onOpen}
            type="button"
          >
            <div className="flex items-center gap-2 text-streamly-violet">
              <Sparkles aria-hidden className="h-4 w-4" />
              <span className="text-xs font-extrabold uppercase">Current stage</span>
            </div>
            <p className="mt-2 text-sm font-extrabold text-streamly-coal">
              Resume {stageLabel}
            </p>
            <p className="mt-1 text-xs font-bold leading-5 text-streamly-purpleBlue">
              Open the latest production stage for this series.
            </p>
          </button>
        </div>
      </div>
    </article>
  );
}
