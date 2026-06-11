import { useEffect, useRef, type RefObject } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, CheckCircle2, Lock } from "lucide-react";

import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { seriesStages, type SeriesStageId } from "@/routes/routeRegistry";
import { BriefsStagePage } from "@/features/series/BriefsStagePage";
import { CaptionsStagePage } from "@/features/series/CaptionsStagePage";
import { DiscoveryStagePage } from "@/features/series/DiscoveryStagePage";
import { EpisodePlanStagePage } from "@/features/series/EpisodePlanStagePage";
import { NarrativeStagePage } from "@/features/series/NarrativeStagePage";
import { OutlineStagePage } from "@/features/series/OutlineStagePage";
import { RecordingsStagePage } from "@/features/series/RecordingsStagePage";
import { SchedulingStagePage } from "@/features/series/SchedulingStagePage";
import {
  useDiscoveryWorkspace,
  useOutlineWorkspace,
  useRecordingWorkspace,
  useSeries
} from "@/features/series/hooks";
import { SeriesStageRail } from "@/features/series/SeriesStageRail";
import {
  currentSeriesStage,
  isSeriesStage,
  isStageComplete,
  isStageUnlocked,
  nextSeriesStage,
  type SeriesStageGates
} from "@/features/series/stageProgress";
import type { Series } from "@/shared/types/series";

