import { Loader2 } from "lucide-react";

type UploadProgressProps = {
  label: string;
  isActive: boolean;
};

export function UploadProgress({ label, isActive }: UploadProgressProps) {
  if (!isActive) {
    return null;
  }

  return (
    <div
      aria-live="polite"
      className="rounded-streamly-md border border-streamly-lavenderStrong bg-streamly-wash px-3 py-2"
    >
      <div className="flex items-center gap-2 text-sm font-extrabold text-streamly-purpleBlue">
        <Loader2 aria-hidden className="h-4 w-4 animate-spin text-streamly-electric" />
        {label}
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-streamly-pill bg-white">
        <div className="h-full w-2/3 animate-pulse rounded-streamly-pill bg-streamly-electric" />
      </div>
      <p className="mt-2 text-xs font-bold text-[var(--streamly-text-muted)]">
        Validating format, streaming storage, and preparing processing jobs.
      </p>
    </div>
  );
}
