import { CalendarClock, Send } from "lucide-react";
import { useMemo, useState } from "react";

import { Modal } from "@/design-system/components/Modal";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import type { BulkSchedulePayload, ScheduleRow } from "@/shared/types/series";

type BulkScheduleModalProps = {
  isOpen: boolean;
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (payload: BulkSchedulePayload) => Promise<unknown>;
  rows: ScheduleRow[];
};

export function BulkScheduleModal({
  isOpen,
  isSubmitting,
  onClose,
  onSubmit,
  rows
}: BulkScheduleModalProps) {
  const [scheduledFor, setScheduledFor] = useState(toDateTimeLocal());
  const [spacingMinutes, setSpacingMinutes] = useState(30);
  const [validationError, setValidationError] = useState<string | null>(null);
  const platformSummary = useMemo(() => {
    const counts = rows.reduce<Record<string, number>>((accumulator, row) => {
      accumulator[row.platform] = (accumulator[row.platform] ?? 0) + 1;
      return accumulator;
    }, {});
    return Object.entries(counts);
  }, [rows]);

  async function submit() {
    const scheduledAt = toIsoDate(scheduledFor);
    if (!scheduledAt) {
      setValidationError("Choose a valid schedule time.");
      return;
    }
    await onSubmit({
      caption_ids: rows.map((row) => row.caption_id),
      scheduled_for: scheduledAt,
      spacing_minutes: spacingMinutes
    });
    onClose();
  }

  return (
    <Modal
      description="Bulk scheduling applies a shared start time and optional spacing to eligible captioned rows only."
      isOpen={isOpen}
      onClose={onClose}
      title="Bulk schedule Buffer posts"
    >
      <div className="space-y-4">
        <div className="rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash/60 p-4">
          <p className="text-sm font-extrabold text-streamly-coal">
            {rows.length} eligible row{rows.length === 1 ? "" : "s"} selected
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {platformSummary.map(([platform, count]) => (
              <StatusBadge
                key={platform}
                label={`${platformLabel(platform)} ${count}`}
                tone="neutral"
              />
            ))}
          </div>
        </div>

        <label className="block">
          <span className="mb-2 flex items-center gap-2 text-xs font-extrabold uppercase text-streamly-purpleBlue">
            <CalendarClock aria-hidden className="h-4 w-4" />
            Start time
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
            Spacing between posts
          </span>
          <input
            className="w-full rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash/45 px-4 py-3 text-sm font-bold text-streamly-coal outline-none focus:border-streamly-electric focus:bg-white"
            max={1440}
            min={0}
            onChange={(event) => setSpacingMinutes(Number(event.target.value))}
            type="number"
            value={spacingMinutes}
          />
        </label>

        {validationError ? (
          <div className="rounded-streamly-xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-900">
            {validationError}
          </div>
        ) : null}

        <div className="flex flex-wrap justify-end gap-2">
          <button
            className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-electric px-4 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!rows.length || isSubmitting}
            onClick={() => void submit()}
            type="button"
          >
            <Send aria-hidden className="h-4 w-4" />
            Schedule {rows.length} row{rows.length === 1 ? "" : "s"}
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
