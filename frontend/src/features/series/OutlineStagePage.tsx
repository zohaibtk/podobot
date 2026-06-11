import {
  CheckCircle2,
  Clock3,
  Keyboard,
  LockKeyhole,
  RefreshCw,
  Save
} from "lucide-react";
import type { KeyboardEvent } from "react";
import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { MarkdownPreview } from "@/features/series/MarkdownPreview";
import { RegenerateOutlineModal } from "@/features/series/RegenerateOutlineModal";
import { StageHeaderNextButton } from "@/features/series/StageHeaderNextButton";
import {
  useApproveOutline,
  useOutlineWorkspace,
  useRegenerateOutline,
  useUpdateOutline
} from "@/features/series/hooks";
import type { EpisodeOutline } from "@/shared/types/series";

type ViewMode = "split" | "preview";
type SaveState = "saved" | "dirty" | "saving";

export function OutlineStagePage({ seriesId }: { seriesId: string }) {
  const workspaceQuery = useOutlineWorkspace(seriesId);
  const updateOutline = useUpdateOutline(seriesId);
  const regenerateOutline = useRegenerateOutline(seriesId);
  const approveOutline = useApproveOutline(seriesId);
  const [activeOutlineId, setActiveOutlineId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [draftMarkdown, setDraftMarkdown] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("preview");
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [regeneratingOutline, setRegeneratingOutline] = useState<EpisodeOutline | null>(null);

  const outlines = useMemo(
    () => workspaceQuery.data?.outlines ?? [],
    [workspaceQuery.data?.outlines]
  );
  const activeOutline = useMemo(
    () => outlines.find((outline) => outline.id === activeOutlineId) ?? outlines[0] ?? null,
    [activeOutlineId, outlines]
  );
  const isActiveOutlineApproved = activeOutline?.status === "approved";
  const activeOutlineCanEdit = Boolean(activeOutline?.can_edit && !isActiveOutlineApproved);
  const activeOutlineReadOnlyReason = isActiveOutlineApproved
    ? "This outline is approved and read-only. Regenerate it to create a new editable version."
    : activeOutline?.read_only_reason;
  const mutationError = [
    updateOutline.error,
    regenerateOutline.error,
    approveOutline.error
  ].find(Boolean);
  const isMutating =
    updateOutline.isPending || regenerateOutline.isPending || approveOutline.isPending;
  const hasChanges = Boolean(
    activeOutline &&
      (draftTitle !== activeOutline.title || draftMarkdown !== activeOutline.outline_markdown)
  );

  useEffect(() => {
    if (!activeOutlineId && outlines[0]) {
      setActiveOutlineId(outlines[0].id);
    }
  }, [activeOutlineId, outlines]);

  useEffect(() => {
    if (!activeOutline) {
      return;
    }
    setDraftTitle(activeOutline.title);
    setDraftMarkdown(activeOutline.outline_markdown);
    setSaveState("saved");
  }, [activeOutline, activeOutline?.id, activeOutline?.current_version_id]);

  useEffect(() => {
    setViewMode("preview");
  }, [activeOutline?.id]);

  useEffect(() => {
    if (!activeOutline || updateOutline.isPending) {
      return;
    }
    setSaveState(hasChanges ? "dirty" : "saved");
  }, [activeOutline, draftMarkdown, draftTitle, hasChanges, updateOutline.isPending]);

  if (workspaceQuery.isLoading) {
    return <LoadingState label="Loading outlines" />;
  }

  if (workspaceQuery.isError || !workspaceQuery.data) {
    return (
      <ErrorState
        actionLabel="Retry"
        description="The outline workspace could not be loaded."
        onAction={() => void workspaceQuery.refetch()}
        title="Outlines unavailable"
      />
    );
  }

  if (!outlines.length) {
    return (
      <EmptyState
        description="Lock the episode plan to generate profile-agnostic outlines for every episode."
        title="No outlines generated"
      />
    );
  }

  async function saveCurrentOutline() {
    if (!activeOutline || !activeOutlineCanEdit || !draftMarkdown.trim()) {
      return;
    }
    setSaveState("saving");
    await updateOutline.mutateAsync({
      outlineId: activeOutline.id,
      payload: {
        title: draftTitle.trim() || activeOutline.title,
        outline_markdown: draftMarkdown
      }
    });
    setSaveState("saved");
  }

  async function approveCurrentOutline() {
    if (!activeOutline || !activeOutlineCanEdit || hasChanges) {
      return;
    }
    await approveOutline.mutateAsync(activeOutline.id);
  }

  async function regenerateCurrentOutline(instruction: string) {
    if (!regeneratingOutline) {
      return;
    }
    await regenerateOutline.mutateAsync({
      outlineId: regeneratingOutline.id,
      payload: { instruction: instruction.trim() || null }
    });
    setRegeneratingOutline(null);
  }

  function handleEditorShortcut(event: KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      if (hasChanges && !isMutating) {
        void saveCurrentOutline();
      }
    }
  }

  const approvedOutlineCount = workspaceQuery.data.readiness.approved_outline_count;
  const approvalProgress = `${approvedOutlineCount}/${workspaceQuery.data.readiness.total_outline_count}`;
  const canContinueToBriefs = approvedOutlineCount > 0;

  return (
    <main className="space-y-5">
      <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge
                label={workspaceQuery.data.readiness.is_ready_for_briefs ? "brief ready" : "outline review"}
                tone={workspaceQuery.data.readiness.is_ready_for_briefs ? "complete" : "planning"}
              />
              <StatusBadge label={`${approvalProgress} approved`} tone="neutral" />
            </div>
            <h2 className="mt-3 font-streamly-platform text-2xl font-extrabold text-streamly-coal">
              Episode outlines
            </h2>
            <p className="mt-2 max-w-3xl font-streamly-body text-sm leading-6 text-streamly-purpleBlue">
              Edit the latest profile-agnostic outline for each episode before the Brief stage consumes it.
            </p>
          </div>
          <StageHeaderNextButton
            disabled={!canContinueToBriefs}
            disabledTitle="Approve at least one outline before moving to Briefs."
            nextStage="briefs"
            seriesId={seriesId}
          />
        </div>
      </section>

      {mutationError ? (
        <ErrorState
          description={errorMessage(mutationError)}
          title="Outline action failed"
        />
      ) : null}

      <div className="grid gap-5 2xl:grid-cols-[24rem_minmax(0,1fr)]">
        <OutlineSelector
          activeOutlineId={activeOutline?.id ?? null}
          outlines={outlines}
          onSelect={(outline) => setActiveOutlineId(outline.id)}
        />

        <section className="min-w-0 rounded-streamly-xl border border-streamly-lavenderStrong bg-white shadow-streamly-card">
          {activeOutline ? (
            <>
              <div className="border-b border-streamly-lavenderStrong p-4">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge label={activeOutline.status} tone={activeOutline.status} />
                      <SaveIndicator state={saveState} />
                      {!activeOutlineCanEdit ? (
                        <span className="inline-flex items-center gap-1 rounded-streamly-pill bg-red-50 px-2.5 py-1 text-xs font-extrabold text-red-700">
                          <LockKeyhole aria-hidden className="h-3.5 w-3.5" />
                          Read-only
                        </span>
                      ) : null}
                    </div>
                    <input
                      className="mt-3 w-full rounded-streamly-md border border-transparent bg-transparent px-0 py-1 font-streamly-platform text-2xl font-extrabold text-streamly-coal outline-none focus:border-streamly-lavenderStrong focus:bg-streamly-wash focus:px-3 disabled:cursor-not-allowed"
                      disabled={!activeOutlineCanEdit || isMutating}
                      onChange={(event) => setDraftTitle(event.target.value)}
                      value={draftTitle}
                    />
                    <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
                      Episode {activeOutline.episode_number}: {activeOutline.episode_title}
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <button
                      className="rounded-streamly-pill bg-streamly-wash px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue hover:bg-streamly-lavender disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={!activeOutline.can_edit || isMutating}
                      onClick={() => setRegeneratingOutline(activeOutline)}
                      type="button"
                    >
                      <span className="inline-flex items-center gap-2">
                        <RefreshCw aria-hidden className="h-4 w-4" />
                        Regenerate
                      </span>
                    </button>
                    <button
                      className="inline-flex items-center gap-2 rounded-streamly-pill bg-white px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-wash disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={!hasChanges || !activeOutlineCanEdit || isMutating || !draftMarkdown.trim()}
                      onClick={() => void saveCurrentOutline()}
                      type="button"
                    >
                      <Save aria-hidden className="h-4 w-4" />
                      Save
                    </button>
                    <button
                      className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-electric px-3 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={
                        activeOutline.status === "approved" ||
                        hasChanges ||
                        !activeOutlineCanEdit ||
                        isMutating
                      }
                      onClick={() => void approveCurrentOutline()}
                      type="button"
                    >
                      <CheckCircle2 aria-hidden className="h-4 w-4" />
                      Approve
                    </button>
                  </div>
                </div>

                {activeOutlineReadOnlyReason ? (
                  <p className="mt-4 rounded-streamly-md bg-red-50 px-3 py-2 text-sm font-bold text-red-700">
                    {activeOutlineReadOnlyReason}
                  </p>
                ) : hasChanges ? (
                  <p className="mt-4 rounded-streamly-md bg-amber-50 px-3 py-2 text-sm font-bold text-amber-800">
                    Save changes before approving this outline for Brief readiness.
                  </p>
                ) : null}
              </div>

              <div className="border-b border-streamly-lavenderStrong px-4 py-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="inline-flex rounded-streamly-pill bg-streamly-wash p-1">
                    <ViewModeButton
                      isActive={viewMode === "split"}
                      label="Split"
                      onClick={() => setViewMode("split")}
                    />
                    <ViewModeButton
                      isActive={viewMode === "preview"}
                      label="Preview"
                      onClick={() => setViewMode("preview")}
                    />
                  </div>
                  <div className="flex w-full flex-col gap-2 sm:w-auto sm:min-w-[13rem]">
                    <div className="rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash/70 px-3 py-2">
                      <div className="flex items-center gap-2 text-streamly-violet">
                        <Keyboard aria-hidden className="h-4 w-4" />
                        <p className="text-xs font-extrabold uppercase">Shortcut</p>
                      </div>
                      <p className="mt-0.5 text-sm font-bold text-streamly-coal">
                        Cmd/Ctrl + S saves
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div
                className={[
                  "grid min-h-[34rem] gap-0",
                  viewMode === "split" ? "xl:grid-cols-2" : "grid-cols-1"
                ].join(" ")}
              >
                {viewMode === "split" ? (
                  <label className="min-h-[34rem] border-b border-streamly-lavenderStrong xl:border-b-0 xl:border-r">
                    <span className="sr-only">Markdown outline editor</span>
                    <textarea
                      className="h-full min-h-[34rem] w-full resize-none bg-white p-5 font-mono text-sm leading-7 text-streamly-coal outline-none disabled:cursor-not-allowed disabled:bg-streamly-wash/60"
                      disabled={!activeOutlineCanEdit || isMutating}
                      onChange={(event) => setDraftMarkdown(event.target.value)}
                      onKeyDown={handleEditorShortcut}
                      value={draftMarkdown}
                    />
                  </label>
                ) : null}

                <div className="min-h-[34rem] overflow-y-auto bg-streamly-wash/35 p-5">
                  <MarkdownPreview markdown={draftMarkdown} />
                </div>
              </div>
            </>
          ) : null}
        </section>

      </div>

      <RegenerateOutlineModal
        isOpen={regeneratingOutline !== null}
        isSubmitting={regenerateOutline.isPending}
        onClose={() => setRegeneratingOutline(null)}
        onConfirm={(instruction) => void regenerateCurrentOutline(instruction)}
        outline={regeneratingOutline}
      />
    </main>
  );
}

