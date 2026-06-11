import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Download,
  Eye,
  Pencil,
  Save
} from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import { StatusBadge } from "@/design-system/components/StatusBadge";
import { MarkdownPreview } from "@/features/series/MarkdownPreview";
import type { BriefKind, BriefUpdatePayload, EpisodeBrief } from "@/shared/types/series";

type BriefEditorPanelProps = {
  brief: EpisodeBrief | null;
  kind: BriefKind;
  isMutating: boolean;
  isPairApproved: boolean;
  onDownload: (briefId: string) => Promise<void>;
  onSave: (briefId: string, payload: BriefUpdatePayload) => Promise<void>;
};

type SaveState = "saved" | "dirty" | "saving";
type ViewMode = "edit" | "preview";

export function BriefEditorPanel({
  brief,
  kind,
  isMutating,
  isPairApproved,
  onDownload,
  onSave
}: BriefEditorPanelProps) {
  const [draftTitle, setDraftTitle] = useState("");
  const [draftMarkdown, setDraftMarkdown] = useState("");
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [viewMode, setViewMode] = useState<ViewMode>("preview");

  useEffect(() => {
    setDraftTitle(brief?.title ?? "");
    setDraftMarkdown(brief?.brief_markdown ?? "");
    setSaveState("saved");
  }, [brief?.id, brief?.current_version_id, brief?.title, brief?.brief_markdown]);

  useEffect(() => {
    setViewMode("preview");
  }, [brief?.id]);

  const hasChanges = Boolean(
    brief && (draftTitle !== brief.title || draftMarkdown !== brief.brief_markdown)
  );
  const laneLabel = kind === "host" ? "Host" : "Guest";

  useEffect(() => {
    if (!brief || saveState === "saving") {
      return;
    }
    setSaveState(hasChanges ? "dirty" : "saved");
  }, [brief, draftMarkdown, draftTitle, hasChanges, saveState]);

  async function saveBrief() {
    if (!brief || !brief.can_edit || !draftMarkdown.trim()) {
      return;
    }
    setSaveState("saving");
    await onSave(brief.id, {
      title: draftTitle.trim() || brief.title,
      brief_markdown: draftMarkdown
    });
    setSaveState("saved");
  }

  if (!brief) {
    return (
      <section className="min-h-[34rem] rounded-streamly-xl border border-dashed border-streamly-lavenderStrong bg-white/80 p-5">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
            {laneLabel} brief
          </p>
          <StatusBadge label="not generated" tone="neutral" />
        </div>
        <div className="mt-16 grid place-items-center text-center">
          <div className="max-w-sm">
            <div className="mx-auto grid h-12 w-12 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric">
              <Pencil aria-hidden className="h-5 w-5" />
            </div>
            <h3 className="mt-4 font-streamly-platform text-lg font-extrabold text-streamly-coal">
              {laneLabel} document waiting
            </h3>
            <p className="mt-2 text-sm font-semibold leading-6 text-[var(--streamly-text-muted)]">
              Generate the brief pair once host, guest, and approved outline context are ready.
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="min-w-0 rounded-streamly-xl border border-streamly-lavenderStrong bg-white shadow-streamly-card">
      <div className="border-b border-streamly-lavenderStrong p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge label={`${kind} brief`} tone="neutral" />
              <StatusBadge label={brief.status} tone={brief.status} />
              <SaveIndicator state={saveState} />
            </div>
            <input
              className="mt-3 w-full rounded-streamly-md border border-transparent bg-transparent px-0 py-1 font-streamly-platform text-lg font-extrabold text-streamly-coal outline-none focus:border-streamly-lavenderStrong focus:bg-streamly-wash focus:px-3 disabled:cursor-not-allowed"
              disabled={!brief.can_edit || isMutating}
              onChange={(event) => setDraftTitle(event.target.value)}
              value={draftTitle}
            />
            <p className="mt-1 text-xs font-bold text-[var(--streamly-text-muted)]">
              {brief.profile_name ?? laneLabel} · v{brief.latest_version_number ?? 0} ·{" "}
              {brief.version_count} version{brief.version_count === 1 ? "" : "s"}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              className="grid h-9 w-9 place-items-center rounded-streamly-pill bg-white text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-wash disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isMutating}
              onClick={() => void onDownload(brief.id)}
              title="Download brief"
              type="button"
            >
              <Download aria-hidden className="h-4 w-4" />
            </button>
            <button
              className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-coal px-3 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!hasChanges || !brief.can_edit || isMutating || !draftMarkdown.trim()}
              onClick={() => void saveBrief()}
              type="button"
            >
              <Save aria-hidden className="h-4 w-4" />
              Save
            </button>
          </div>
        </div>

        {brief.read_only_reason ? (
          <InlineNotice tone="danger" text={brief.read_only_reason} />
        ) : hasChanges && isPairApproved ? (
          <InlineNotice
            tone="warning"
            text="Saving this change will invalidate the approved host/guest pair."
          />
        ) : brief.approval_invalidated_at ? (
          <InlineNotice
            tone="warning"
            text="Approval was invalidated. Re-approve the pair after review."
          />
        ) : null}
      </div>

      <div className="border-b border-streamly-lavenderStrong px-4 py-3">
        <div className="inline-flex rounded-streamly-pill bg-streamly-wash p-1">
          <ModeButton
            icon={<Pencil aria-hidden className="h-4 w-4" />}
            isActive={viewMode === "edit"}
            label="Edit"
            onClick={() => setViewMode("edit")}
          />
          <ModeButton
            icon={<Eye aria-hidden className="h-4 w-4" />}
            isActive={viewMode === "preview"}
            label="Preview"
            onClick={() => setViewMode("preview")}
          />
        </div>
      </div>

      {viewMode === "edit" ? (
        <label className="block">
          <span className="sr-only">{laneLabel} brief markdown editor</span>
          <textarea
            className="min-h-[28rem] w-full resize-none bg-white p-5 font-mono text-sm leading-7 text-streamly-coal outline-none disabled:cursor-not-allowed disabled:bg-streamly-wash/60"
            disabled={!brief.can_edit || isMutating}
            onChange={(event) => setDraftMarkdown(event.target.value)}
            value={draftMarkdown}
          />
        </label>
      ) : (
        <div className="min-h-[28rem] overflow-y-auto bg-streamly-wash/35 p-5">
          <MarkdownPreview markdown={draftMarkdown} />
        </div>
      )}
    </section>
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
      {state === "saved" ? (
        <CheckCircle2 aria-hidden className="h-3.5 w-3.5" />
      ) : (
        <Clock3 aria-hidden className="h-3.5 w-3.5" />
      )}
      {label}
    </span>
  );
}

function ModeButton({
  icon,
  isActive,
  label,
  onClick
}: {
  icon: ReactNode;
  isActive: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      aria-pressed={isActive}
      className={[
        "inline-flex items-center gap-2 rounded-streamly-pill px-3 py-2 text-sm font-extrabold transition",
        isActive
          ? "bg-white text-streamly-violet shadow-streamly-card"
          : "text-streamly-purpleBlue hover:bg-white/70"
      ].join(" ")}
      onClick={onClick}
      type="button"
    >
      {icon}
      {label}
    </button>
  );
}

function InlineNotice({ text, tone }: { text: string; tone: "danger" | "warning" }) {
  const className =
    tone === "danger"
      ? "bg-red-50 text-red-700"
      : "bg-amber-50 text-amber-800";

  return (
    <div className={`mt-4 flex gap-2 rounded-streamly-md px-3 py-2 ${className}`}>
      <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
      <p className="text-xs font-bold leading-5">{text}</p>
    </div>
  );
}
