import {
  AlertTriangle,
  Activity,
  FileText,
  Image,
  LockKeyhole,
  PlaySquare,
  Scissors,
  UploadCloud
} from "lucide-react";
import { ChangeEvent, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { StageHeaderNextButton } from "@/features/series/StageHeaderNextButton";
import {
  useRecordingWorkspace,
  useRequestClipSuggestions,
  useUploadClipSuggestionVideo,
  useUploadEpisodeThumbnail,
  useUploadEpisodeTranscript,
  useUploadEpisodeVideo
} from "@/features/series/hooks";
import { UploadProgress } from "@/features/series/UploadProgress";
import { env } from "@/shared/config/env";
import type {
  ClipSuggestion,
  MediaAsset,
  MediaProcessingJob,
  RecordingEpisodeWorkspace
} from "@/shared/types/series";

type UploadKind = "video" | "transcript" | "thumbnail" | "clip";

const uploadRules: Record<
  UploadKind,
  { extensions: string[]; maxBytes: number; mimeTypes: string[] }
> = {
  video: {
    extensions: [".mp4", ".mov", ".webm"],
    maxBytes: 500 * 1024 * 1024,
    mimeTypes: ["video/mp4", "video/quicktime", "video/webm"]
  },
  transcript: {
    extensions: [".txt", ".md", ".vtt", ".srt"],
    maxBytes: 10 * 1024 * 1024,
    mimeTypes: ["text/plain", "text/markdown", "text/vtt", "application/x-subrip"]
  },
  thumbnail: {
    extensions: [".jpg", ".jpeg", ".png", ".webp"],
    maxBytes: 10 * 1024 * 1024,
    mimeTypes: ["image/jpeg", "image/png", "image/webp"]
  },
  clip: {
    extensions: [".mp4", ".mov", ".webm"],
    maxBytes: 500 * 1024 * 1024,
    mimeTypes: ["video/mp4", "video/quicktime", "video/webm"]
  }
};

function recordingRequirementMessage(episode: RecordingEpisodeWorkspace) {
  if (episode.recording_complete) {
    return "Full video and transcript are both present.";
  }
  if (!episode.video_file_uploaded && !episode.transcript_uploaded) {
    return "Upload the full video and transcript to complete recording intake.";
  }
  if (!episode.video_file_uploaded) {
    return "Upload the full video to complete recording intake.";
  }
  if (!episode.transcript_uploaded) {
    return "Upload the transcript to complete recording intake.";
  }
  return "Complete full video and transcript before moving to Captions.";
}

function isGeneratedThumbnail(
  thumbnail: RecordingEpisodeWorkspace["selected_thumbnail"]
) {
  return Boolean(thumbnail?.file_path?.includes("/recordings/generated-thumbnails/"));
}

export function RecordingsStagePage({ seriesId }: { seriesId: string }) {
  const workspaceQuery = useRecordingWorkspace(seriesId);
  const uploadVideo = useUploadEpisodeVideo(seriesId);
  const uploadTranscript = useUploadEpisodeTranscript(seriesId);
  const uploadThumbnail = useUploadEpisodeThumbnail(seriesId);
  const uploadClipVideo = useUploadClipSuggestionVideo(seriesId);
  const requestClipSuggestions = useRequestClipSuggestions(seriesId);
  const [activeEpisodeId, setActiveEpisodeId] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

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
    uploadVideo.error,
    uploadTranscript.error,
    uploadThumbnail.error,
    uploadClipVideo.error,
    requestClipSuggestions.error
  ].find(Boolean);
  const isUploadingVideo = uploadVideo.isPending;
  const isUploadingTranscript = uploadTranscript.isPending;
  const isUploadingThumbnail = uploadThumbnail.isPending;
  const isUploadingClip = uploadClipVideo.isPending;
  const isMutating =
    uploadVideo.isPending ||
    uploadTranscript.isPending ||
    uploadThumbnail.isPending ||
    uploadClipVideo.isPending ||
    requestClipSuggestions.isPending;

  useEffect(() => {
    if (!activeEpisodeId && episodes[0]) {
      setActiveEpisodeId(episodes[0].episode_id);
    }
  }, [activeEpisodeId, episodes]);

  if (workspaceQuery.isLoading) {
    return <RecordingsSkeleton />;
  }

  if (workspaceQuery.isError || !workspaceQuery.data) {
    return (
      <ErrorState
        actionLabel="Retry"
        description="The Recordings workspace could not be loaded."
        onAction={() => void workspaceQuery.refetch()}
        title="Recordings unavailable"
      />
    );
  }

  if (!episodes.length) {
    return (
      <EmptyState
        description="Approve a brief pair before preparing media uploads."
        title="No episodes ready for recording"
      />
    );
  }

  async function handleUpload(
    episodeId: string,
    kind: UploadKind,
    event: ChangeEvent<HTMLInputElement>
  ) {
    const file = event.target.files?.[0] ?? null;
    event.target.value = "";
    if (!file) {
      return;
    }

    const validationError = validateFile(file, kind);
    setLocalError(validationError);
    if (validationError) {
      return;
    }

    try {
      if (kind === "video") {
        await uploadVideo.mutateAsync({ episodeId, file });
      } else if (kind === "transcript") {
        await uploadTranscript.mutateAsync({ episodeId, file });
      } else {
        await uploadThumbnail.mutateAsync({ episodeId, file });
      }
    } catch {
      return;
    }
  }

  async function handleClipUpload(
    episodeId: string,
    clipSuggestionId: string,
    event: ChangeEvent<HTMLInputElement>
  ) {
    const file = event.target.files?.[0] ?? null;
    event.target.value = "";
    if (!file) {
      return;
    }

    const validationError = validateFile(file, "clip");
    setLocalError(validationError);
    if (validationError) {
      return;
    }

    try {
      await uploadClipVideo.mutateAsync({ episodeId, clipSuggestionId, file });
    } catch {
      return;
    }
  }

  const readiness = workspaceQuery.data.readiness;
  const completionProgress = `${readiness.complete_episode_count}/${readiness.total_episode_count}`;

  return (
    <main className="space-y-5">
      <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge
                label={readiness.captions_unlocked ? "captions ready" : "recording intake"}
                tone={readiness.captions_unlocked ? "complete" : "planning"}
              />
              <StatusBadge label={`${completionProgress} complete`} tone="neutral" />
            </div>
            <h2 className="mt-3 font-streamly-platform text-2xl font-extrabold text-streamly-coal">
              Recordings
            </h2>
            <p className="mt-2 max-w-3xl font-streamly-body text-sm leading-6 text-streamly-purpleBlue">
              Upload full-episode media, attach transcripts for caption readiness, and request metadata-only clip suggestions.
            </p>
          </div>
          <div className="flex w-full justify-end sm:w-auto">
            <StageHeaderNextButton
              disabled={!readiness.captions_unlocked}
              disabledTitle="Complete video and transcript for at least one episode before moving to Captions."
              nextStage="captions"
              seriesId={seriesId}
            />
          </div>
        </div>
      </section>

      {localError || mutationError ? (
        <ErrorState
          description={localError ?? errorMessage(mutationError)}
          title="Recording action failed"
        />
      ) : null}

      <div className="grid gap-5 2xl:grid-cols-[18rem_minmax(0,1fr)]">
        <EpisodeRecordingSelector
          activeEpisodeId={activeEpisode?.episode_id ?? null}
          episodes={episodes}
          onSelect={(episode) => {
            setActiveEpisodeId(episode.episode_id);
            setLocalError(null);
          }}
        />

        <section className="min-w-0 space-y-4">
          {activeEpisode ? (
            <>
              <RecordingGateBanner episode={activeEpisode} />
              <div className="grid gap-4 xl:grid-cols-2">
                <VideoUploadCard
                  disabled={!activeEpisode.can_upload || isMutating}
                  episode={activeEpisode}
                  isUploading={isUploadingVideo}
                  onUpload={(event) =>
                    void handleUpload(activeEpisode.episode_id, "video", event)
                  }
                />
                <TranscriptUploadCard
                  disabled={!activeEpisode.can_upload || isMutating}
                  episode={activeEpisode}
                  isUploading={isUploadingTranscript}
                  onUpload={(event) =>
                    void handleUpload(activeEpisode.episode_id, "transcript", event)
                  }
                />
              </div>
              <ThumbnailSelector
                disabled={!activeEpisode.can_upload || isMutating}
                episode={activeEpisode}
                isUploading={isUploadingThumbnail}
                onUpload={(event) =>
                  void handleUpload(activeEpisode.episode_id, "thumbnail", event)
                }
              />
              <ClipSuggestionsPanel
                disabled={!activeEpisode.can_upload || isMutating}
                episode={activeEpisode}
                isUploadingClip={isUploadingClip}
                isRequesting={requestClipSuggestions.isPending}
                onClipUpload={(clipSuggestionId, event) =>
                  void handleClipUpload(
                    activeEpisode.episode_id,
                    clipSuggestionId,
                    event
                  )
                }
                onRequest={() => requestClipSuggestions.mutate(activeEpisode.episode_id)}
              />
            </>
          ) : null}
        </section>

      </div>
    </main>
  );
}

