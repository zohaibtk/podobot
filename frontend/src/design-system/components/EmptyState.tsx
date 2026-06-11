import { Boxes, Sparkles } from "lucide-react";

type EmptyStateProps = {
  title: string;
  description: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="grid min-h-[22rem] place-items-center rounded-streamly-panel border border-dashed border-streamly-lavenderStrong/80 bg-white/80 p-8 text-center shadow-streamly-card">
      <div className="max-w-xl">
        <div className="mx-auto grid h-20 w-20 place-items-center rounded-streamly-panel bg-streamly-wash text-streamly-electric shadow-streamly-card">
          <div className="grid h-12 w-12 place-items-center rounded-streamly-pill bg-white shadow-streamly-card">
            <Boxes aria-hidden className="h-5 w-5" />
          </div>
        </div>
        <div className="mx-auto mt-5 inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-lavender px-3 py-1 text-xs font-extrabold uppercase text-streamly-violet">
          <Sparkles aria-hidden className="h-3.5 w-3.5" />
          Ready when you are
        </div>
        <h2 className="mt-4 font-streamly-platform text-2xl font-extrabold text-streamly-coal">
          {title}
        </h2>
        <p className="mx-auto mt-3 max-w-md font-streamly-body text-sm leading-6 text-[var(--streamly-text-muted)]">
          {description}
        </p>
      </div>
    </div>
  );
}
