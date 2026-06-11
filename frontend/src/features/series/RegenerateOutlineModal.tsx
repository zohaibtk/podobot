import { Loader2, RefreshCw, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

import { Modal } from "@/design-system/components/Modal";
import type { EpisodeOutline } from "@/shared/types/series";

const MAX_INSTRUCTION_LENGTH = 600;

type RegenerateOutlineModalProps = {
  isOpen: boolean;
  outline: EpisodeOutline | null;
  isSubmitting: boolean;
  onClose: () => void;
  onConfirm: (instruction: string) => void;
};

export function RegenerateOutlineModal({
  isOpen,
  outline,
  isSubmitting,
  onClose,
  onConfirm
}: RegenerateOutlineModalProps) {
  const [instruction, setInstruction] = useState("");
  const instructionLength = instruction.length;
  const isInstructionAtLimit = instructionLength === MAX_INSTRUCTION_LENGTH;
  const isInstructionTooLong = instructionLength > MAX_INSTRUCTION_LENGTH;

  useEffect(() => {
    if (isOpen) {
      setInstruction("");
    }
  }, [isOpen, outline?.id]);

  return (
    <Modal
      description="Regeneration preserves the current version in history and creates a new latest outline."
      isOpen={isOpen}
      onClose={onClose}
      title="Regenerate Outline"
    >
      <div className="space-y-5">
        <div className="rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash p-4">
          <div className="flex gap-3">
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-streamly-pill bg-white text-streamly-electric">
              <Sparkles aria-hidden className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-extrabold text-streamly-coal">
                {outline?.episode_title ?? "Selected episode"}
              </p>
              <p className="mt-1 text-sm font-semibold leading-6 text-streamly-purpleBlue">
                A regenerated outline stays profile-agnostic and becomes the latest context for the next Brief slice.
              </p>
            </div>
          </div>
        </div>

        <label className="block">
          <span className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
            Producer direction
          </span>
          <textarea
            className="mt-2 min-h-24 w-full rounded-streamly-md border border-streamly-lavenderStrong px-3 py-2 text-sm font-semibold leading-6 text-streamly-coal outline-none focus:border-streamly-electric focus:ring-2 focus:ring-streamly-lavender disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubmitting || !outline?.can_edit}
            maxLength={MAX_INSTRUCTION_LENGTH}
            onChange={(event) => setInstruction(event.target.value)}
            placeholder="Sharper hook, more concrete evidence, stronger handoff to the Brief stage..."
            value={instruction}
          />
          <span
            className={[
              "mt-2 flex justify-between gap-3 text-xs font-bold",
              isInstructionTooLong || isInstructionAtLimit
                ? "text-red-700"
                : "text-streamly-purpleBlue"
            ].join(" ")}
          >
            <span>
              {isInstructionTooLong
                ? "Keep producer direction to 600 characters or fewer."
                : isInstructionAtLimit
                  ? "600 character limit reached."
                : "Keep this direction short and specific."}
            </span>
            <span>
              {instructionLength}/{MAX_INSTRUCTION_LENGTH}
            </span>
          </span>
        </label>

        <div className="flex flex-wrap justify-end gap-3">
          <button
            className="rounded-streamly-pill px-4 py-2 text-sm font-extrabold text-streamly-purpleBlue hover:bg-streamly-wash"
            disabled={isSubmitting}
            onClick={onClose}
            type="button"
          >
            Cancel
          </button>
          <button
            className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-coal px-4 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubmitting || !outline?.can_edit || isInstructionTooLong}
            onClick={() => onConfirm(instruction)}
            type="button"
          >
            {isSubmitting ? (
              <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw aria-hidden className="h-4 w-4" />
            )}
            {isSubmitting ? "Regenerating..." : "Regenerate"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