function EpisodeRecordingSelector({
  activeEpisodeId,
  episodes,
  onSelect
}: {
  activeEpisodeId: string | null;
  episodes: RecordingEpisodeWorkspace[];
  onSelect: (episode: RecordingEpisodeWorkspace) => void;
}) {
  return (
    <aside className="space-y-2">
      {episodes.map((episode) => {
        const isActive = episode.episode_id === activeEpisodeId;
        const statusLabel = episode.recording_locked
          ? "locked"
          : episode.recording_complete
            ? "complete"
            : !episode.video_file_uploaded && !episode.transcript_uploaded
              ? "media missing"
              : !episode.video_file_uploaded
                ? "needs video"
                : !episode.transcript_uploaded
                  ? "needs transcript"
                  : "incomplete";

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
                tone={episode.recording_complete ? "complete" : "neutral"}
              />
            </div>
            <p className="mt-3 line-clamp-2 text-sm font-extrabold text-streamly-coal">
              {episode.episode_title}
            </p>
            <p className="mt-1 text-xs font-bold text-[var(--streamly-text-muted)]">
              {episode.transcript_uploaded ? "Transcript ready" : "Transcript missing"}
            </p>
          </button>
        );
      })}
    </aside>
  );
}

function RecordingGateBanner({ episode }: { episode: RecordingEpisodeWorkspace }) {
  if (episode.recording_locked) {
    return (
      <div className="rounded-streamly-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-emerald-800">
        <div className="flex gap-2">
          <LockKeyhole aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="text-sm font-extrabold">Recording locked</p>
            <p className="mt-1 text-sm font-medium">
              This episode is frozen for planning edits and ready to feed Captions.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (episode.upload_blockers.length) {
    return (
      <div className="rounded-streamly-xl border border-amber-100 bg-amber-50 px-4 py-3 text-amber-900">
        <div className="flex gap-2">
          <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="text-sm font-extrabold">Recording uploads are blocked</p>
            <p className="mt-1 text-sm font-medium">
              Resolve: {episode.upload_blockers.join(", ")}.
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
            {recordingRequirementMessage(episode)}
          </p>
        </div>
        <StatusBadge
          label={episode.recording_complete ? "complete" : "incomplete"}
          tone={episode.recording_complete ? "complete" : "missing"}
        />
      </div>
    </div>
  );
}

function VideoUploadCard({
  disabled,
  episode,
  isUploading,
  onUpload
}: {
  disabled: boolean;
  episode: RecordingEpisodeWorkspace;
  isUploading: boolean;
  onUpload: (event: ChangeEvent<HTMLInputElement>) => void;
}) {
  const inputId = `video-upload-${episode.episode_id}`;
  const previewUrl = signedMediaUrl(episode.video.media_asset);
  return (
    <section className="flex h-full flex-col rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-streamly-violet">
            <PlaySquare aria-hidden className="h-4 w-4" />
            <p className="text-xs font-extrabold uppercase">Full episode video</p>
          </div>
          <h3 className="mt-2 font-streamly-platform text-lg font-extrabold text-streamly-coal">
            {episode.video.file_name ?? "Video missing"}
          </h3>
          <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
            {episode.video_file_uploaded
              ? `${formatBytes(episode.video.file_size_bytes ?? 0)} uploaded`
              : "MP4, MOV, or WebM up to 500 MB"}
          </p>
        </div>
        <StatusBadge label={episode.video.status} tone={episode.video.status} />
      </div>
      <UploadProgress isActive={isUploading} label="Uploading video" />
      <ProcessingSummary
        failure={episode.video.media_asset?.last_error}
        jobs={episode.video.processing_jobs}
      />
      {previewUrl ? (
        <div className="mt-4 overflow-hidden rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-coal">
          <video className="aspect-video w-full bg-streamly-coal" controls preload="metadata">
            <source src={previewUrl} type={episode.video.content_type ?? undefined} />
          </video>
        </div>
      ) : null}
      <div className="mt-auto pt-4">
        <input
          accept=".mp4,.mov,.webm,video/mp4,video/quicktime,video/webm"
          className="sr-only"
          disabled={disabled}
          id={inputId}
          onChange={onUpload}
          type="file"
        />
        <label
          aria-disabled={disabled}
          className={[
            "inline-flex cursor-pointer items-center gap-2 rounded-streamly-pill px-3 py-2 text-sm font-extrabold shadow-streamly-button",
            disabled
              ? "cursor-not-allowed bg-streamly-wash text-[var(--streamly-text-muted)]"
              : "bg-streamly-electric text-white hover:opacity-95"
          ].join(" ")}
          htmlFor={disabled ? undefined : inputId}
        >
          <UploadCloud aria-hidden className="h-4 w-4" />
          {episode.video_file_uploaded ? "Replace video" : "Upload video"}
        </label>
      </div>
    </section>
  );
}

function TranscriptUploadCard({
  disabled,
  episode,
  isUploading,
  onUpload
}: {
  disabled: boolean;
  episode: RecordingEpisodeWorkspace;
  isUploading: boolean;
  onUpload: (event: ChangeEvent<HTMLInputElement>) => void;
}) {
  const inputId = `transcript-upload-${episode.episode_id}`;
  const transcriptPreview = readMetadataText(episode.transcript?.metadata?.metadata, "text_preview");
  return (
    <section className="flex h-full flex-col rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-streamly-violet">
            <FileText aria-hidden className="h-4 w-4" />
            <p className="text-xs font-extrabold uppercase">Transcript</p>
          </div>
          <h3 className="mt-2 font-streamly-platform text-lg font-extrabold text-streamly-coal">
            {episode.transcript?.file_name ?? "Transcript missing"}
          </h3>
          <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
            {episode.transcript_uploaded
              ? "Captions can consume this transcript."
              : "TXT, Markdown, VTT, or SRT up to 10 MB"}
          </p>
        </div>
        <StatusBadge
          label={episode.transcript?.status ?? "missing"}
          tone={episode.transcript?.status ?? "missing"}
        />
      </div>
      <UploadProgress isActive={isUploading} label="Uploading transcript" />
      <ProcessingSummary
        failure={episode.transcript?.media_asset?.last_error}
        jobs={episode.transcript?.processing_jobs ?? []}
      />
      {transcriptPreview ? (
        <div className="mt-4 rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash p-3">
          <p className="text-xs font-extrabold uppercase text-streamly-electric">
            Parsed preview
          </p>
          <p className="mt-2 line-clamp-6 text-sm font-bold leading-6 text-streamly-purpleBlue">
            {transcriptPreview}
          </p>
        </div>
      ) : null}
      <div className="mt-auto pt-4">
        <input
          accept=".txt,.md,.vtt,.srt,text/plain,text/markdown,text/vtt"
          className="sr-only"
          disabled={disabled}
          id={inputId}
          onChange={onUpload}
          type="file"
        />
        <label
          aria-disabled={disabled}
          className={[
            "inline-flex cursor-pointer items-center gap-2 rounded-streamly-pill px-3 py-2 text-sm font-extrabold shadow-streamly-card",
            disabled
              ? "cursor-not-allowed bg-streamly-wash text-[var(--streamly-text-muted)]"
              : "bg-white text-streamly-purpleBlue hover:bg-streamly-wash"
          ].join(" ")}
          htmlFor={disabled ? undefined : inputId}
        >
          <UploadCloud aria-hidden className="h-4 w-4" />
          {episode.transcript_uploaded ? "Replace transcript" : "Upload transcript"}
        </label>
      </div>
    </section>
  );
}

function ThumbnailSelector({
  disabled,
  episode,
  isUploading,
  onUpload
}: {
  disabled: boolean;
  episode: RecordingEpisodeWorkspace;
  isUploading: boolean;
  onUpload: (event: ChangeEvent<HTMLInputElement>) => void;
}) {
  const inputId = `thumbnail-upload-${episode.episode_id}`;
  const selectedThumbnail = isGeneratedThumbnail(episode.selected_thumbnail)
    ? null
    : episode.selected_thumbnail;
  const selectedThumbnailUrl = signedMediaUrl(selectedThumbnail?.media_asset);
  return (
    <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-streamly-violet">
            <Image aria-hidden className="h-4 w-4" />
            <p className="text-xs font-extrabold uppercase">Thumbnail</p>
          </div>
          <h3 className="mt-2 font-streamly-platform text-lg font-extrabold text-streamly-coal">
            {selectedThumbnail?.file_name ?? "Upload thumbnail"}
          </h3>
          <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
            Upload the production thumbnail artwork for this episode.
          </p>
        </div>
      </div>

      <input
        accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
        className="sr-only"
        disabled={disabled}
        id={inputId}
        onChange={onUpload}
        type="file"
      />
      <label
        aria-disabled={disabled}
        className={[
          "relative mt-4 flex aspect-video w-full overflow-hidden rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash shadow-streamly-card transition",
          disabled
            ? "cursor-not-allowed opacity-70"
            : "cursor-pointer hover:border-streamly-electric hover:bg-white"
        ].join(" ")}
        htmlFor={disabled ? undefined : inputId}
      >
        {selectedThumbnailUrl ? (
          <img
            alt=""
            className="h-full w-full object-cover"
            src={selectedThumbnailUrl}
          />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center gap-3 p-6 text-center">
            <span className="grid h-14 w-14 place-items-center rounded-streamly-pill bg-white text-streamly-electric shadow-streamly-card">
              <Image aria-hidden className="h-6 w-6" />
            </span>
            <div>
              <p className="font-streamly-platform text-lg font-extrabold text-streamly-coal">
                Thumbnail waiting
              </p>
              <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
                Upload a JPG, PNG, or WebP image.
              </p>
            </div>
          </div>
        )}
        <span className="absolute bottom-4 right-4 inline-flex items-center gap-2 rounded-streamly-pill bg-white px-4 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card">
          <UploadCloud aria-hidden className="h-4 w-4" />
          {selectedThumbnail ? "Replace thumbnail" : "Upload thumbnail"}
        </span>
        {selectedThumbnail ? (
          <span className="absolute bottom-4 left-4 max-w-[calc(100%-13rem)] truncate rounded-streamly-pill bg-white px-4 py-2 text-xs font-extrabold text-streamly-purpleBlue shadow-streamly-card">
            {formatBytes(selectedThumbnail.file_size_bytes)}
          </span>
        ) : null}
      </label>
      <UploadProgress isActive={isUploading} label="Uploading thumbnail" />
    </section>
  );
}

function ClipSuggestionsPanel({
  disabled,
  episode,
  isUploadingClip,
  isRequesting,
  onClipUpload,
  onRequest
}: {
  disabled: boolean;
  episode: RecordingEpisodeWorkspace;
  isUploadingClip: boolean;
  isRequesting: boolean;
  onClipUpload: (
    clipSuggestionId: string,
    event: ChangeEvent<HTMLInputElement>
  ) => void;
  onRequest: () => void;
}) {
  const buttonDisabled = disabled || !episode.transcript_uploaded || isRequesting;
  const slots = episode.clip_suggestions.length
    ? episode.clip_suggestions
    : ([1, 2, 3].map((slot) => ({
        id: `empty-${slot}`,
        slot_number: slot
      })) as Array<Partial<ClipSuggestion> & { id: string; slot_number: number }>);

  return (
    <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-streamly-violet">
            <Scissors aria-hidden className="h-4 w-4" />
            <p className="text-xs font-extrabold uppercase">Short clip slots</p>
          </div>
          <h3 className="mt-2 font-streamly-platform text-lg font-extrabold text-streamly-coal">
            Suggested moments
          </h3>
          <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
            Suggestions identify the moment. Clip video uploads are optional and can be added when the edited file is ready.
          </p>
        </div>
        <button
          className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-electric px-3 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-50"
          disabled={buttonDisabled}
          onClick={onRequest}
          type="button"
        >
          <Scissors aria-hidden className="h-4 w-4" />
          {isRequesting
            ? "Requesting..."
            : episode.clip_suggestions.length
              ? "Refresh request"
              : "Request suggestions"}
        </button>
      </div>

      {!episode.transcript_uploaded ? (
        <p className="mt-3 rounded-streamly-md bg-amber-50 px-3 py-2 text-sm font-bold text-amber-900">
          Upload a transcript before requesting clip suggestions.
        </p>
      ) : null}

      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        {slots.map((slot) => (
          <div
            className="flex h-full min-h-[18rem] flex-col rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash p-3"
            key={slot.id}
          >
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs font-extrabold uppercase text-streamly-electric">
                Slot {slot.slot_number}
              </p>
              {slot.status ? <StatusBadge label={slot.status} tone={slot.status} /> : null}
            </div>
            <p className="mt-2 text-sm font-extrabold text-streamly-coal">
              {slot.title ?? "No suggestion yet"}
            </p>
            <p className="mt-2 text-xs font-bold leading-5 text-streamly-purpleBlue">
              {slot.rationale ??
                (episode.transcript_uploaded
                  ? "Request suggestions to create metadata-only clip moments."
                  : "Request suggestions after transcript upload.")}
            </p>
            {slot.start_timecode && slot.end_timecode ? (
              <p className="mt-3 text-xs font-extrabold text-streamly-violet">
                {slot.start_timecode} - {slot.end_timecode}
              </p>
            ) : null}
            {"clip_media_uploaded" in slot && slot.clip_media_uploaded ? (
              <div className="mt-3 rounded-streamly-md bg-emerald-50 px-3 py-2 text-xs font-extrabold text-emerald-700">
                Clip uploaded: {slot.clip_file_name ?? "short clip video"}
              </div>
            ) : null}
            {slot.title && !slot.id.startsWith("empty-") ? (
              <div className="mt-auto pt-4">
                <label
                  className={[
                    "inline-flex cursor-pointer items-center gap-2 rounded-streamly-pill px-3 py-2 text-xs font-extrabold shadow-streamly-card transition",
                    disabled
                      ? "cursor-not-allowed bg-streamly-wash text-[var(--streamly-text-muted)] opacity-60"
                      : "bg-white text-streamly-purpleBlue hover:bg-streamly-lavender"
                  ].join(" ")}
                >
                  <UploadCloud aria-hidden className="h-4 w-4" />
                  {isUploadingClip
                    ? "Uploading..."
                    : slot.clip_media_uploaded
                      ? "Replace clip"
                      : "Upload clip"}
                  <input
                    accept={[...uploadRules.clip.mimeTypes, ...uploadRules.clip.extensions].join(",")}
                    className="sr-only"
                    disabled={disabled || isUploadingClip}
                    onChange={(event) => onClipUpload(slot.id, event)}
                    type="file"
                  />
                </label>
              </div>
            ) : null}
          </div>
        ))}
      </div>
      <UploadProgress isActive={isUploadingClip} label="Uploading short clip" />
    </section>
  );
}

function ProcessingSummary({
  failure,
  jobs
}: {
  failure?: string | null;
  jobs: MediaProcessingJob[];
}) {
  if (!jobs.length && !failure) {
    return null;
  }

  return (
    <div className="mt-4 rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash p-3">
      <div className="flex items-center gap-2 text-streamly-violet">
        <Activity aria-hidden className="h-4 w-4" />
        <p className="text-xs font-extrabold uppercase">Processing</p>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {jobs.map((job) => (
          <StatusBadge
            key={job.id}
            label={`${formatJobType(job.job_type)} ${job.status}`}
            tone={job.status}
          />
        ))}
      </div>
      {failure ? (
        <p className="mt-3 rounded-streamly-md bg-red-50 px-3 py-2 text-sm font-bold text-red-700">
          {failure}
        </p>
      ) : null}
    </div>
  );
}

function RecordingsSkeleton() {
  return (
    <div className="space-y-4">
      <LoadingState label="Loading recordings" />
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="h-48 animate-pulse rounded-streamly-xl bg-streamly-lavender" />
        <div className="h-48 animate-pulse rounded-streamly-xl bg-streamly-lavender" />
      </div>
    </div>
  );
}

function validateFile(file: File, kind: UploadKind) {
  const rule = uploadRules[kind];
  const extension = file.name.includes(".")
    ? `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`
    : "";
  const typeAllowed = file.type ? rule.mimeTypes.includes(file.type) : false;
  const extensionAllowed = rule.extensions.includes(extension);
  if (!typeAllowed && !extensionAllowed) {
    return `Unsupported ${kind} file type. Allowed: ${rule.extensions.join(", ")}.`;
  }
  if (file.size > rule.maxBytes) {
    return `${capitalize(kind)} file exceeds ${formatBytes(rule.maxBytes)}.`;
  }
  if (file.size === 0) {
    return `${capitalize(kind)} file cannot be empty.`;
  }
  return null;
}

function errorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }
  return "The recording action could not be completed.";
}

function formatBytes(bytes: number) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`;
  }
  return `${Math.round((bytes / (1024 * 1024)) * 10) / 10} MB`;
}

function signedMediaUrl(asset: MediaAsset | null | undefined) {
  const signedUrl = asset?.signed_url;
  if (!signedUrl) {
    return null;
  }
  return signedUrl.startsWith("http") ? signedUrl : `${env.apiBaseUrl}${signedUrl}`;
}

function readMetadataText(
  metadata: Record<string, unknown> | null | undefined,
  key: string
) {
  const value = metadata?.[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function formatJobType(value: string) {
  return value.replaceAll("_", " ");
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
