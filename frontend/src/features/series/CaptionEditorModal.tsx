import { CheckCircle2, RefreshCw, Save } from "lucide-react";
import { useEffect, useState } from "react";

import { Modal } from "@/design-system/components/Modal";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import type {
  CaptionUpdatePayload,
  EpisodeVideoPlatformCaption
} from "@/shared/types/series";

type CaptionEditorModalProps = {
  caption: EpisodeVideoPlatformCaption | null;
  isOpen: boolean;
  isMutating: boolean;
  onClose: () => void;
  onRegenerate: (captionId: string) => Promise<unknown>;
  onSave: (captionId: string, payload: CaptionUpdatePayload) => Promise<unknown>;
};

export function CaptionEditorModal({
  caption,
  isOpen,
  isMutating,
  onClose,
  onRegenerate,
  onSave
}: CaptionEditorModalProps) {
  const [draft, setDraft] = useState("");

  useEffect(() => {
    setDraft(caption?.caption_text ?? "");
  }, [caption?.id, caption?.caption_text]);

  if (!caption) {
    return null;
  }

  const hasChanges = draft !== (caption.caption_text ?? "");
  const canSave = draft.trim().length > 0 && hasChanges && !isMutating;

  async function save() {
    if (!caption || !canSave) {
      return;
    }
    await onSave(caption.id, { caption_text: draft.trim() });
    onClose();
  }

  async function regenerate() {
    if (!caption || isMutating) {
      return;
    }
    await onRegenerate(caption.id);
    onClose();
  }

  return (
    <Modal
      description="Edit the platform-specific copy that will become available for the Scheduling stage."
      isOpen={isOpen}
      onClose={onClose}
      title={`${platformLabel(caption.platform)} caption`}
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge label={caption.video_kind} tone="neutral" />
          <StatusBadge label={caption.status} tone={caption.status} />
          {caption.can_schedule ? (
            <span className="inline-flex items-center gap-1 rounded-streamly-pill bg-emerald-50 px-2.5 py-1 text-xs font-extrabold text-emerald-700">
              <CheckCircle2 aria-hidden className="h-3.5 w-3.5" />
              Scheduling ready
            </span>
          ) : null}
        </div>

        <label className="block">
          <span className="mb-2 block text-xs font-extrabold uppercase text-streamly-purpleBlue">
            Caption copy
          </span>
          <textarea
            className="min-h-72 w-full resize-none rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash/45 p-4 font-streamly-body text-sm font-semibold leading-7 text-streamly-coal outline-none focus:border-streamly-electric focus:bg-white"
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Write or generate caption copy for this platform."
            value={draft}
          />
        </label>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs font-bold text-[var(--streamly-text-muted)]">
            v{caption.generation_count} ·{" "}
            {caption.generated_at ? "generated from transcript context" : "manual draft allowed"}
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              className="inline-flex items-center gap-2 rounded-streamly-pill bg-white px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-wash disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isMutating}
              onClick={() => void regenerate()}
              type="button"
            >
              <RefreshCw aria-hidden className="h-4 w-4" />
              Regenerate
            </button>
            <button
              className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-coal px-3 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!canSave}
              onClick={() => void save()}
              type="button"
            >
              <Save aria-hidden className="h-4 w-4" />
              Save caption
            </button>
          </div>
        </div>
      </div>
    </Modal>
  );
}

function platformLabel(platform: string) {
  if (platform === "x") {
    return "X";
  }
  return platform.charAt(0).toUpperCase() + platform.slice(1);
}
