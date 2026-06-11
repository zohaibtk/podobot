import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  ExternalLink,
  LockKeyhole,
  Pencil,
  RefreshCw,
  RotateCcw,
  Rows3,
  Scissors,
  Send,
  XCircle
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { BulkScheduleModal } from "@/features/series/BulkScheduleModal";
import { ScheduleModal, type ScheduleModalMode } from "@/features/series/ScheduleModal";
import {
  useBulkSchedule,
  useCancelSchedule,
  useCreateSchedule,
  useReschedulePost,
  useScheduleWorkspace,
  useSyncScheduleStatuses,
  useUpdateSchedule
} from "@/features/series/hooks";
import type {
  BulkSchedulePayload,
  PublishingAuditLog,
  ScheduleCreatePayload,
  ScheduleEpisodeWorkspace,
  ScheduleReschedulePayload,
  ScheduleRow,
  ScheduleShortClipSlot,
  ScheduleUpdatePayload
} from "@/shared/types/series";

type ScheduleModalState = {
  mode: ScheduleModalMode;
  row: ScheduleRow;
} | null;

export function SchedulingStagePage({ seriesId }: { seriesId: string }) {
  const workspaceQuery = useScheduleWorkspace(seriesId);
  const createSchedule = useCreateSchedule(seriesId);
  const bulkSchedule = useBulkSchedule(seriesId);
  const updateSchedule = useUpdateSchedule(seriesId);
  const reschedulePost = useReschedulePost(seriesId);
  const cancelSchedule = useCancelSchedule(seriesId);
  const syncStatuses = useSyncScheduleStatuses(seriesId);
  const [activeEpisodeId, setActiveEpisodeId] = useState<string | null>(null);
  const [scheduleModal, setScheduleModal] = useState<ScheduleModalState>(null);
  const [isBulkOpen, setIsBulkOpen] = useState(false);

  const episodes = useMemo(
    () => workspaceQuery.data?.episodes ?? [],
    [workspaceQuery.data?.episodes]
  );
  const activeEpisode = useMemo(
    () =>
      episodes.find((episode) => episode.episode_id === activeEpisodeId) ??
      episodes[0] ??
      null,
    [activeEpisodeId, episodes]
  );
  const hasScheduledRows = useMemo(
    () =>
      episodes.some(
        (episode) =>
          episode.full_episode_rows.some((row) => row.schedule?.status === "scheduled") ||
          episode.short_clip_slots.some((slot) =>
            slot.rows.some((row) => row.schedule?.status === "scheduled")
          )
      ),
    [episodes]
  );
  const bulkRows = useMemo(() => eligibleBulkRows(episodes), [episodes]);
  const mutationError = [
    createSchedule.error,
    bulkSchedule.error,
    updateSchedule.error,
    reschedulePost.error,
    cancelSchedule.error,
    syncStatuses.error
  ].find(Boolean);
  const isMutating =
    createSchedule.isPending ||
    bulkSchedule.isPending ||
    updateSchedule.isPending ||
    reschedulePost.isPending ||
    cancelSchedule.isPending ||
    syncStatuses.isPending;

  useEffect(() => {
    if (!activeEpisodeId && episodes[0]) {
      setActiveEpisodeId(episodes[0].episode_id);
    }
  }, [activeEpisodeId, episodes]);

  useEffect(() => {
    if (!hasScheduledRows) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      void workspaceQuery.refetch();
    }, 30_000);

    return () => window.clearInterval(intervalId);
  }, [hasScheduledRows, workspaceQuery.refetch]);

  if (workspaceQuery.isLoading) {
    return <LoadingState label="Loading scheduling workspace" />;
  }

  if (workspaceQuery.isError || !workspaceQuery.data) {
    return (
      <ErrorState
        actionLabel="Retry"
        description="The Scheduling workspace could not be loaded."
        onAction={() => void workspaceQuery.refetch()}
        title="Scheduling unavailable"
      />
    );
  }

  if (!episodes.length) {
    return (
      <EmptyState
        description="Generate at least one platform caption before scheduling Buffer posts."
        title="No caption rows available"
      />
    );
  }

  async function submitScheduleModal(
    row: ScheduleRow,
    payload: ScheduleCreatePayload | ScheduleUpdatePayload | ScheduleReschedulePayload
  ) {
    if (scheduleModal?.mode === "create") {
      await createSchedule.mutateAsync(payload as ScheduleCreatePayload);
      return;
    }
    if (!row.schedule) {
      return;
    }
    if (scheduleModal?.mode === "edit") {
      await updateSchedule.mutateAsync({
        scheduleId: row.schedule.id,
        payload: payload as ScheduleUpdatePayload
      });
      return;
    }
    await reschedulePost.mutateAsync({
      scheduleId: row.schedule.id,
      payload: payload as ScheduleReschedulePayload
    });
  }

  async function submitBulkSchedule(payload: BulkSchedulePayload) {
    await bulkSchedule.mutateAsync(payload);
  }

  async function cancel(row: ScheduleRow) {
    if (!row.schedule) {
      return;
    }
    const confirmed = window.confirm(
      "Stop this publish item? This removes it from Buffer and returns the row to scheduling."
    );
    if (!confirmed) {
      return;
    }
    await cancelSchedule.mutateAsync(row.schedule.id);
  }

  const readiness = workspaceQuery.data.readiness;
  const bulkResult = bulkSchedule.data?.bulk_result ?? workspaceQuery.data.bulk_result;
  const bufferWarnings = workspaceQuery.data.buffer?.warnings ?? [];

  return (
    <main className="space-y-5">
      <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge label="Buffer" tone="neutral" />
              <StatusBadge
                label={`${readiness.scheduled_row_count} scheduled`}
                tone={readiness.scheduled_row_count ? "scheduled" : "neutral"}
              />
              <StatusBadge
                label={`${readiness.published_row_count} published`}
                tone={readiness.published_row_count ? "published" : "neutral"}
              />
            </div>
            <h2 className="mt-3 font-streamly-platform text-2xl font-extrabold text-streamly-coal">
              Scheduling
            </h2>
            <p className="mt-2 max-w-3xl font-streamly-body text-sm leading-6 text-streamly-purpleBlue">
              Schedule captioned video/platform rows into Buffer, monitor publishing status, and recover failed posts without changing uncaptioned rows.
            </p>
            {bufferWarnings.length ? (
              <div className="mt-4 max-w-3xl rounded-streamly-xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm font-bold leading-6 text-amber-900">
                <div className="flex gap-2">
                  <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
                  <div className="space-y-1">
                    {bufferWarnings.map((warning) => (
                      <p key={warning}>{warning}</p>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="inline-flex items-center gap-2 rounded-streamly-pill bg-white px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-wash disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isMutating}
              onClick={() => syncStatuses.mutate()}
              type="button"
            >
              <RefreshCw aria-hidden className="h-4 w-4" />
              Sync Buffer
            </button>
            <button
              className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-electric px-3 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!bulkRows.length || isMutating}
              onClick={() => setIsBulkOpen(true)}
              type="button"
            >
              <Send aria-hidden className="h-4 w-4" />
              Bulk schedule
            </button>
          </div>
        </div>
      </section>

      {mutationError ? (
        <ErrorState description={errorMessage(mutationError)} title="Scheduling action failed" />
      ) : null}

      {bulkResult ? <BulkResultBanner result={bulkResult} /> : null}

      <div className="grid gap-5 2xl:grid-cols-[18rem_minmax(0,1fr)]">
        <EpisodeScheduleSelector
          activeEpisodeId={activeEpisode?.episode_id ?? null}
          episodes={episodes}
          onSelect={(episode) => setActiveEpisodeId(episode.episode_id)}
        />

        <section className="min-w-0 space-y-4">
          {activeEpisode ? (
            <>
              <EpisodeScheduleBanner episode={activeEpisode} />
              <ScheduleGrid
                isMutating={isMutating}
                onCancel={(row) => void cancel(row)}
                onEdit={(row) => setScheduleModal({ mode: "edit", row })}
                onReschedule={(row) => setScheduleModal({ mode: "reschedule", row })}
                onSchedule={(row) => setScheduleModal({ mode: "create", row })}
                rows={activeEpisode.full_episode_rows}
                title="Full episode platform schedule"
                videoLabel="Full episode"
              />
              <ShortClipScheduleGrid
                episode={activeEpisode}
                isMutating={isMutating}
                onCancel={(row) => void cancel(row)}
                onEdit={(row) => setScheduleModal({ mode: "edit", row })}
                onReschedule={(row) => setScheduleModal({ mode: "reschedule", row })}
                onSchedule={(row) => setScheduleModal({ mode: "create", row })}
              />
            </>
          ) : null}
        </section>

      </div>

      <ScheduleModal
        isOpen={scheduleModal !== null}
        isSubmitting={isMutating}
        mode={scheduleModal?.mode ?? "create"}
        onClose={() => setScheduleModal(null)}
        onSubmit={submitScheduleModal}
        row={scheduleModal?.row ?? null}
      />

      <BulkScheduleModal
        isOpen={isBulkOpen}
        isSubmitting={bulkSchedule.isPending}
        onClose={() => setIsBulkOpen(false)}
        onSubmit={submitBulkSchedule}
        rows={bulkRows}
      />
    </main>
  );
}

function EpisodeScheduleSelector({
  activeEpisodeId,
  episodes,
  onSelect
}: {
  activeEpisodeId: string | null;
  episodes: ScheduleEpisodeWorkspace[];
  onSelect: (episode: ScheduleEpisodeWorkspace) => void;
}) {
  return (
    <aside className="space-y-2">
      {episodes.map((episode) => {
        const isActive = episode.episode_id === activeEpisodeId;
        const statusLabel = episode.failed_count
          ? `${episode.failed_count} failed`
          : episode.published_count
            ? `${episode.published_count} published`
            : episode.scheduled_count
              ? `${episode.scheduled_count} scheduled`
              : `${episode.eligible_count} ready`;

        return (
          <button
            className={[
              "w-full rounded-streamly-xl border p-4 text-left shadow-streamly-card transition",
              isActive
                ? "border-streamly-electric bg-white"
                : "border-streamly-lavenderStrong bg-white/82 hover:bg-streamly-wash"
            ].join(" ")}
            key={episode.episode_id}
            onClick={() => onSelect(episode)}
            type="button"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="grid h-9 w-9 place-items-center rounded-streamly-lg bg-streamly-lavender font-streamly-platform text-sm font-extrabold text-streamly-electric">
                {episode.episode_number}
              </span>
              <StatusBadge
                label={statusLabel}
                tone={episode.failed_count ? "failed" : episode.scheduled_count ? "scheduled" : "neutral"}
              />
            </div>
            <p className="mt-3 line-clamp-2 text-sm font-extrabold text-streamly-coal">
              {episode.episode_title}
            </p>
            <p className="mt-1 text-xs font-bold text-[var(--streamly-text-muted)]">
              {episode.locked_count} locked · {episode.eligible_count} ready
            </p>
          </button>
        );
      })}
    </aside>
  );
}

function EpisodeScheduleBanner({ episode }: { episode: ScheduleEpisodeWorkspace }) {
  const needsCaptions = episode.locked_count > 0;
  return (
    <div
      className={[
        "rounded-streamly-xl border px-4 py-3 shadow-streamly-card",
        needsCaptions
          ? "border-amber-100 bg-amber-50 text-amber-900"
          : "border-streamly-lavenderStrong bg-white text-streamly-coal"
      ].join(" ")}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-extrabold">
            Episode {episode.episode_number}: {episode.episode_title}
          </p>
          <p className="mt-1 text-sm font-bold">
            {needsCaptions
              ? `${episode.locked_count} row(s) still need captions or clip media before scheduling.`
              : "Every platform row in this episode is captioned."}
          </p>
        </div>
        <StatusBadge label={episode.episode_status} tone={episode.episode_status} />
      </div>
    </div>
  );
}

function ScheduleGrid({
  isMutating,
  onCancel,
  onEdit,
  onReschedule,
  onSchedule,
  rows,
  title,
  videoLabel
}: {
  isMutating: boolean;
  onCancel: (row: ScheduleRow) => void;
  onEdit: (row: ScheduleRow) => void;
  onReschedule: (row: ScheduleRow) => void;
  onSchedule: (row: ScheduleRow) => void;
  rows: ScheduleRow[];
  title: string;
  videoLabel: string;
}) {
  return (
    <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white shadow-streamly-card">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-streamly-lavenderStrong p-4">
        <div>
          <div className="flex items-center gap-2 text-streamly-violet">
            <Rows3 aria-hidden className="h-4 w-4" />
            <p className="text-xs font-extrabold uppercase">{title}</p>
          </div>
          <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
            Scheduling is managed per captioned video/platform row.
          </p>
        </div>
      </div>
      <div className="divide-y divide-streamly-lavenderStrong">
        {rows.length ? (
          rows.map((row) => (
            <ScheduleGridRow
              isMutating={isMutating}
              key={row.caption_id}
              onCancel={onCancel}
              onEdit={onEdit}
              onReschedule={onReschedule}
              onSchedule={onSchedule}
              row={row}
              videoLabel={videoLabel}
            />
          ))
        ) : (
          <div className="p-5">
            <EmptyState
              description="Generate platform captions before scheduling."
              title="No schedule rows"
            />
          </div>
        )}
      </div>
    </section>
  );
}

function ShortClipScheduleGrid({
  episode,
  isMutating,
  onCancel,
  onEdit,
  onReschedule,
  onSchedule
}: {
  episode: ScheduleEpisodeWorkspace;
  isMutating: boolean;
  onCancel: (row: ScheduleRow) => void;
  onEdit: (row: ScheduleRow) => void;
  onReschedule: (row: ScheduleRow) => void;
  onSchedule: (row: ScheduleRow) => void;
}) {
  if (!episode.short_clip_slots.length) {
    return (
      <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <div className="flex items-center gap-2 text-streamly-violet">
          <Scissors aria-hidden className="h-4 w-4" />
          <p className="text-xs font-extrabold uppercase">Short clip schedule</p>
        </div>
        <div className="mt-5">
          <EmptyState
            description="Add short clip caption rows in Captions before scheduling short-form posts."
            title="No short clip rows"
          />
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2 text-streamly-violet">
        <Scissors aria-hidden className="h-4 w-4" />
        <p className="text-xs font-extrabold uppercase">Short clip schedule</p>
      </div>
      {episode.short_clip_slots.map((slot) => (
        <ShortClipScheduleSlot
          isMutating={isMutating}
          key={slot.clip_suggestion.id}
          onCancel={onCancel}
          onEdit={onEdit}
          onReschedule={onReschedule}
          onSchedule={onSchedule}
          slot={slot}
        />
      ))}
    </section>
  );
}

function ShortClipScheduleSlot({
  isMutating,
  onCancel,
  onEdit,
  onReschedule,
  onSchedule,
  slot
}: {
  isMutating: boolean;
  onCancel: (row: ScheduleRow) => void;
  onEdit: (row: ScheduleRow) => void;
  onReschedule: (row: ScheduleRow) => void;
  onSchedule: (row: ScheduleRow) => void;
  slot: ScheduleShortClipSlot;
}) {
  return (
    <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white shadow-streamly-card">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-streamly-lavenderStrong p-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge label={`clip ${slot.clip_suggestion.slot_number}`} tone="neutral" />
            <StatusBadge
              label={`${slot.scheduled_count} scheduled`}
              tone={slot.scheduled_count ? "scheduled" : "neutral"}
            />
            {slot.failed_count ? (
              <StatusBadge label={`${slot.failed_count} failed`} tone="failed" />
            ) : null}
          </div>
          <h3 className="mt-2 font-streamly-platform text-lg font-extrabold text-streamly-coal">
            {slot.clip_suggestion.title}
          </h3>
          <p className="mt-1 text-sm font-semibold leading-6 text-streamly-purpleBlue">
            {slot.clip_suggestion.start_timecode}-{slot.clip_suggestion.end_timecode} ·{" "}
            {slot.clip_suggestion.rationale}
          </p>
        </div>
      </div>
      <div className="divide-y divide-streamly-lavenderStrong">
        {slot.rows.map((row) => (
          <ScheduleGridRow
            isMutating={isMutating}
            key={row.caption_id}
            onCancel={onCancel}
            onEdit={onEdit}
            onReschedule={onReschedule}
            onSchedule={onSchedule}
            row={row}
            videoLabel="Short clip"
          />
        ))}
      </div>
    </section>
  );
}

function ScheduleGridRow({
  isMutating,
  onCancel,
  onEdit,
  onReschedule,
  onSchedule,
  row,
  videoLabel
}: {
  isMutating: boolean;
  onCancel: (row: ScheduleRow) => void;
  onEdit: (row: ScheduleRow) => void;
  onReschedule: (row: ScheduleRow) => void;
  onSchedule: (row: ScheduleRow) => void;
  row: ScheduleRow;
  videoLabel: string;
}) {
  const schedule = row.schedule;
  const isFailed = schedule?.status === "failed";
  const isPublished = schedule?.status === "published";
  const isCancelled = schedule?.status === "cancelled";
  const isScheduled = schedule?.status === "scheduled";

  return (
    <div className="grid gap-4 p-4 xl:grid-cols-[12rem_minmax(0,1fr)_17rem] xl:items-center">
      <div>
        <div className="flex items-center gap-2">
          <CalendarClock aria-hidden className="h-4 w-4 text-streamly-violet" />
          <p className="font-streamly-platform text-base font-extrabold text-streamly-coal">
            {platformLabel(row.platform)}
          </p>
        </div>
        <p className="mt-1 text-xs font-bold text-[var(--streamly-text-muted)]">
          {videoLabel}
        </p>
      </div>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge
            label={schedule?.status ?? (row.schedule_ready ? "ready" : "locked")}
            tone={schedule?.status ?? (row.schedule_ready ? "ready" : "missing")}
          />
          {schedule ? (
            <StatusBadge label={`Buffer ${schedule.buffer_status}`} tone={schedule.buffer_status} />
          ) : null}
          {schedule?.buffer_post_id ? (
            <StatusBadge label={schedule.buffer_post_id} tone="neutral" />
          ) : null}
        </div>
        {isFailed && schedule.failure_reason ? (
          <div className="mt-3 rounded-streamly-lg border border-red-100 bg-red-50 px-3 py-2 text-sm font-bold text-red-700">
            <div className="flex gap-2">
              <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{schedule.failure_reason}</span>
            </div>
          </div>
        ) : null}
        {schedule?.buffer_post_id ? (
          <p className="mt-2 text-xs font-extrabold uppercase text-[var(--streamly-text-muted)]">
            Buffer ID {schedule.buffer_post_id} · {schedule.buffer_status}
          </p>
        ) : null}
        <p className="mt-2 line-clamp-2 text-sm font-semibold leading-6 text-streamly-purpleBlue">
          {schedule
            ? scheduleSummary(schedule.scheduled_for, schedule.live_url)
            : row.schedule_locked_reason ?? row.caption_text}
        </p>
        {row.video_kind === "short_clip" && row.media_file_name ? (
          <p className="mt-2 text-xs font-extrabold uppercase text-emerald-700">
            Clip media: {row.media_file_name}
          </p>
        ) : null}
        {isPublished && schedule.live_url ? (
          <a
            className="mt-2 inline-flex items-center gap-1 text-sm font-extrabold text-streamly-electric hover:text-streamly-violet"
            href={schedule.live_url}
            rel="noreferrer"
            target="_blank"
          >
            <ExternalLink aria-hidden className="h-4 w-4" />
            Open published post
          </a>
        ) : null}
        {schedule?.channel ? (
          <p className="mt-2 text-xs font-bold text-[var(--streamly-text-muted)]">
            Channel: {schedule.channel.display_name} ({schedule.channel.service})
          </p>
        ) : null}
        {schedule?.rate_limit_reset_at ? (
          <p className="mt-1 text-xs font-bold text-amber-700">
            Rate limit resets {formatDateTime(schedule.rate_limit_reset_at)}.
          </p>
        ) : null}
        {schedule?.next_retry_at ? (
          <p className="mt-1 text-xs font-bold text-amber-700">
            Retry available {formatDateTime(schedule.next_retry_at)}.
          </p>
        ) : null}
        {schedule?.audit_logs.length ? (
          <ScheduleAuditTimeline logs={schedule.audit_logs.slice(0, 3)} />
        ) : null}
      </div>

      <div className="flex flex-wrap justify-start gap-2 xl:justify-end">
        {!row.schedule_ready ? (
          <button
            className="inline-flex cursor-not-allowed items-center gap-2 rounded-streamly-pill bg-streamly-wash px-3 py-2 text-sm font-extrabold text-[var(--streamly-text-muted)]"
            disabled
            type="button"
          >
            <LockKeyhole aria-hidden className="h-4 w-4" />
            Locked
          </button>
        ) : !schedule ? (
          <button
            className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-electric px-3 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isMutating}
            onClick={() => onSchedule(row)}
            type="button"
          >
            <Send aria-hidden className="h-4 w-4" />
            Schedule
          </button>
        ) : (
          <>
            {isScheduled ? (
              <button
                className="inline-flex items-center gap-2 rounded-streamly-pill bg-white px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-wash disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isMutating}
                onClick={() => onEdit(row)}
                type="button"
              >
                <Pencil aria-hidden className="h-4 w-4" />
                Edit
              </button>
            ) : null}
            {(isScheduled || isFailed || isCancelled) && !isPublished ? (
              <button
                className="inline-flex items-center gap-2 rounded-streamly-pill bg-white px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-wash disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isMutating}
                onClick={() => onReschedule(row)}
                type="button"
              >
                <RotateCcw aria-hidden className="h-4 w-4" />
                {isFailed ? "Retry schedule" : "Reschedule"}
              </button>
            ) : null}
            {(isScheduled || isFailed) && !isPublished ? (
              <button
                aria-label="Stop publish"
                className="grid h-9 w-9 place-items-center rounded-streamly-pill bg-white text-red-700 shadow-streamly-card hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isMutating}
                onClick={() => onCancel(row)}
                title="Stop publish"
                type="button"
              >
                <XCircle aria-hidden className="h-4 w-4" />
              </button>
            ) : null}
            {isPublished ? (
              <span className="inline-flex items-center gap-2 rounded-streamly-pill bg-emerald-50 px-3 py-2 text-sm font-extrabold text-emerald-700">
                <CheckCircle2 aria-hidden className="h-4 w-4" />
                Published
              </span>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}

function ScheduleAuditTimeline({ logs }: { logs: PublishingAuditLog[] }) {
  return (
    <div className="mt-3 rounded-streamly-lg border border-streamly-lavenderStrong bg-white/80 px-3 py-2">
      <p className="text-xs font-extrabold uppercase text-streamly-violet">
        Publishing timeline
      </p>
      <div className="mt-2 space-y-2">
        {logs.map((log) => (
          <AuditLine compact key={log.id} log={log} />
        ))}
      </div>
    </div>
  );
}

function AuditLine({ compact = false, log }: { compact?: boolean; log: PublishingAuditLog }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <p className="truncate text-xs font-extrabold text-streamly-coal">
          {log.action.replaceAll(".", " ")}
        </p>
        <p className="mt-0.5 text-xs font-bold text-[var(--streamly-text-muted)]">
          {formatDateTime(log.created_at)}
        </p>
        {!compact && log.error_message ? (
          <p className="mt-1 text-xs font-bold text-red-700">{log.error_message}</p>
        ) : null}
      </div>
      <StatusBadge label={log.status} tone={auditTone(log.status)} />
    </div>
  );
}

function BulkResultBanner({
  result
}: {
  result: {
    requested_count: number;
    scheduled_count: number;
    failed_count: number;
    skipped_count: number;
  };
}) {
  return (
    <div className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white px-4 py-3 shadow-streamly-card">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge label="bulk result" tone="neutral" />
        <StatusBadge label={`${result.scheduled_count} scheduled`} tone="scheduled" />
        <StatusBadge
          label={`${result.failed_count} failed`}
          tone={result.failed_count ? "failed" : "neutral"}
        />
        <StatusBadge label={`${result.skipped_count} skipped`} tone="neutral" />
      </div>
    </div>
  );
}

function eligibleBulkRows(episodes: ScheduleEpisodeWorkspace[]) {
  return episodes
    .flatMap((episode) => [
      ...episode.full_episode_rows,
      ...episode.short_clip_slots.flatMap((slot) => slot.rows)
    ])
    .filter(
      (row) =>
        row.can_create_schedule ||
        row.schedule?.status === "failed" ||
        row.schedule?.status === "cancelled"
    );
}

function auditTone(status: PublishingAuditLog["status"]) {
  if (status === "succeeded") {
    return "ready";
  }
  if (status === "retry_scheduled" || status === "rate_limited") {
    return "scheduled";
  }
  return "failed";
}

function scheduleSummary(scheduledFor: string, liveUrl: string | null) {
  if (liveUrl) {
    return "Published through Buffer with a live post link.";
  }
  return `Scheduled for ${formatDateTime(scheduledFor)}.`;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function platformLabel(platform: string) {
  if (platform === "x") {
    return "X";
  }
  return platform.charAt(0).toUpperCase() + platform.slice(1);
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Unexpected scheduling workflow error.";
}
