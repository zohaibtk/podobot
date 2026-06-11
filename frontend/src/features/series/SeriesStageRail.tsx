import { Link } from "react-router-dom";
import { Check, Lock } from "lucide-react";

import { seriesStages, type SeriesStageId } from "@/routes/routeRegistry";
import {
  isStageComplete,
  isStageUnlocked,
  type SeriesStageGates
} from "@/features/series/stageProgress";
import type { Series } from "@/shared/types/series";

type SeriesStageRailProps = {
  series: Series;
  activeStage: SeriesStageId;
  hasApprovedBriefs: boolean;
  hasApprovedOutline: boolean;
  hasCaptionsReadyForScheduling: boolean;
  hasDiscoveryRun: boolean;
  hasLockedPlan: boolean;
  hasSelectedNarrative: boolean;
  hasTranscriptForCaptions: boolean;
};

export function SeriesStageRail({
  series,
  activeStage,
  hasApprovedBriefs,
  hasApprovedOutline,
  hasCaptionsReadyForScheduling,
  hasDiscoveryRun,
  hasLockedPlan,
  hasSelectedNarrative,
  hasTranscriptForCaptions
}: SeriesStageRailProps) {
  const activeStageIndex = seriesStages.findIndex((stage) => stage.id === activeStage);
  const gates: SeriesStageGates = {
    hasApprovedBriefs,
    hasApprovedOutline,
    hasCaptionsReadyForScheduling,
    hasDiscoveryRun,
    hasLockedPlan,
    hasSelectedNarrative,
    hasTranscriptForCaptions
  };

  return (
    <nav
      aria-label="Series production stages"
      className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white/92 px-4 py-4 shadow-streamly-card backdrop-blur"
    >
      <p className="mb-3 text-center text-[11px] font-extrabold uppercase text-streamly-purpleBlue">
        Production stages
      </p>
      <div className="overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <ol className="mx-auto flex w-max min-w-full items-center justify-start lg:justify-center">
          {seriesStages.map((stage, index) => {
            const isUnlocked = isStageUnlocked(
              stage.id,
              gates
            );
            const isActive = activeStage === stage.id;
            const isComplete =
              !isActive &&
              isStageComplete(
                stage.id,
                series,
                gates
              );
            const connectorIsComplete =
              index <= activeStageIndex ||
              isStageComplete(
                seriesStages[index - 1]?.id,
                series,
                gates
              );

            const marker = isComplete ? (
              <Check aria-hidden className="h-3.5 w-3.5" />
            ) : (
              index + 1
            );

            return (
              <li className="flex shrink-0 items-center" key={stage.id}>
                {index > 0 ? (
                  <span
                    aria-hidden
                    className={[
                      "mx-1 h-0.5 w-4 rounded-streamly-pill 2xl:mx-2.5 2xl:w-9",
                      connectorIsComplete ? "bg-streamly-electric" : "bg-streamly-lavenderStrong"
                    ].join(" ")}
                  />
                ) : null}
                {isUnlocked ? (
                  <Link
                    aria-current={isActive ? "step" : undefined}
                    className={[
                      "group inline-flex items-center gap-1.5 rounded-streamly-pill text-xs font-extrabold transition duration-200 2xl:gap-2 2xl:text-sm",
                      isActive
                        ? "bg-streamly-electric/12 px-2 py-2 text-streamly-electric ring-1 ring-streamly-electric/45 shadow-streamly-card"
                        : "text-streamly-coal hover:text-streamly-electric"
                    ].join(" ")}
                    to={`/series/${series.id}/${stage.id}`}
                  >
                    <span
                      className={[
                        "grid h-7 w-7 shrink-0 place-items-center rounded-streamly-pill text-xs shadow-streamly-card",
                        isActive
                          ? "bg-streamly-electric text-white shadow-streamly-glow ring-2 ring-white"
                          : isComplete
                            ? "bg-streamly-electric text-white"
                            : "bg-streamly-lavender text-streamly-purpleBlue"
                      ].join(" ")}
                    >
                      {marker}
                    </span>
                    <span className="whitespace-nowrap">{stage.label}</span>
                  </Link>
                ) : (
                  <div className="inline-flex items-center gap-1.5 text-xs font-bold text-[var(--streamly-text-muted)] 2xl:gap-2 2xl:text-sm">
                    <span className="grid h-7 w-7 shrink-0 place-items-center rounded-streamly-pill bg-streamly-wash text-xs text-streamly-purpleBlue">
                      {index + 1}
                    </span>
                    <span className="whitespace-nowrap">{stage.label}</span>
                    <Lock aria-label={`${stage.label} locked`} className="h-3.5 w-3.5" />
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      </div>
    </nav>
  );
}