export function SeriesDetailShell() {
  const nextStageFooterRef = useRef<HTMLDivElement>(null);
  const lastAdvanceKeyRef = useRef<string | null>(null);
  const lastStageKeyRef = useRef<string | null>(null);
  const hasTrackedAdvanceRef = useRef(false);
  const { seriesId, stage } = useParams();
  const requestedStage = isSeriesStage(stage) ? stage : null;
  const { data: series, isLoading, isError, refetch } = useSeries(seriesId);
  const {
    data: discoveryWorkspace,
    isLoading: isDiscoveryLoading
  } = useDiscoveryWorkspace(seriesId);
  const {
    data: outlineWorkspace,
    isLoading: isOutlineLoading
  } = useOutlineWorkspace(
    seriesId,
    requestedStage === "outlines" && Boolean(series?.plan_locked_at)
  );
  const shouldUseRecordingGate =
    requestedStage === "recordings" && Boolean(series?.briefs_approved_at);
  const {
    data: recordingWorkspace,
    isLoading: isRecordingLoading
  } = useRecordingWorkspace(seriesId, shouldUseRecordingGate);

  const hasSelectedNarrative = Boolean(discoveryWorkspace?.selected_narrative_id);
  const hasDiscoveryRun = Boolean(
    series &&
      (series.discovery_status === "complete" ||
        discoveryWorkspace?.ledger.length ||
        hasSelectedNarrative)
  );
  const hasLockedPlan = Boolean(series?.plan_locked_at);
  const hasApprovedOutline = Boolean(
    outlineWorkspace?.readiness.approved_outline_count
  );
  const hasApprovedBriefs = Boolean(series?.briefs_approved_at);
  const hasTranscriptForCaptions = shouldUseRecordingGate
    ? Boolean(recordingWorkspace?.readiness.captions_unlocked)
    : Boolean(series?.captions_unlocked_at);
  const hasCaptionsReadyForScheduling = Boolean(series?.scheduling_unlocked_at);
  const gates: SeriesStageGates = {
    hasApprovedBriefs,
    hasApprovedOutline,
    hasCaptionsReadyForScheduling,
    hasDiscoveryRun,
    hasLockedPlan,
    hasSelectedNarrative,
    hasTranscriptForCaptions
  };
  const nextStageForScroll = requestedStage ? nextSeriesStage(requestedStage) : null;
  const canTrackAdvance = Boolean(
    series &&
      requestedStage &&
      !isLoading &&
      !isDiscoveryLoading &&
      (requestedStage !== "outlines" || !isOutlineLoading) &&
      (requestedStage !== "recordings" || !isRecordingLoading)
  );
  const stageKey = series && requestedStage ? `${series.id}:${requestedStage}` : null;
  const advanceKey =
    series && requestedStage && nextStageForScroll &&
    isStageComplete(requestedStage, series, gates) &&
    isStageUnlocked(nextStageForScroll.id, gates)
      ? `${series.id}:${requestedStage}:${nextStageForScroll.id}`
      : null;

  useEffect(() => {
    if (!canTrackAdvance) {
      return;
    }

    if (!hasTrackedAdvanceRef.current || lastStageKeyRef.current !== stageKey) {
      hasTrackedAdvanceRef.current = true;
      lastStageKeyRef.current = stageKey;
      lastAdvanceKeyRef.current = advanceKey;
      return;
    }

    if (!advanceKey || lastAdvanceKeyRef.current === advanceKey) {
      lastAdvanceKeyRef.current = advanceKey;
      return;
    }

    lastAdvanceKeyRef.current = advanceKey;
    const frame = window.requestAnimationFrame(() => {
      const prefersReducedMotion =
        typeof window.matchMedia === "function" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      nextStageFooterRef.current?.scrollIntoView({
        behavior: prefersReducedMotion ? "auto" : "smooth",
        block: "center"
      });
    });

    return () => window.cancelAnimationFrame(frame);
  }, [advanceKey, canTrackAdvance, stageKey]);

  if (!seriesId) {
    return <Navigate replace to="/series" />;
  }

  if (isLoading) {
    return <LoadingState label="Loading series workspace" />;
  }

  if (isError || !series) {
    return (
      <ErrorState
        actionLabel="Retry"
        description="The series workspace could not be loaded."
        onAction={() => void refetch()}
        title="Series unavailable"
      />
    );
  }

  const fallbackStage = currentSeriesStage(series);
  if (!requestedStage) {
    return <Navigate replace to={`/series/${series.id}/${fallbackStage}`} />;
  }

  const normalizedStage = requestedStage;
  const isDiscoveryStage = normalizedStage === "discovery";
  const isNarrativeStage = normalizedStage === "narrative";
  const isPlanStage = normalizedStage === "plan";
  const isOutlineStage = normalizedStage === "outlines";
  const isBriefStage = normalizedStage === "briefs";
  const isRecordingStage = normalizedStage === "recordings";
  const isCaptionStage = normalizedStage === "captions";
  const isScheduleStage = normalizedStage === "schedule";

  return (
    <section className="streamly-page gap-4">
      <div className="streamly-page-hero streamly-page-header overflow-hidden">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1 max-w-4xl">
            <Link
              className="inline-flex items-center gap-2 rounded-streamly-pill bg-white px-3 py-1.5 text-xs font-extrabold text-streamly-purpleBlue shadow-streamly-card transition hover:-translate-y-0.5 hover:bg-streamly-wash hover:text-streamly-electric"
              to="/series"
            >
              <ArrowLeft aria-hidden className="h-3.5 w-3.5" />
              Series workspace
            </Link>
            <p className="streamly-kicker mt-4">Editorial production</p>
            <h1 className="streamly-page-heading">{series.name}</h1>
            <p className="streamly-page-description">{series.description}</p>
          </div>
        </div>

        <div className="mt-5 grid gap-2 md:grid-cols-3">
          <WorkspaceSignal label="Audience" value={series.audience} />
          <WorkspaceSignal
            label="Narrative"
            value={hasSelectedNarrative ? "Selected" : "Awaiting selection"}
          />
          <WorkspaceSignal
            label="Production gate"
            value={
              hasCaptionsReadyForScheduling
                ? "Scheduling ready"
                : hasTranscriptForCaptions
                  ? "Captions ready"
                  : hasApprovedBriefs
                    ? "Recording ready"
                    : hasLockedPlan
                      ? "Briefs ready"
                      : hasSelectedNarrative
                        ? "Planning ready"
                        : "Discovery active"
            }
          />
        </div>
      </div>

      <SeriesStageRail
        activeStage={normalizedStage}
        hasApprovedBriefs={hasApprovedBriefs}
        hasApprovedOutline={hasApprovedOutline}
        hasDiscoveryRun={hasDiscoveryRun}
        hasLockedPlan={hasLockedPlan}
        hasSelectedNarrative={hasSelectedNarrative}
        hasCaptionsReadyForScheduling={hasCaptionsReadyForScheduling}
        hasTranscriptForCaptions={hasTranscriptForCaptions}
        series={series}
      />

      <div className="min-w-0">
        {isDiscoveryStage ? (
          <DiscoveryStagePage seriesId={series.id} />
        ) : isNarrativeStage && hasDiscoveryRun ? (
          <NarrativeStagePage seriesId={series.id} />
        ) : isPlanStage && hasSelectedNarrative ? (
          <EpisodePlanStagePage seriesId={series.id} />
        ) : isOutlineStage && hasLockedPlan ? (
          <OutlineStagePage seriesId={series.id} />
        ) : isBriefStage && hasLockedPlan ? (
          <BriefsStagePage seriesId={series.id} />
        ) : isRecordingStage && hasApprovedBriefs ? (
          <RecordingsStagePage seriesId={series.id} />
        ) : isCaptionStage && hasTranscriptForCaptions ? (
          <CaptionsStagePage seriesId={series.id} />
        ) : isScheduleStage && hasCaptionsReadyForScheduling ? (
          <SchedulingStagePage seriesId={series.id} />
        ) : (
          <LaterStagePanel
            hasApprovedBriefs={hasApprovedBriefs}
            hasCaptionsReadyForScheduling={hasCaptionsReadyForScheduling}
            hasDiscoveryRun={hasDiscoveryRun}
            hasLockedPlan={hasLockedPlan}
            hasSelectedNarrative={hasSelectedNarrative}
            hasTranscriptForCaptions={hasTranscriptForCaptions}
            stage={normalizedStage}
          />
        )}
      </div>

      <NextStageFooter
        activeStage={normalizedStage}
        footerRef={nextStageFooterRef}
        gates={gates}
        series={series}
      />
    </section>
  );
}

