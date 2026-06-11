import { seriesStages, type SeriesStageId } from "@/routes/routeRegistry";
import type { Series } from "@/shared/types/series";

export type SeriesStageGates = {
  hasApprovedBriefs: boolean;
  hasApprovedOutline: boolean;
  hasCaptionsReadyForScheduling: boolean;
  hasDiscoveryRun: boolean;
  hasLockedPlan: boolean;
  hasSelectedNarrative: boolean;
  hasTranscriptForCaptions: boolean;
};

export function currentSeriesStage(series: Series): SeriesStageId {
  const storedStage = isSeriesStage(series.current_stage) ? series.current_stage : "discovery";
  const unlockedStage = furthestUnlockedStage(series);
  return stageIndex(unlockedStage) > stageIndex(storedStage) ? unlockedStage : storedStage;
}

export function isSeriesStage(value: string | undefined): value is SeriesStageId {
  return Boolean(value && seriesStages.some((stage) => stage.id === value));
}

export function seriesStageLabel(stageId: SeriesStageId) {
  return seriesStages.find((stage) => stage.id === stageId)?.label ?? "Stage";
}

export function nextSeriesStage(stageId: SeriesStageId) {
  const nextIndex = stageIndex(stageId) + 1;
  return seriesStages[nextIndex] ?? null;
}

export function isStageComplete(
  stageId: SeriesStageId | undefined,
  series: Series,
  gates: SeriesStageGates
) {
  if (!stageId) {
    return false;
  }
  if (stageId === "discovery") {
    return series.discovery_status === "complete" || gates.hasSelectedNarrative;
  }
  if (stageId === "narrative") {
    return gates.hasSelectedNarrative;
  }
  if (stageId === "plan") {
    return gates.hasLockedPlan;
  }
  if (stageId === "outlines") {
    return gates.hasApprovedOutline || stageIndex(currentSeriesStage(series)) > stageIndex("outlines");
  }
  if (stageId === "briefs") {
    return gates.hasApprovedBriefs;
  }
  if (stageId === "recordings") {
    return gates.hasTranscriptForCaptions;
  }
  if (stageId === "captions") {
    return gates.hasCaptionsReadyForScheduling;
  }
  if (stageId === "schedule") {
    return series.status === "complete" || series.status === "partially_published";
  }
  return false;
}

export function isStageUnlocked(stageId: SeriesStageId, gates: SeriesStageGates) {
  if (stageId === "discovery") {
    return true;
  }
  if (stageId === "narrative") {
    return gates.hasDiscoveryRun;
  }
  if (stageId === "plan") {
    return gates.hasSelectedNarrative;
  }
  if (stageId === "outlines" || stageId === "briefs") {
    return gates.hasLockedPlan;
  }
  if (stageId === "recordings") {
    return gates.hasApprovedBriefs;
  }
  if (stageId === "captions") {
    return gates.hasTranscriptForCaptions;
  }
  if (stageId === "schedule") {
    return gates.hasCaptionsReadyForScheduling;
  }
  return false;
}

function stageIndex(stageId: SeriesStageId) {
  return Math.max(0, seriesStages.findIndex((stage) => stage.id === stageId));
}

function furthestUnlockedStage(series: Series): SeriesStageId {
  if (series.scheduling_unlocked_at) {
    return "schedule";
  }
  if (series.captions_unlocked_at) {
    return "captions";
  }
  if (series.briefs_approved_at) {
    return "recordings";
  }
  if (series.plan_locked_at) {
    return "outlines";
  }
  return "discovery";
}