function OutlineSelector({
  activeOutlineId,
  outlines,
  onSelect
}: {
  activeOutlineId: string | null;
  outlines: EpisodeOutline[];
  onSelect: (outline: EpisodeOutline) => void;
}) {
  return (
    <aside className="space-y-2">
      {outlines.map((outline) => {
        const isActive = outline.id === activeOutlineId;
        return (
          <button
            className={[
              "w-full rounded-streamly-xl border p-4 text-left shadow-streamly-card transition",
              isActive
                ? "border-streamly-electric bg-white"
                : "border-streamly-lavenderStrong bg-white/82 hover:bg-streamly-wash"
            ].join(" ")}
            key={outline.id}
            onClick={() => onSelect(outline)}
            type="button"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="grid h-9 w-9 place-items-center rounded-streamly-lg bg-streamly-lavender font-streamly-platform text-sm font-extrabold text-streamly-electric">
                {outline.episode_number}
              </span>
              <StatusBadge label={outline.status} tone={outline.status} />
            </div>
            <p className="mt-3 line-clamp-2 text-sm font-extrabold text-streamly-coal">
              {outline.episode_title}
            </p>
            <div className="mt-4 rounded-streamly-lg bg-streamly-wash/70 p-3">
              <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
                Outline
              </p>
              <p className="mt-2 line-clamp-4 text-sm font-semibold leading-6 text-streamly-purpleBlue">
                {outlineSnippet(outline.outline_markdown)}
              </p>
            </div>
            <p className="mt-1 text-xs font-bold text-[var(--streamly-text-muted)]">
              v{outline.latest_version_number ?? 0} · {outline.version_count} version{outline.version_count === 1 ? "" : "s"}
            </p>
          </button>
        );
      })}
    </aside>
  );
}

