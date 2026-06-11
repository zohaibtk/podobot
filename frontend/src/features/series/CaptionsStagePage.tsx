import {
  LockKeyhole,
  MessageSquareText,
  Pencil,
  Plus,
  RefreshCw,
  Rows3,
  Scissors,
  Sparkles
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { AddPlatformModal } from "@/features/series/AddPlatformModal";
import { CaptionEditorModal } from "@/features/series/CaptionEditorModal";
import { StageHeaderNextButton } from "@/features/series/StageHeaderNextButton";
import {
  useAddCaptionPlatform,
  useCaptionWorkspace,
  useGenerateCaption,
  useRegenerateCaption,
  useUpdateCaption
} from "@/features/series/hooks";
import type {
  CaptionEpisodeWorkspace,
  CaptionPlatform,
  CaptionPlatformCreatePayload,
  CaptionShortClipSlot,
  CaptionUpdatePayload,
  CaptionVideoKind,
  EpisodeVideoPlatformCaption
} from "@/shared/types/series";

type AddPlatformContext = {
  videoKind: CaptionVideoKind;
  availablePlatforms: CaptionPlatform[];
  clipSuggestionId?: string | null;
} | null;

export function CaptionsStagePage({ seriesId }: { seriesId: string }) {
  const workspaceQuery = useCaptionWorkspace(seriesId);
  const addPlatform = useAddCaptionPlatform(seriesId);
  const generateCaption = useGenerateCaption(seriesId);
  const regenerateCaption = useRegenerateCaption(seriesId);
  const updateCaption = useUpdateCaption(seriesId);
  const [activeEpisodeId, setActiveEpisodeId] = useState<string | null>(null);
  const [captionForEdit, setCaptionForEdit] =
    useState<EpisodeVideoPlatformCaption | null>(null);
  const [addContext, setAddContext] = useState<AddPlatformContext>(null);

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
    addPlatform.error,
    generateCaption.error,
    regenerateCaption.error,
    updateCaption.error
  ].find(Boolean);
  const isMutating =
    addPlatform.isPending ||
    generateCaption.isPending ||
    regenerateCaption.isPending ||
    updateCaption.isPending;

  useEffect(() => {
    if (!activeEpisodeId && episodes[0]) {
      setActiveEpisodeId(episodes[0].episode_id);
    }
  }, [activeEpisodeId, episodes]);

  if (workspaceQuery.isLoading) {
    return <CaptionsSkeleton />;
  }

  if (workspaceQuery.isError || !workspaceQuery.data) {
    return (
      <ErrorState
        actionLabel="Retry"
        description="The Captions workspace could not be loaded."
        onAction={() => void workspaceQuery.refetch()}
        title="Captions unavailable"
      />
    );
  }

  if (!episodes.length) {
    return (
      <EmptyState
        description="Upload a transcript in Recordings before preparing platform captions."
        title="No transcript-ready episodes"
      />
    );
  }

  async function addCaptionPlatform(payload: CaptionPlatformCreatePayload) {
    if (!activeEpisode) {
      return;
    }
    await addPlatform.mutateAsync({
      episodeId: activeEpisode.episode_id,
      payload
    });
  }

  async function saveCaption(captionId: string, payload: CaptionUpdatePayload) {
    await updateCaption.mutateAsync({ captionId, payload });
  }

  const readiness = workspaceQuery.data.readiness;
  const completionLabel = `${readiness.ready_caption_count}/${readiness.total_caption_count}`;

  return (
    <main className="space-y-5">
      <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge
                label={
                  readiness.scheduling_unlocked ? "scheduling unlocked" : "captioning"
                }
                tone={readiness.scheduling_unlocked ? "complete" : "captioning"}
              />
              <StatusBadge label={`${completionLabel} ready`} tone="neutral" />
            </div>
            <h2 className="mt-3 font-streamly-platform text-2xl font-extrabold text-streamly-coal">
              Captions
            </h2>
            <p className="mt-2 max-w-3xl font-streamly-body text-sm leading-6 text-streamly-purpleBlue">
              Generate and curate platform-specific copy from the transcript, then unlock only ready rows for Scheduling.
            </p>
          </div>
          <div className="flex w-full justify-end sm:w-auto">
            <StageHeaderNextButton
              disabled={!readiness.scheduling_unlocked}
              disabledTitle="Prepare at least one ready caption before moving to Schedule."
              nextStage="schedule"
              seriesId={seriesId}
            />
          </div>
        </div>
      </section>

      {mutationError ? (
        <ErrorState description={errorMessage(mutationError)} title="Caption action failed" />
      ) : null}

      <div className="grid gap-5 xl:grid-cols-[18rem_minmax(0,1fr)]">
        <EpisodeCaptionSelector
          activeEpisodeId={activeEpisode?.episode_id ?? null}
          episodes={episodes}
          onSelect={(episode) => setActiveEpisodeId(episode.episode_id)}
        />

        <section className="min-w-0 space-y-4">
          {activeEpisode ? (
            <>
              <CaptionGateBanner episode={activeEpisode} />
              <PlatformCaptionGrid
                availablePlatforms={activeEpisode.full_available_platforms}
                captions={activeEpisode.full_episode_captions}
                isMutating={isMutating}
                onAddPlatform={() =>
                  setAddContext({
                    videoKind: "full_episode",
                    availablePlatforms: activeEpisode.full_available_platforms
                  })
                }
                onEdit={setCaptionForEdit}
                onGenerate={(caption) => generateCaption.mutate(caption.id)}
                onRegenerate={(caption) => regenerateCaption.mutate(caption.id)}
                title="Full episode platforms"
                videoKind="full_episode"
              />
              <ShortClipGrid
                episode={activeEpisode}
                isMutating={isMutating}
                onAddPlatform={(slot) =>
                  setAddContext({
                    videoKind: "short_clip",
                    availablePlatforms: slot.available_platforms,
                    clipSuggestionId: slot.clip_suggestion.id
                  })
                }
                onEdit={setCaptionForEdit}
                onGenerate={(caption) => generateCaption.mutate(caption.id)}
                onRegenerate={(caption) => regenerateCaption.mutate(caption.id)}
                seriesId={seriesId}
              />
            </>
          ) : null}
        </section>
      </div>

      <AddPlatformModal
        availablePlatforms={addContext?.availablePlatforms ?? []}
        clipSuggestionId={addContext?.clipSuggestionId ?? null}
        isOpen={addContext !== null}
        isSubmitting={addPlatform.isPending}
        onClose={() => setAddContext(null)}
        onSubmit={addCaptionPlatform}
        videoKind={addContext?.videoKind ?? "full_episode"}
      />

      <CaptionEditorModal
        caption={captionForEdit}
        isMutating={isMutating}
        isOpen={captionForEdit !== null}
        onClose={() => setCaptionForEdit(null)}
        onRegenerate={(captionId) => regenerateCaption.mutateAsync(captionId)}
        onSave={saveCaption}
      />
    </main>
  );
}

