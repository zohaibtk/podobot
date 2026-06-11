import {
  AlertTriangle,
  CheckCircle2,
  FileCheck2,
  RefreshCw,
  Sparkles
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { ApproveBriefPairModal } from "@/features/series/ApproveBriefPairModal";
import { BriefEditorPanel } from "@/features/series/BriefEditorPanel";
import { StageHeaderNextButton } from "@/features/series/StageHeaderNextButton";
import {
  useApproveBriefPair,
  useBriefWorkspace,
  useDownloadBrief,
  useGenerateBriefPair,
  useRegenerateBrief,
  useUpdateBrief
} from "@/features/series/hooks";
import type {
  BriefEpisodeWorkspace,
  BriefUpdatePayload
} from "@/shared/types/series";

export function BriefsStagePage({ seriesId }: { seriesId: string }) {
  const workspaceQuery = useBriefWorkspace(seriesId);
  const generateBriefPair = useGenerateBriefPair(seriesId);
  const updateBrief = useUpdateBrief(seriesId);
  const regenerateBrief = useRegenerateBrief(seriesId);
  const approveBriefPair = useApproveBriefPair(seriesId);
  const downloadBrief = useDownloadBrief(seriesId);
  const [activeEpisodeId, setActiveEpisodeId] = useState<string | null>(null);
  const [episodeForApproval, setEpisodeForApproval] = useState<BriefEpisodeWorkspace | null>(null);

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
  const mutationError = [
    generateBriefPair.error,
    updateBrief.error,
    regenerateBrief.error,
    approveBriefPair.error,
    downloadBrief.error
  ].find(Boolean);
  const isMutating =
    generateBriefPair.isPending ||
    updateBrief.isPending ||
    regenerateBrief.isPending ||
    approveBriefPair.isPending ||
    downloadBrief.isPending;

  useEffect(() => {
    if (!activeEpisodeId && episodes[0]) {
      setActiveEpisodeId(episodes[0].episode_id);
    }
  }, [activeEpisodeId, episodes]);

  if (workspaceQuery.isLoading) {
    return <BriefsSkeleton />;
  }

  if (workspaceQuery.isError || !workspaceQuery.data) {
    return (
      <ErrorState
        actionLabel="Retry"
        description="The Briefs workspace could not be loaded."
        onAction={() => void workspaceQuery.refetch()}
        title="Briefs unavailable"
      />
    );
  }

  if (!episodes.length) {
    return (
      <EmptyState
        description="Lock an episode plan before generating host and guest briefs."
        title="No episodes ready for briefs"
      />
    );
  }

  async function saveBrief(briefId: string, payload: BriefUpdatePayload) {
    await updateBrief.mutateAsync({ briefId, payload });
  }

  async function downloadCurrentBrief(briefId: string) {
    const result = await downloadBrief.mutateAsync(briefId);
    const url = window.URL.createObjectURL(result.blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = result.filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  async function approveCurrentPair() {
    if (!episodeForApproval) {
      return;
    }
    await approveBriefPair.mutateAsync(episodeForApproval.episode_id);
    setEpisodeForApproval(null);
  }

  const readiness = workspaceQuery.data.readiness;
  const approvalProgress = `${readiness.approved_episode_count}/${readiness.total_episode_count}`;

  return (
    <main className="space-y-5">
      <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge
                label={readiness.recordings_unlocked ? "recordings unlocked" : "brief review"}
                tone={readiness.recordings_unlocked ? "complete" : "planning"}
              />
              <StatusBadge label={`${approvalProgress} approved`} tone="neutral" />
            </div>
            <h2 className="mt-3 font-streamly-platform text-2xl font-extrabold text-streamly-coal">
              Brief generation
            </h2>
            <p className="mt-2 max-w-3xl font-streamly-body text-sm leading-6 text-streamly-purpleBlue">
              Generate, edit, and approve separate host and guest documents from the latest approved outline context.
            </p>
          </div>
          <div className="flex w-full justify-end sm:w-auto">
            <StageHeaderNextButton
              disabled={!readiness.recordings_unlocked}
              disabledTitle="Approve at least one brief pair before moving to Recordings."
              nextStage="recordings"
              seriesId={seriesId}
            />
          </div>
        </div>
      </section>

      {mutationError ? (
        <ErrorState description={errorMessage(mutationError)} title="Brief action failed" />
      ) : null}

      <div className="grid gap-5 2xl:grid-cols-[22rem_minmax(0,1fr)]">
        <EpisodeBriefSelector
          activeEpisodeId={activeEpisode?.episode_id ?? null}
          episodes={episodes}
          onSelect={(episode) => setActiveEpisodeId(episode.episode_id)}
        />

        <section className="min-w-0 space-y-4">
          {activeEpisode ? (
            <>
              <RequirementsGuard episode={activeEpisode} seriesId={seriesId} />

              {!activeEpisode.pair_generated ? (
                <GeneratePairPanel
                  canGenerate={activeEpisode.requirement.can_generate}
                  episode={activeEpisode}
                  isSubmitting={generateBriefPair.isPending}
                  onGenerate={() => void generateBriefPair.mutateAsync(activeEpisode.episode_id)}
                />
              ) : null}

              {activeEpisode.pair_generated ? (
                <PairApprovalBar
                  episode={activeEpisode}
                  isMutating={isMutating}
                  onApprove={() => setEpisodeForApproval(activeEpisode)}
                />
              ) : null}

              <div className="grid gap-4 xl:grid-cols-2">
                <BriefEditorPanel
                  brief={activeEpisode.host_brief}
                  isMutating={isMutating}
                  isPairApproved={activeEpisode.pair_approved}
                  kind="host"
                  onDownload={downloadCurrentBrief}
                  onSave={saveBrief}
                />
                <BriefEditorPanel
                  brief={activeEpisode.guest_brief}
                  isMutating={isMutating}
                  isPairApproved={activeEpisode.pair_approved}
                  kind="guest"
                  onDownload={downloadCurrentBrief}
                  onSave={saveBrief}
                />
              </div>
            </>
          ) : null}
        </section>
      </div>

      <ApproveBriefPairModal
        episode={episodeForApproval}
        isOpen={episodeForApproval !== null}
        isSubmitting={approveBriefPair.isPending}
        onClose={() => setEpisodeForApproval(null)}
        onConfirm={() => void approveCurrentPair()}
      />
    </main>
  );
}

function EpisodeBriefSelector({
  activeEpisodeId,
  episodes,
  onSelect
}: {
  activeEpisodeId: string | null;
  episodes: BriefEpisodeWorkspace[];
  onSelect: (episode: BriefEpisodeWorkspace) => void;
}) {
  return (
    <aside className="space-y-2">
      {episodes.map((episode) => {
        const isActive = episode.episode_id === activeEpisodeId;
        const statusLabel = episode.pair_approved
          ? "approved"
          : episode.pair_generated
            ? "review"
            : "not generated";

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
                tone={episode.pair_approved ? "approved" : "neutral"}
              />
            </div>
            <p className="mt-3 line-clamp-2 text-sm font-extrabold text-streamly-coal">
              {episode.episode_title}
            </p>
            <p className="mt-1 text-xs font-bold text-[var(--streamly-text-muted)]">
              {episode.requirement.host_profile_name ?? "Host missing"} ·{" "}
              {episode.requirement.guest_profile_name ?? "Guest missing"}
            </p>
          </button>
        );
      })}
    </aside>
  );
}

function RequirementsGuard({
  episode,
  seriesId
}: {
  episode: BriefEpisodeWorkspace;
  seriesId: string;
}) {
  const missing = episode.requirement.missing_requirements;
  if (!missing.length) {
    return (
      <div className="rounded-streamly-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-emerald-800">
        <div className="flex gap-2">
          <CheckCircle2 aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
          <p className="text-sm font-bold leading-6">
            Host, guest, and latest approved outline context are ready for this episode.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-streamly-xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
      <div className="flex gap-3">
        <AlertTriangle aria-hidden className="mt-0.5 h-5 w-5 shrink-0" />
        <div>
          <h3 className="font-streamly-platform text-sm font-extrabold">
            Brief generation is blocked
          </h3>
          <p className="mt-1 text-sm font-semibold leading-6">
            Missing {missing.join(", ")} for episode {episode.episode_number}.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {missing.some((item) => item.includes("profile")) ? (
              <Link
                className="rounded-streamly-pill bg-white px-3 py-2 text-xs font-extrabold text-amber-900 shadow-streamly-card"
                to={`/series/${seriesId}/plan`}
              >
                Review assignments
              </Link>
            ) : null}
            {missing.some((item) => item.includes("outline")) ? (
              <Link
                className="rounded-streamly-pill bg-white px-3 py-2 text-xs font-extrabold text-amber-900 shadow-streamly-card"
                to={`/series/${seriesId}/outlines`}
              >
                Review outline
              </Link>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

function GeneratePairPanel({
  canGenerate,
  episode,
  isSubmitting,
  onGenerate
}: {
  canGenerate: boolean;
  episode: BriefEpisodeWorkspace;
  isSubmitting: boolean;
  onGenerate: () => void;
}) {
  return (
    <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-streamly-violet">
            <Sparkles aria-hidden className="h-4 w-4" />
            <p className="text-xs font-extrabold uppercase">Explicit generation</p>
          </div>
          <h3 className="mt-3 font-streamly-platform text-lg font-extrabold text-streamly-coal">
            Generate host and guest briefs
          </h3>
          <p className="mt-2 max-w-2xl text-sm font-semibold leading-6 text-streamly-purpleBlue">
            Episode {episode.episode_number} will receive two separate documents using the latest
            approved outline version and assigned profile voices.
          </p>
        </div>
        <button
          className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-electric px-4 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!canGenerate || isSubmitting}
          onClick={onGenerate}
          type="button"
        >
          <RefreshCw aria-hidden className="h-4 w-4" />
          {isSubmitting ? "Generating..." : "Generate pair"}
        </button>
      </div>
    </section>
  );
}

function PairApprovalBar({
  episode,
  isMutating,
  onApprove
}: {
  episode: BriefEpisodeWorkspace;
  isMutating: boolean;
  onApprove: () => void;
}) {
  const canApprove = episode.pair_generated && !episode.pair_approved;
  const title = episode.pair_approved
    ? "Pair approved"
    : episode.approval_invalidated_at
      ? "Approval invalidated"
      : "Awaiting pair approval";
  const description = episode.pair_approved
    ? "Recordings are unlocked for this series."
    : episode.approval_invalidated_at
      ? "Review the latest brief versions, then approve the pair again."
      : "Approve only after both host and guest briefs are final.";

  return (
    <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white px-4 py-3 shadow-streamly-card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric">
            <FileCheck2 aria-hidden className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-extrabold text-streamly-coal">{title}</p>
              <StatusBadge
                label={episode.pair_approved ? "approved" : "review"}
                tone={episode.pair_approved ? "approved" : "neutral"}
              />
            </div>
            <p className="mt-1 text-xs font-bold leading-5 text-streamly-purpleBlue">
              {description}
            </p>
          </div>
        </div>
        <button
          className="inline-flex items-center justify-center gap-2 rounded-streamly-pill bg-streamly-coal px-4 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!canApprove || isMutating}
          onClick={onApprove}
          type="button"
        >
          <CheckCircle2 aria-hidden className="h-4 w-4" />
          Approve pair
        </button>
      </div>
    </section>
  );
}

function BriefsSkeleton() {
  return (
    <main className="space-y-4">
      <LoadingState label="Loading briefs" />
      <div className="grid gap-4 xl:grid-cols-2">
        {[0, 1].map((item) => (
          <div
            className="min-h-[32rem] rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card"
            key={item}
          >
            <div className="h-5 w-32 animate-pulse rounded-streamly-pill bg-streamly-lavender" />
            <div className="mt-5 h-8 w-2/3 animate-pulse rounded-streamly-md bg-streamly-wash" />
            <div className="mt-6 space-y-3">
              <div className="h-4 animate-pulse rounded-streamly-pill bg-streamly-wash" />
              <div className="h-4 w-5/6 animate-pulse rounded-streamly-pill bg-streamly-wash" />
              <div className="h-4 w-2/3 animate-pulse rounded-streamly-pill bg-streamly-wash" />
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "The brief request could not be completed.";
}
