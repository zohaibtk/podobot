type LoadingStateProps = {
  label: string;
};

export function LoadingState({ label }: LoadingStateProps) {
  return (
    <div className="streamly-ai-pulse rounded-streamly-panel border border-streamly-lavenderStrong/80 bg-white/88 p-6 shadow-streamly-card">
      <div className="flex items-center gap-3" aria-label={label} role="status">
        <div className="grid h-11 w-11 place-items-center rounded-streamly-pill bg-streamly-lavender">
          <div className="h-4 w-4 animate-pulse rounded-streamly-pill bg-streamly-electric" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="h-3 w-36 animate-pulse rounded-streamly-pill bg-streamly-lavender" />
          <div className="mt-3 h-4 max-w-xl animate-pulse rounded-streamly-pill bg-streamly-wash" />
        </div>
      </div>
      <div className="mt-6 grid gap-3 md:grid-cols-3">
        <div className="h-24 animate-pulse rounded-streamly-xl bg-streamly-wash" />
        <div className="h-24 animate-pulse rounded-streamly-xl bg-streamly-wash" />
        <div className="h-24 animate-pulse rounded-streamly-xl bg-streamly-wash" />
      </div>
    </div>
  );
}
