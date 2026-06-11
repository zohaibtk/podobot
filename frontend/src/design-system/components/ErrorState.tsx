import { AlertTriangle } from "lucide-react";

type ErrorStateProps = {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function ErrorState({ title, description, actionLabel, onAction }: ErrorStateProps) {
  return (
    <div className="rounded-streamly-panel border border-red-100 bg-white p-5 text-red-900 shadow-streamly-card">
      <div className="flex gap-3">
        <div className="grid h-11 w-11 shrink-0 place-items-center rounded-streamly-pill bg-red-50 text-red-700">
          <AlertTriangle aria-hidden className="h-5 w-5" />
        </div>
        <div>
          <p className="streamly-kicker text-red-700">Attention needed</p>
          <h2 className="font-streamly-platform text-xl font-extrabold text-streamly-coal">
            {title}
          </h2>
          <p className="mt-2 max-w-2xl font-streamly-body text-sm leading-6 text-red-800">
            {description}
          </p>
          {actionLabel && onAction ? (
            <button
              className="mt-4 rounded-streamly-pill bg-red-700 px-4 py-2 text-sm font-extrabold text-white shadow-streamly-card transition hover:-translate-y-0.5 hover:bg-red-800"
              onClick={onAction}
              type="button"
            >
              {actionLabel}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