function EpisodeCaptionSelector({
  activeEpisodeId,
  episodes,
  onSelect
}: {
  activeEpisodeId: string | null;
  episodes: CaptionEpisodeWorkspace[];
  onSelect: (episode: CaptionEpisodeWorkspace) => void;
}) {
  return (
    <aside className="space-y-2">
      {episodes.map((episode) => {
        const isActive = episode.episode_id === activeEpisodeId;
        const statusLabel = episode.caption_blockers.length
          ? "locked"
          : episode.ready_caption_count
            ? `${episode.ready_caption_count} ready`
            : "not started";

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
                tone={
                  episode.caption_blockers.length
                    ? "missing"
                    : episode.ready_caption_count
                      ? "ready"
                      : "neutral"
                }
              />
            </div>
            <p className="mt-3 line-clamp-2 text-sm font-extrabold text-streamly-coal">
              {episode.episode_title}
            </p>
            <p className="mt-1 text-xs font-bold text-[var(--streamly-text-muted)]">
              {episode.transcript_ready ? "Transcript ready" : "Transcript missing"}
            </p>
          </button>
        );
      })}
    </aside>
  );
}

function CaptionGateBanner({ episode }: { episode: CaptionEpisodeWorkspace }) {
  if (episode.caption_blockers.length) {
    return (
      <div className="rounded-streamly-xl border border-amber-100 bg-amber-50 px-4 py-3 text-amber-900">
        <div className="flex gap-2">
          <LockKeyhole aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="text-sm font-extrabold">Captioning is locked for this episode</p>
            <p className="mt-1 text-sm font-medium">
              Resolve: {episode.caption_blockers.join(", ")}.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white px-4 py-3 shadow-streamly-card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-extrabold text-streamly-coal">
            Episode {episode.episode_number}: {episode.episode_title}
          </p>
          <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
            Transcript is ready. Generate any platform row to make it schedulable.
          </p>
        </div>
        <StatusBadge label={episode.video_status} tone={episode.video_status} />
      </div>
    </div>
  );
}

function PlatformCaptionGrid({
  availablePlatforms,
  captions,
  isMutating,
  onAddPlatform,
  onEdit,
  onGenerate,
  onRegenerate,
  title,
  videoKind
}: {
  availablePlatforms: CaptionPlatform[];
  captions: EpisodeVideoPlatformCaption[];
  isMutating: boolean;
  onAddPlatform: () => void;
  onEdit: (caption: EpisodeVideoPlatformCaption) => void;
  onGenerate: (caption: EpisodeVideoPlatformCaption) => void;
  onRegenerate: (caption: EpisodeVideoPlatformCaption) => void;
  title: string;
  videoKind: CaptionVideoKind;
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
            {videoKind === "full_episode"
              ? "LinkedIn, Facebook, and YouTube rows are managed for the full upload."
              : "Short clip rows are added per clip suggestion."}
          </p>
        </div>
        {availablePlatforms.length ? (
          <button
            className="inline-flex items-center gap-2 rounded-streamly-pill bg-white px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-wash disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isMutating}
            onClick={onAddPlatform}
            type="button"
          >
            <Plus aria-hidden className="h-4 w-4" />
            Add platform
          </button>
        ) : null}
      </div>
      <div className="divide-y divide-streamly-lavenderStrong">
        {captions.length ? (
          captions.map((caption) => (
            <CaptionRow
              caption={caption}
              isMutating={isMutating}
              key={caption.id}
              onEdit={onEdit}
              onGenerate={onGenerate}
              onRegenerate={onRegenerate}
            />
          ))
        ) : (
          <div className="p-5">
            <EmptyState
              description="Add a valid platform row to start caption generation."
              title="No platform rows yet"
            />
          </div>
        )}
      </div>
    </section>
  );
}

function ShortClipGrid({
  episode,
  isMutating,
  onAddPlatform,
  onEdit,
  onGenerate,
  onRegenerate,
  seriesId
}: {
  episode: CaptionEpisodeWorkspace;
  isMutating: boolean;
  onAddPlatform: (slot: CaptionShortClipSlot) => void;
  onEdit: (caption: EpisodeVideoPlatformCaption) => void;
  onGenerate: (caption: EpisodeVideoPlatformCaption) => void;
  onRegenerate: (caption: EpisodeVideoPlatformCaption) => void;
  seriesId: string;
}) {
  if (!episode.short_clip_slots.length) {
    return (
      <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <div className="flex items-center gap-2 text-streamly-violet">
          <Scissors aria-hidden className="h-4 w-4" />
          <p className="text-xs font-extrabold uppercase">Short clip platforms</p>
        </div>
        <div className="mt-5">
          <EmptyState
            description="Request clip suggestions in Recordings, then return here to add short clip platform rows."
            title="No short clip slots yet"
          />
          <Link
            className="mt-4 inline-flex items-center gap-2 rounded-streamly-pill bg-white px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-wash"
            to={`/series/${seriesId}/recordings`}
          >
            <Scissors aria-hidden className="h-4 w-4" />
            Review clip suggestions
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2 text-streamly-violet">
        <Scissors aria-hidden className="h-4 w-4" />
        <p className="text-xs font-extrabold uppercase">Short clip platforms</p>
      </div>
      {episode.short_clip_slots.map((slot) => (
        <section
          className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white shadow-streamly-card"
          key={slot.clip_suggestion.id}
        >
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-streamly-lavenderStrong p-4">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge label={`clip ${slot.clip_suggestion.slot_number}`} tone="neutral" />
                <StatusBadge
                  label={`${slot.complete_caption_count} ready`}
                  tone={slot.complete_caption_count ? "ready" : "neutral"}
                />
              </div>
              <h3 className="mt-2 font-streamly-platform text-lg font-extrabold text-streamly-coal">
                {slot.clip_suggestion.title}
              </h3>
              <p className="mt-1 text-sm font-semibold leading-6 text-streamly-purpleBlue">
                {slot.clip_suggestion.start_timecode}-{slot.clip_suggestion.end_timecode} ·{" "}
                {slot.clip_suggestion.rationale}
              </p>
            </div>
            {slot.available_platforms.length ? (
              <button
                className="inline-flex items-center gap-2 rounded-streamly-pill bg-white px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-wash disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isMutating}
                onClick={() => onAddPlatform(slot)}
                type="button"
              >
                <Plus aria-hidden className="h-4 w-4" />
                Add platform
              </button>
            ) : null}
          </div>
          <div className="divide-y divide-streamly-lavenderStrong">
            {slot.captions.length ? (
              slot.captions.map((caption) => (
                <CaptionRow
                  caption={caption}
                  isMutating={isMutating}
                  key={caption.id}
                  onEdit={onEdit}
                  onGenerate={onGenerate}
                  onRegenerate={onRegenerate}
                />
              ))
            ) : (
              <div className="p-4 text-sm font-bold text-[var(--streamly-text-muted)]">
                Add a platform row for this clip before generation.
              </div>
            )}
          </div>
        </section>
      ))}
    </section>
  );
}

function CaptionRow({
  caption,
  isMutating,
  onEdit,
  onGenerate,
  onRegenerate
}: {
  caption: EpisodeVideoPlatformCaption;
  isMutating: boolean;
  onEdit: (caption: EpisodeVideoPlatformCaption) => void;
  onGenerate: (caption: EpisodeVideoPlatformCaption) => void;
  onRegenerate: (caption: EpisodeVideoPlatformCaption) => void;
}) {
  return (
    <div className="grid gap-4 p-4 lg:grid-cols-[12rem_minmax(0,1fr)_15rem] lg:items-center">
      <div>
        <div className="flex items-center gap-2">
          <MessageSquareText aria-hidden className="h-4 w-4 text-streamly-violet" />
          <p className="font-streamly-platform text-base font-extrabold text-streamly-coal">
            {platformLabel(caption.platform)}
          </p>
        </div>
        <p className="mt-1 text-xs font-bold text-[var(--streamly-text-muted)]">
          {caption.video_kind === "full_episode" ? "Full episode" : "Short clip"} · v
          {caption.generation_count}
        </p>
      </div>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge label={caption.status} tone={caption.status} />
          <StatusBadge
            label={caption.can_schedule ? "schedulable" : "schedule locked"}
            tone={caption.can_schedule ? "ready" : "missing"}
          />
        </div>
        <p className="mt-2 line-clamp-2 text-sm font-semibold leading-6 text-streamly-purpleBlue">
          {caption.caption_text ??
            caption.scheduling_locked_reason ??
            "Generate platform copy from the transcript."}
        </p>
      </div>

      <div className="flex flex-wrap justify-start gap-2 lg:justify-end">
        {caption.status === "not_started" ? (
          <button
            className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-electric px-3 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isMutating}
            onClick={() => onGenerate(caption)}
            type="button"
          >
            <Sparkles aria-hidden className="h-4 w-4" />
            Generate
          </button>
        ) : (
          <button
            className="grid h-9 w-9 place-items-center rounded-streamly-pill bg-white text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-wash disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isMutating}
            onClick={() => onRegenerate(caption)}
            title="Regenerate caption"
            type="button"
          >
            <RefreshCw aria-hidden className="h-4 w-4" />
          </button>
        )}
        <button
          className="inline-flex items-center gap-2 rounded-streamly-pill bg-white px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-wash disabled:cursor-not-allowed disabled:opacity-50"
          disabled={isMutating}
          onClick={() => onEdit(caption)}
          type="button"
        >
          <Pencil aria-hidden className="h-4 w-4" />
          Edit
        </button>
      </div>
    </div>
  );
}

function CaptionsSkeleton() {
  return <LoadingState label="Loading captions workspace" />;
}

function platformLabel(platform: CaptionPlatform) {
  if (platform === "x") {
    return "X";
  }
  return platform.charAt(0).toUpperCase() + platform.slice(1);
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Unexpected caption workflow error.";
}