function WorkspaceSignal({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-streamly-card bg-white/72 px-3 py-2.5 shadow-streamly-card backdrop-blur">
      <p className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-streamly-purpleBlue">
        {label}
      </p>
      <p className="mt-0.5 line-clamp-1 text-sm font-extrabold text-streamly-coal">
        {value}
      </p>
    </div>
  );
}

function NextStageFooter({
  activeStage,
  footerRef,
  gates,
  series
}: {
  activeStage: SeriesStageId;
  footerRef: RefObject<HTMLDivElement>;
  gates: SeriesStageGates;
  series: Series;
}) {
  const nextStage = nextSeriesStage(activeStage);
  if (
    !nextStage ||
    !isStageComplete(activeStage, series, gates) ||
    !isStageUnlocked(nextStage.id, gates)
  ) {
    return null;
  }

  return (
    <div className="flex justify-end" ref={footerRef}>
      <Link
        className="inline-flex min-h-12 items-center gap-3 rounded-streamly-pill bg-streamly-electric px-5 py-3 text-sm font-extrabold text-white shadow-streamly-button transition hover:-translate-y-0.5 hover:bg-streamly-violet"
        to={`/series/${series.id}/${nextStage.id}`}
      >
        Next: {nextStage.label}
        <ArrowRight aria-hidden className="h-4 w-4" />
      </Link>
    </div>
  );
}

