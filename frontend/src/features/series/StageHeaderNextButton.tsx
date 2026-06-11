import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

import { seriesStageLabel } from "@/features/series/stageProgress";
import type { SeriesStageId } from "@/routes/routeRegistry";

type StageHeaderNextButtonProps = {
  disabled?: boolean;
  disabledTitle?: string;
  nextStage: SeriesStageId;
  seriesId: string;
};

export function StageHeaderNextButton({
  disabled = false,
  disabledTitle,
  nextStage,
  seriesId
}: StageHeaderNextButtonProps) {
  const label = `Next: ${seriesStageLabel(nextStage)}`;
  const className =
    "streamly-button-primary w-full justify-center whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto";

  if (disabled) {
    return (
      <button className={className} disabled title={disabledTitle} type="button">
        {label}
        <ArrowRight aria-hidden className="h-4 w-4" />
      </button>
    );
  }

  return (
    <Link className={className} to={`/series/${seriesId}/${nextStage}`}>
      {label}
      <ArrowRight aria-hidden className="h-4 w-4" />
    </Link>
  );
}