function SaveIndicator({ state }: { state: SaveState }) {
  const label = state === "saving" ? "Saving" : state === "dirty" ? "Unsaved" : "Saved";
  const tone =
    state === "saving"
      ? "bg-streamly-lavender text-streamly-violet"
      : state === "dirty"
        ? "bg-amber-50 text-amber-800"
        : "bg-emerald-50 text-emerald-700";

  return (
    <span className={`inline-flex items-center gap-1 rounded-streamly-pill px-2.5 py-1 text-xs font-extrabold ${tone}`}>
      {state === "saved" ? <CheckCircle2 aria-hidden className="h-3.5 w-3.5" /> : <Clock3 aria-hidden className="h-3.5 w-3.5" />}
      {label}
    </span>
  );
}

function ViewModeButton({
  isActive,
  label,
  onClick
}: {
  isActive: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      aria-pressed={isActive}
      className={[
        "rounded-streamly-pill px-4 py-2 text-sm font-extrabold transition",
        isActive
          ? "bg-white text-streamly-violet shadow-streamly-card"
          : "text-streamly-purpleBlue hover:bg-white/70"
      ].join(" ")}
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
  );
}

function outlineSnippet(markdown: string) {
  const plainText = markdown
    .replace(/[#*_`>-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return plainText || "Outline content will appear here.";
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "The outline request could not be completed.";
}
