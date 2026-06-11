import { FileText, Loader2, RefreshCw, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { Modal } from "@/design-system/components/Modal";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import {
  useDiscoveryWorkspace,
  useRegenerateNarratives,
  useSelectNarrative
} from "@/features/series/hooks";
import { StageHeaderNextButton } from "@/features/series/StageHeaderNextButton";
import type { Narrative, SupportingSignal } from "@/shared/types/series";

type NarrativeStagePageProps = {
  seriesId: string;
};

export function NarrativeStagePage({ seriesId }: NarrativeStagePageProps) {
  const { data, isLoading, isError, refetch } = useDiscoveryWorkspace(seriesId);
  const regenerate = useRegenerateNarratives(seriesId);
  const select = useSelectNarrative(seriesId);
  const [ledgerNarrative, setLedgerNarrative] = useState<Narrative | null>(null);
  const [optimisticSelectedNarrativeId, setOptimisticSelectedNarrativeId] = useState<
    string | null
  >(null);
  const [selectingNarrativeId, setSelectingNarrativeId] = useState<string | null>(null);
  const [narrativeOrder, setNarrativeOrder] = useState<string[]>([]);
  const narrativeIdKey = data?.narratives.map((narrative) => narrative.id).join("|") ?? "";
  const selectedNarrativeId = optimisticSelectedNarrativeId ?? data?.selected_narrative_id ?? null;

  useEffect(() => {
    if (
      optimisticSelectedNarrativeId &&
      data?.selected_narrative_id === optimisticSelectedNarrativeId
    ) {
      setOptimisticSelectedNarrativeId(null);
    }
  }, [data?.selected_narrative_id, optimisticSelectedNarrativeId]);

  useEffect(() => {
    if (!data) {
      setNarrativeOrder([]);
      return;
    }

    setNarrativeOrder((currentOrder) => {
      const visibleIds = data.narratives.map((narrative) => narrative.id);
      const visibleIdSet = new Set(visibleIds);
      const retainedIds = currentOrder.filter((id) => visibleIdSet.has(id));
      const addedIds = visibleIds.filter((id) => !retainedIds.includes(id));
      const nextOrder = [...retainedIds, ...addedIds];

      return nextOrder.length === currentOrder.length &&
        nextOrder.every((id, index) => id === currentOrder[index])
        ? currentOrder
        : nextOrder;
    });
  }, [data, narrativeIdKey]);

  const orderedNarratives = useMemo(() => {
    if (!data) {
      return [];
    }

    const orderIndex = new Map(narrativeOrder.map((id, index) => [id, index]));
    return data.narratives
      .map((narrative, index) => ({ narrative, index }))
      .sort((left, right) => {
        const leftOrder = orderIndex.get(left.narrative.id) ?? left.index;
        const rightOrder = orderIndex.get(right.narrative.id) ?? right.index;
        return leftOrder - rightOrder;
      })
      .map(({ narrative }) => narrative);
  }, [data, narrativeOrder]);

  if (isLoading) {
    return <LoadingState label="Loading narrative workspace" />;
  }

  if (isError || !data) {
    return (
      <ErrorState
        actionLabel="Retry"
        description="Narrative options could not be loaded."
        onAction={() => void refetch()}
        title="Narrative unavailable"
      />
    );
  }

  const hasLedger = data.ledger.length > 0;
  const hasNarratives = data.narratives.length > 0;
  const isPlanLocked = Boolean(data.series.plan_locked_at);
  const handleSelectNarrative = (narrativeId: string) => {
    if (select.isPending || isPlanLocked) {
      return;
    }

    setSelectingNarrativeId(narrativeId);
    select.mutate(narrativeId, {
      onSuccess: () => setOptimisticSelectedNarrativeId(narrativeId),
      onSettled: () => setSelectingNarrativeId(null)
    });
  };

  return (
    <div className="space-y-6">
      <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="streamly-kicker">Narrative</p>
            <h2 className="font-streamly-platform text-2xl font-extrabold text-streamly-coal">
              Select the strategic direction
            </h2>
            <p className="mt-2 max-w-2xl font-streamly-body text-sm leading-6 text-streamly-purpleBlue">
              Narrative options are generated from the Discovery source ledger.
              Select exactly one direction before moving into episode planning.
            </p>
          </div>
          <div className="flex w-full flex-wrap justify-end gap-3 sm:w-auto">
            <button
              className="streamly-button-secondary"
              disabled={!hasLedger || regenerate.isPending}
              onClick={() => regenerate.mutate()}
              type="button"
            >
              <RefreshCw aria-hidden className="h-4 w-4" />
              {regenerate.isPending ? "Regenerating..." : "Regenerate"}
            </button>
            <StageHeaderNextButton
              disabled={!selectedNarrativeId}
              disabledTitle="Select a narrative before moving to Plan."
              nextStage="plan"
              seriesId={seriesId}
            />
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          {data.selected_narrative_id ? (
            <StatusBadge label="Narrative selected" tone="complete" />
          ) : (
            <StatusBadge label="Selection required" tone="pending" />
          )}
          <StatusBadge label={`${data.ledger.length} source signal(s)`} tone="neutral" />
          <StatusBadge label={`${data.narratives.length} option(s)`} tone="neutral" />
        </div>
      </section>

      {!hasLedger ? (
        <EmptyState
          description="Run Discovery first to collect source signals. Narrative options are created from that evidence."
          title="Discovery evidence required"
        />
      ) : hasNarratives ? (
        <div className="grid gap-4 xl:grid-cols-3">
          {orderedNarratives.map((narrative) => (
            <NarrativeCard
              key={narrative.id}
              narrative={narrative}
              isPlanLocked={isPlanLocked}
              isSelected={
                selectedNarrativeId
                  ? narrative.id === selectedNarrativeId
                  : narrative.is_selected
              }
              isSelecting={select.isPending && selectingNarrativeId === narrative.id}
              onOpenLedger={() => setLedgerNarrative(narrative)}
              onSelect={() => handleSelectNarrative(narrative.id)}
              selectionLocked={select.isPending}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          description="Regenerate narratives to create strategic options from the existing Discovery ledger."
          title="No narrative options yet"
        />
      )}

      <NarrativeLedgerModal
        narrative={ledgerNarrative}
        onClose={() => setLedgerNarrative(null)}
      />
    </div>
  );
}

function NarrativeCard({
  isPlanLocked,
  isSelected,
  isSelecting,
  narrative,
  onOpenLedger,
  onSelect,
  selectionLocked
}: {
  isPlanLocked: boolean;
  isSelected: boolean;
  isSelecting: boolean;
  narrative: Narrative;
  onOpenLedger: () => void;
  onSelect: () => void;
  selectionLocked: boolean;
}) {
  return (
    <article
      className={[
        "flex min-h-full flex-col rounded-streamly-xl border bg-white p-7 shadow-streamly-card",
        isSelected
          ? "border-streamly-electric ring-4 ring-streamly-electric/15"
          : "border-streamly-lavenderStrong"
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric">
          <Sparkles aria-hidden className="h-4 w-4" />
        </div>
        <div className="flex items-center gap-2">
          <button
            aria-label={`View source ledger for ${narrative.title}`}
            className="grid h-9 w-9 place-items-center rounded-streamly-pill bg-streamly-wash text-streamly-purpleBlue transition hover:-translate-y-0.5 hover:bg-streamly-lavender"
            onClick={onOpenLedger}
            title="View source ledger"
            type="button"
          >
            <FileText aria-hidden className="h-4 w-4" />
          </button>
          {isSelected ? (
            <StatusBadge label="selected" tone="complete" />
          ) : (
            <ConfidenceBadge score={narrative.confidence_score} />
          )}
        </div>
      </div>

      <div className="mt-8 flex flex-1 flex-col">
        <h3 className="font-streamly-platform text-xl font-extrabold leading-tight text-streamly-coal">
          {narrative.title}
        </h3>
        <p className="mt-5 font-streamly-body text-base leading-8 text-streamly-purpleBlue">
          {narrative.summary}
        </p>
        <p className="mt-8 rounded-streamly-lg bg-streamly-wash p-5 text-base font-bold leading-8 text-streamly-coal">
          {narrative.thesis}
        </p>

        <div className="mt-auto pt-8">
          <button
            aria-busy={isSelecting}
            className="streamly-button-primary w-full justify-center disabled:opacity-50"
            disabled={isSelected || selectionLocked || isPlanLocked}
            onClick={onSelect}
            title={
              isPlanLocked && !isSelected
                ? "Narrative selection cannot change after the episode plan is locked."
                : undefined
            }
            type="button"
          >
            {isSelecting ? (
              <>
                <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
                Selecting narrative...
              </>
            ) : isSelected ? (
              "Selected narrative"
            ) : isPlanLocked ? (
              "Plan locked"
            ) : (
              "Select narrative"
            )}
          </button>
        </div>
      </div>
    </article>
  );
}

function ConfidenceBadge({ score }: { score: number }) {
  return (
    <span
      aria-label={`Confidence ${score} percent. Confidence reflects how strongly the source ledger supports this narrative.`}
      className="group relative inline-flex outline-none"
      tabIndex={0}
    >
      <StatusBadge label={`confidence ${score}%`} tone="neutral" />
      <span
        className="pointer-events-none absolute right-0 top-full z-20 mt-2 w-72 rounded-streamly-lg border border-streamly-lavenderStrong bg-white p-3 text-left text-xs font-bold leading-5 text-streamly-purpleBlue opacity-0 shadow-streamly-elevated transition group-hover:opacity-100 group-focus:opacity-100"
        role="tooltip"
      >
        Confidence shows how strongly the source ledger supports this narrative, based on
        evidence quality, signal strength, and source scoring.
      </span>
    </span>
  );
}

function NarrativeLedgerModal({
  narrative,
  onClose
}: {
  narrative: Narrative | null;
  onClose: () => void;
}) {
  return (
    <Modal
      description={narrative ? `Evidence signals supporting “${narrative.title}”.` : undefined}
      isOpen={narrative !== null}
      onClose={onClose}
      title="Source ledger"
    >
      {narrative ? (
        <div className="space-y-3">
          <div className="rounded-streamly-xl bg-streamly-wash p-4">
            <p className="streamly-kicker">Narrative confidence</p>
            <p className="mt-2 font-streamly-platform text-3xl font-extrabold text-streamly-coal">
              {narrative.confidence_score}%
            </p>
          </div>
          {narrative.supporting_signals.length ? (
            narrative.supporting_signals.map((signal) => (
              <LedgerSignalRow
                key={`${narrative.id}-${signal.source_name}-${signal.signal_title}`}
                signal={signal}
              />
            ))
          ) : (
            <div className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 text-sm font-bold text-streamly-purpleBlue">
              No supporting ledger signals were attached to this narrative.
            </div>
          )}
        </div>
      ) : null}
    </Modal>
  );
}

function LedgerSignalRow({ signal }: { signal: SupportingSignal }) {
  return (
    <div className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs font-extrabold uppercase text-streamly-electric">
          {signal.source_name}
        </p>
        <StatusBadge label={`${signal.confidence_score}% confidence`} tone="neutral" />
      </div>
      <p className="mt-2 font-streamly-platform text-base font-extrabold leading-6 text-streamly-coal">
        {signal.signal_title}
      </p>
    </div>
  );
}
