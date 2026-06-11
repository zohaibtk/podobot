import { ArrowRight, ShieldCheck } from "lucide-react";

import { Modal } from "@/design-system/components/Modal";
import type { StrategyIdea } from "@/shared/types/strategy";

type ConvertIdeaModalProps = {
  idea: StrategyIdea | null;
  isOpen: boolean;
  isConverting: boolean;
  errorMessage: string | null;
  onClose: () => void;
  onConfirm: (idea: StrategyIdea) => void;
};

export function ConvertIdeaModal({
  idea,
  isOpen,
  isConverting,
  errorMessage,
  onClose,
  onConfirm
}: ConvertIdeaModalProps) {
  if (!idea) {
    return null;
  }

  return (
    <Modal
      description="Create a draft series from this proposal and send it to Episode Plan review."
      isOpen={isOpen}
      onClose={onClose}
      title="Convert idea to series"
    >
      <div className="space-y-5">
        <div className="rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash p-4">
          <p className="streamly-kicker">Draft series</p>
          <h3 className="mt-1 font-streamly-platform text-xl font-extrabold text-streamly-coal">
            {idea.title}
          </h3>
          <p className="mt-3 text-sm font-bold leading-6 text-streamly-purpleBlue">
            {idea.description}
          </p>
        </div>

        <div className="rounded-streamly-lg border border-emerald-100 bg-emerald-50 p-4 text-emerald-800">
          <div className="flex items-center gap-2">
            <ShieldCheck aria-hidden className="h-4 w-4" />
            <p className="text-sm font-extrabold">Human approval gates stay active</p>
          </div>
          <p className="mt-2 text-sm font-bold leading-6">
            Conversion creates the selected narrative and editable episode plan, but the
            plan is not locked and briefs, recordings, captions, and scheduling remain gated.
          </p>
        </div>

        {errorMessage ? (
          <div className="rounded-streamly-md border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700">
            {errorMessage}
          </div>
        ) : null}

        <div className="flex flex-wrap justify-end gap-2 border-t border-streamly-lavenderStrong pt-4">
          <button className="streamly-button-secondary" onClick={onClose} type="button">
            Cancel
          </button>
          <button
            className="streamly-button-primary"
            disabled={isConverting}
            onClick={() => onConfirm(idea)}
            type="button"
          >
            <ArrowRight aria-hidden className="h-4 w-4" />
            {isConverting ? "Converting" : "Convert and open plan"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
