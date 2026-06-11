import { LockKeyhole, ShieldCheck } from "lucide-react";

import { Modal } from "@/design-system/components/Modal";
import type { PlanLockReadiness } from "@/shared/types/series";

type LockPlanModalProps = {
  episodeCount: number;
  isOpen: boolean;
  isSubmitting: boolean;
  readiness: PlanLockReadiness;
  onClose: () => void;
  onConfirm: () => void;
};

export function LockPlanModal({
  episodeCount,
  isOpen,
  isSubmitting,
  readiness,
  onClose,
  onConfirm
}: LockPlanModalProps) {
  return (
    <Modal
      description="Locking freezes the editorial plan and creates profile-agnostic outlines for production."
      isOpen={isOpen}
      onClose={onClose}
      title="Lock Episode Plan"
    >
      <div className="space-y-4">
        <div className="rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash p-4">
          <div className="flex items-start gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-streamly-pill bg-white text-streamly-electric">
              {readiness.is_ready ? (
                <ShieldCheck aria-hidden className="h-5 w-5" />
              ) : (
                <LockKeyhole aria-hidden className="h-5 w-5" />
              )}
            </div>
            <div>
              <p className="text-sm font-extrabold text-streamly-coal">
                {readiness.is_ready
                  ? `${episodeCount} episode plan is ready to lock`
                  : `${readiness.missing_episode_count} episode(s) need assignments`}
              </p>
              <p className="mt-1 text-sm leading-6 text-streamly-purpleBlue">
                {readiness.is_ready
                  ? "Production stages will unlock after outlines are created."
                  : "Complete every host and guest assignment before locking the board."}
              </p>
            </div>
          </div>
        </div>

        {readiness.warnings.length ? (
          <ul className="space-y-2">
            {readiness.warnings.map((warning) => (
              <li
                className="rounded-streamly-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-bold text-red-800"
                key={warning}
              >
                {warning}
              </li>
            ))}
          </ul>
        ) : null}

        <div className="flex flex-wrap justify-end gap-3 pt-2">
          <button
            className="rounded-streamly-pill px-4 py-2 text-sm font-extrabold text-streamly-purpleBlue hover:bg-streamly-wash"
            onClick={onClose}
            type="button"
          >
            Cancel
          </button>
          <button
            className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-coal px-4 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-60"
            disabled={!readiness.is_ready || isSubmitting}
            onClick={onConfirm}
            type="button"
          >
            <LockKeyhole aria-hidden className="h-4 w-4" />
            {isSubmitting ? "Locking" : "Lock plan"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
