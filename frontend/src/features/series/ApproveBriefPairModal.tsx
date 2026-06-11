import { CheckCircle2, FileCheck2 } from "lucide-react";

import { Modal } from "@/design-system/components/Modal";
import type { BriefEpisodeWorkspace } from "@/shared/types/series";

type ApproveBriefPairModalProps = {
  episode: BriefEpisodeWorkspace | null;
  isOpen: boolean;
  isSubmitting: boolean;
  onClose: () => void;
  onConfirm: () => void;
};

export function ApproveBriefPairModal({
  episode,
  isOpen,
  isSubmitting,
  onClose,
  onConfirm
}: ApproveBriefPairModalProps) {
  const hostVersion = episode?.host_brief?.latest_version_number ?? 0;
  const guestVersion = episode?.guest_brief?.latest_version_number ?? 0;

  return (
    <Modal
      description="Approval is recorded for the host and guest briefs together."
      isOpen={isOpen}
      onClose={onClose}
      title="Approve Brief Pair"
    >
      <div className="space-y-5">
        <div className="rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash p-4">
          <div className="flex gap-3">
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-streamly-pill bg-white text-streamly-electric">
              <FileCheck2 aria-hidden className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-extrabold text-streamly-coal">
                Episode {episode?.episode_number ?? ""}: {episode?.episode_title ?? "Selected episode"}
              </p>
              <p className="mt-1 text-sm font-semibold leading-6 text-streamly-purpleBlue">
                This approves host brief v{hostVersion} and guest brief v{guestVersion}. Editing or
                regenerating either brief later will invalidate this approval.
              </p>
            </div>
          </div>
        </div>

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
            className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-electric px-4 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubmitting || !episode?.pair_generated}
            onClick={onConfirm}
            type="button"
          >
            <CheckCircle2 aria-hidden className="h-4 w-4" />
            {isSubmitting ? "Approving..." : "Approve pair"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