function LaterStagePanel({
  hasApprovedBriefs,
  hasCaptionsReadyForScheduling,
  hasDiscoveryRun,
  hasLockedPlan,
  hasSelectedNarrative,
  hasTranscriptForCaptions,
  stage
}: {
  hasApprovedBriefs: boolean;
  hasCaptionsReadyForScheduling: boolean;
  hasDiscoveryRun: boolean;
  hasLockedPlan: boolean;
  hasSelectedNarrative: boolean;
  hasTranscriptForCaptions: boolean;
  stage: SeriesStageId;
}) {
  const label = seriesStages.find((item) => item.id === stage)?.label ?? "Stage";
  const isNarrativeStage = stage === "narrative";
  const isRecordingStage = stage === "recordings";
  const isCaptionStage = stage === "captions";
  const isScheduleStage = stage === "schedule";
  const isUnlocked = isNarrativeStage
    ? hasDiscoveryRun
    : isRecordingStage
    ? hasApprovedBriefs
    : isCaptionStage
      ? hasTranscriptForCaptions
      : isScheduleStage
        ? hasCaptionsReadyForScheduling
        : hasSelectedNarrative && hasLockedPlan;
  const title = isNarrativeStage && !hasDiscoveryRun
    ? "Run discovery to unlock Narrative"
    : !hasSelectedNarrative
    ? "Select a narrative to unlock"
    : isRecordingStage && hasApprovedBriefs
      ? "Recordings unlocked"
      : isRecordingStage
        ? "Approve a brief pair to unlock"
        : isCaptionStage && hasTranscriptForCaptions
          ? "Captions unlocked"
          : isCaptionStage
            ? "Complete recordings to unlock"
            : isScheduleStage && hasCaptionsReadyForScheduling
              ? "Scheduling unlocked"
              : isScheduleStage
                ? "Generate a caption to unlock"
                : hasLockedPlan
                  ? "Stage unlocked"
                  : "Lock the episode plan to unlock";
  const description = isNarrativeStage && !hasDiscoveryRun
    ? "Narrative options stay locked until Discovery has run and produced the evidence base for this series."
    : !hasSelectedNarrative
    ? "Later production stages remain locked until exactly one narrative direction is selected from the Narrative stage."
    : isRecordingStage && hasApprovedBriefs
      ? "At least one approved brief pair is ready for recording intake."
      : isRecordingStage
        ? "Recordings stay gated until a host and guest brief pair is approved together."
        : isCaptionStage && hasTranscriptForCaptions
          ? "Every required recording has video and transcript attached. Captions are ready for production."
          : isCaptionStage
            ? "Captions stay gated until every required recording has both video and transcript."
            : isScheduleStage && hasCaptionsReadyForScheduling
              ? "At least one platform caption is ready. Buffer scheduling is available for captioned rows."
              : isScheduleStage
                ? "Scheduling remains gated until at least one platform caption is ready."
                : hasLockedPlan
                  ? "The episode plan is locked and outlines are ready for editorial review."
                  : "Production stages remain gated until the producer locks the episode plan and outlines are created.";

  return (
    <main className="streamly-panel p-7">
      <div className="flex flex-col items-start gap-5 md:flex-row">
        <div
          className={[
            "grid h-14 w-14 place-items-center rounded-streamly-pill shadow-streamly-card",
            isUnlocked
              ? "bg-emerald-50 text-emerald-700"
              : "bg-streamly-lavender text-streamly-electric"
          ].join(" ")}
        >
          {isUnlocked ? (
            <CheckCircle2 aria-hidden className="h-5 w-5" />
          ) : (
            <Lock aria-hidden className="h-5 w-5" />
          )}
        </div>
        <div className="max-w-2xl">
          <p className="streamly-kicker">
            {label}
          </p>
          <h2 className="mt-2 font-streamly-platform text-2xl font-extrabold text-streamly-coal">
            {title}
          </h2>
          <p className="mt-3 font-streamly-body text-sm leading-6 text-streamly-purpleBlue">
            {description}
          </p>
        </div>
      </div>
    </main>
  );
}
