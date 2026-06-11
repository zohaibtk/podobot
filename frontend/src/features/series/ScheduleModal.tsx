import { CalendarClock, Save, Send } from "lucide-react";
import { useEffect, useState } from "react";

import { Modal } from "@/design-system/components/Modal";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import type {
  ScheduleCreatePayload,
  ScheduleReschedulePayload,
  ScheduleRow,
  ScheduleUpdatePayload
} from "@/shared/types/series";

export type ScheduleModalMode = "create" | "edit" | "reschedule";

type ScheduleModalProps = {
  isOpen: boolean;
  isSubmitting: boolean;
  mode: ScheduleModalMode;
  onClose: () => void;
  onSubmit: (
    row: ScheduleRow,
    payload: ScheduleCreatePayload | ScheduleUpdatePayload | ScheduleReschedulePayload
  ) => Promise<unknown>;
  row: ScheduleRow | null;
};

export function ScheduleModal({
  isOpen,
  isSubmitting,
  mode,
  onClose,
  onSubmit,
  row
}: ScheduleModalProps) {
  const [scheduledFor, setScheduledFor] = useState(toDateTimeLocal());
  const [captionText, setCaptionText] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    setScheduledFor(toDateTimeLocal(row?.schedule?.scheduled_for));
    setCaptionText(row?.schedule?.scheduled_caption_text ?? row?.caption_text ?? "");
    setValidationError(null);
  }, [row?.caption_id, row?.schedule?.scheduled_for, row?.schedule?.scheduled_caption_text, row?.caption_text]);

  if (!row) {
    return null;
  }

  const activeRow = row;
  const title =
    mode === "create"
      ? `Schedule ${platformLabel(activeRow.platform)}`
      : mode === "edit"
        ? `Edit ${platformLabel(activeRow.platform)} post`
        : `Reschedule ${platformLabel(activeRow.platform)} post`;
  const canEditCopy = mode !== "create";
  const canSubmit = scheduledFor.length > 0 && (!canEditCopy || captionText.trim().length > 0);

  async function submit() {
    if (!canSubmit || isSubmitting) {
      return;
    }
    const scheduledAt = toIsoDate(scheduledFor);
    if (!scheduledAt) {
      setValidationError("Choose a valid schedule time.");
      return;
    }

    const payload =
      mode === "create"
        ? { caption_id: activeRow.caption_id, scheduled_for: scheduledAt }
        : {
            scheduled_for: scheduledAt,
            scheduled_caption_text: captionText.trim()
          };
    await onSubmit(activeRow, payload);
    onClose();
  }

  return (
    <Modal
      description="Buffer is the publishing system of record. This schedule is scoped to one captioned video/platform row."
      isOpen={isOpen}
      onClose={onClose}
      title={title}
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge label={activeRow.video_kind} tone="neutral" />
          <StatusBadge label={activeRow.platform} tone="neutral" />
          {activeRow.schedule ? (
            <StatusBadge label={activeRow.schedule.status} tone={activeRow.schedule.status} />
          ) : (
            <StatusBadge label="ready" tone="ready" />
          )}
        </div>

        <label className="block">
          <span className="mb-2 flex items-center gap-2 text-xs font-extrabold uppercase text-streamly-purpleBlue">
            <CalendarClock aria-hidden className="h-4 w-4" />
            Schedule time
          </span>
          <input
            className="w-full rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash/45 px-4 py-3 text-sm font-bold text-streamly-coal outline-none focus:border-streamly-electric focus:bg-white"
            min={toDateTimeLocal()}
            onChange={(event) => setScheduledFor(event.target.value)}
            type="datetime-local"
            value={scheduledFor}
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-xs font-extrabold uppercase text-streamly-purpleBlue">
            Buffer post copy
          </span>
          <textarea
            className="min-h-44 w-full resize-none rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash/45 p-4 text-sm font-semibold leading-7 text-streamly-coal outline-none focus:border-streamly-electric focus:bg-white disabled:text-[var(--streamly-text-muted)]"
            disabled={!canEditCopy}
            onChange={(event) => setCaptionText(event.target.value)}
            value={captionText}
          />
          <p className="mt-2 text-xs font-bold text-[var(--streamly-text-muted)]">
            {canEditCopy
              ? "Editing scheduled copy updates the Buffer post."
              : "Initial scheduling uses the approved platform caption."}
          </p>
        </label>

        {activeRow.schedule?.failure_reason ? (
          <div className="rounded-streamly-xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700">
            {activeRow.schedule.failure_reason}
          </div>
        ) : null}

        {validationError ? (
          <div className="rounded-streamly-xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-900">
            {validationError}
          </div>
        ) : null}

        <div className="flex flex-wrap justify-end gap-2">
          <button
            className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-coal px-4 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!canSubmit || isSubmitting}
            onClick={() => void submit()}
            type="button"
          >
            {mode === "edit" ? (
              <Save aria-hidden className="h-4 w-4" />
            ) : (
              <Send aria-hidden className="h-4 w-4" />
            )}
            {mode === "create" ? "Schedule post" : mode === "edit" ? "Save post" : "Reschedule post"}
          </button>
        </div>
      </div>
    </Modal>
  );
}

function toDateTimeLocal(value?: string | null) {
  const date = value ? new Date(value) : new Date(Date.now() + 2 * 60 * 60 * 1000);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function toIsoDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function platformLabel(platform: string) {
  if (platform === "x") {
    return "X";
  }
  return platform.charAt(0).toUpperCase() + platform.slice(1);
}
