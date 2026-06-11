import { Plus } from "lucide-react";
import { useEffect, useState } from "react";

import { Modal } from "@/design-system/components/Modal";
import type {
  CaptionPlatform,
  CaptionPlatformCreatePayload,
  CaptionVideoKind
} from "@/shared/types/series";

type AddPlatformModalProps = {
  availablePlatforms: CaptionPlatform[];
  clipSuggestionId?: string | null;
  isOpen: boolean;
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (payload: CaptionPlatformCreatePayload) => Promise<void>;
  videoKind: CaptionVideoKind;
};

export function AddPlatformModal({
  availablePlatforms,
  clipSuggestionId = null,
  isOpen,
  isSubmitting,
  onClose,
  onSubmit,
  videoKind
}: AddPlatformModalProps) {
  const [selectedPlatform, setSelectedPlatform] = useState<CaptionPlatform | "">("");

  useEffect(() => {
    setSelectedPlatform(availablePlatforms[0] ?? "");
  }, [availablePlatforms, isOpen]);

  async function submit() {
    if (!selectedPlatform) {
      return;
    }
    await onSubmit({
      video_kind: videoKind,
      platform: selectedPlatform,
      clip_suggestion_id: videoKind === "short_clip" ? clipSuggestionId : null
    });
    onClose();
  }

  return (
    <Modal
      description="Only valid, unconfigured platforms are available for this video row."
      isOpen={isOpen}
      onClose={onClose}
      title="Add platform"
    >
      {availablePlatforms.length ? (
        <div className="space-y-5">
          <div className="grid gap-2 sm:grid-cols-2">
            {availablePlatforms.map((platform) => {
              const isSelected = selectedPlatform === platform;
              return (
                <button
                  aria-pressed={isSelected}
                  className={[
                    "rounded-streamly-xl border p-4 text-left transition",
                    isSelected
                      ? "border-streamly-electric bg-streamly-lavender text-streamly-coal"
                      : "border-streamly-lavenderStrong bg-white text-streamly-purpleBlue hover:bg-streamly-wash"
                  ].join(" ")}
                  key={platform}
                  onClick={() => setSelectedPlatform(platform)}
                  type="button"
                >
                  <p className="font-streamly-platform text-base font-extrabold">
                    {platformLabel(platform)}
                  </p>
                  <p className="mt-1 text-xs font-bold">
                    {videoKind === "full_episode" ? "Full episode" : "Short clip"} caption row
                  </p>
                </button>
              );
            })}
          </div>

          <div className="flex justify-end">
            <button
              className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-electric px-4 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!selectedPlatform || isSubmitting}
              onClick={() => void submit()}
              type="button"
            >
              <Plus aria-hidden className="h-4 w-4" />
              Add platform
            </button>
          </div>
        </div>
      ) : (
        <div className="rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash/70 p-5">
          <p className="text-sm font-extrabold text-streamly-coal">
            All valid platforms are already configured.
          </p>
          <p className="mt-2 text-sm font-semibold leading-6 text-streamly-purpleBlue">
            Generate, edit, or regenerate the existing rows before moving to Scheduling.
          </p>
        </div>
      )}
    </Modal>
  );
}

function platformLabel(platform: CaptionPlatform) {
  if (platform === "x") {
    return "X";
  }
  return platform.charAt(0).toUpperCase() + platform.slice(1);
}
