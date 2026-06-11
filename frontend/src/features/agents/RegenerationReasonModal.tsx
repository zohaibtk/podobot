import { useEffect, useState } from "react";

import { Modal } from "@/design-system/components/Modal";

type RegenerationReasonModalProps = {
  isOpen: boolean;
  isSubmitting?: boolean;
  title?: string;
  description?: string;
  onClose: () => void;
  onConfirm: (reason: string) => void;
};

export function RegenerationReasonModal({
  isOpen,
  isSubmitting = false,
  title = "Regeneration reason",
  description = "Record why this AI run is being regenerated or retried.",
  onClose,
  onConfirm
}: RegenerationReasonModalProps) {
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (!isOpen) {
      setReason("");
    }
  }, [isOpen]);

  return (
    <Modal description={description} isOpen={isOpen} onClose={onClose} title={title}>
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (reason.trim().length >= 3) {
            onConfirm(reason.trim());
          }
        }}
      >
        <label className="block">
          <span className="text-sm font-extrabold text-streamly-coal">Reason</span>
          <textarea
            className="mt-2 min-h-28 w-full rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash px-3 py-2 font-streamly-body text-sm leading-6 text-streamly-coal outline-none focus:border-streamly-electric"
            onChange={(event) => setReason(event.target.value)}
            placeholder="Example: refine the narrative around operating cadence after new source review."
            value={reason}
          />
        </label>
        <div className="flex justify-end gap-2">
          <button className="streamly-button-secondary" onClick={onClose} type="button">
            Cancel
          </button>
          <button
            className="streamly-button-primary disabled:opacity-50"
            disabled={isSubmitting || reason.trim().length < 3}
            type="submit"
          >
            {isSubmitting ? "Recording..." : "Confirm"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
