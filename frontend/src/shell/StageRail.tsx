import { Lock, Radio, Timer } from "lucide-react";

import { seriesStages } from "@/routes/routeRegistry";

export function StageRail() {
  return (
    <aside
      aria-label="Series stage overview"
      className="border-b border-streamly-lavenderStrong bg-white/74 px-4 py-4 shadow-streamly-card backdrop-blur lg:border-b-0 lg:border-r"
    >
      <div className="mb-5 flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric shadow-streamly-card">
          <Radio aria-hidden className="h-4 w-4" />
        </div>
        <div>
          <p className="streamly-kicker">Stage rail</p>
          <p className="mt-1 text-sm font-extrabold text-streamly-coal">
            Production path
          </p>
        </div>
      </div>
      <ol className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:flex lg:flex-col">
        {seriesStages.map((stage, index) => (
          <li key={stage.id}>
            <div className="flex w-full items-center justify-between gap-3 rounded-streamly-card bg-streamly-wash/62 px-3 py-3 text-left text-sm font-bold text-[var(--streamly-text-muted)]">
              <span className="flex min-w-0 items-center gap-3">
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-streamly-pill bg-white text-xs text-streamly-purpleBlue">
                  {index + 1}
                </span>
                <span className="truncate">{stage.label}</span>
              </span>
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-streamly-pill bg-white text-streamly-purpleBlue">
                {index === 0 ? (
                  <Timer
                    aria-label="Stage pending series context"
                    className="h-3.5 w-3.5"
                    role="img"
                  />
                ) : (
                  <Lock
                    aria-label="Stage locked until business workflow exists"
                    className="h-3.5 w-3.5"
                    role="img"
                  />
                )}
              </span>
            </div>
          </li>
        ))}
      </ol>
    </aside>
  );
}
