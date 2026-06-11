import { describe, expect, it } from "vitest";

import {
  currentSeriesStage,
  isStageComplete,
  isStageUnlocked,
  nextSeriesStage,
  seriesStageLabel,
  type SeriesStageGates
} from "@/features/series/stageProgress";
import type { Series } from "@/shared/types/series";

describe("stageProgress", () => {
  it("labels and resumes from the saved current stage", () => {
    const series = seriesFixture({ current_stage: "briefs" });

    expect(currentSeriesStage(series)).toBe("briefs");
    expect(seriesStageLabel(currentSeriesStage(series))).toBe("Briefs");
  });

  it("uses later unlock gates when the saved current stage is stale", () => {
    const series = seriesFixture({
      captions_unlocked_at: "2026-06-09T00:00:00Z",
      current_stage: "recordings"
    });

    expect(currentSeriesStage(series)).toBe("captions");
  });

  it("does not mark outlines complete until the series advances beyond outlines", () => {
    const gates = gatesFixture({ hasLockedPlan: true });

    expect(
      isStageComplete("outlines", seriesFixture({ current_stage: "outlines" }), gates)
    ).toBe(false);
    expect(
      isStageComplete("outlines", seriesFixture({ current_stage: "briefs" }), gates)
    ).toBe(true);
    expect(nextSeriesStage("outlines")?.id).toBe("briefs");
  });

  it("marks outlines complete after any outline is approved", () => {
    const gates = gatesFixture({ hasApprovedOutline: true, hasLockedPlan: true });

    expect(
      isStageComplete("outlines", seriesFixture({ current_stage: "outlines" }), gates)
    ).toBe(true);
  });

  it("keeps narrative locked until discovery has run", () => {
    expect(isStageUnlocked("narrative", gatesFixture({ hasDiscoveryRun: false }))).toBe(false);
    expect(isStageUnlocked("narrative", gatesFixture({ hasDiscoveryRun: true }))).toBe(true);
  });
});

function gatesFixture(overrides: Partial<SeriesStageGates> = {}): SeriesStageGates {
  return {
    hasApprovedBriefs: false,
    hasApprovedOutline: false,
    hasCaptionsReadyForScheduling: false,
    hasDiscoveryRun: true,
    hasLockedPlan: false,
    hasSelectedNarrative: true,
    hasTranscriptForCaptions: false,
    ...overrides
  };
}

function seriesFixture(overrides: Partial<Series> = {}): Series {
  return {
    audience: "Operators",
    briefs_approved_at: null,
    captions_unlocked_at: null,
    created_at: "2026-06-09T00:00:00Z",
    current_stage: "discovery",
    description: "A test series.",
    discovery_status: "complete",
    episode_plan_generated_at: null,
    guest_name: null,
    id: "series-1",
    name: "Series",
    plan_locked_at: null,
    scheduling_unlocked_at: null,
    status: "planning",
    updated_at: "2026-06-09T00:00:00Z",
    ...overrides
  };
}
