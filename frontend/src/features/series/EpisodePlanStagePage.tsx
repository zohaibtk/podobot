import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  LockKeyhole,
  Pencil,
  Plus,
  Sparkles,
  Trash2
} from "lucide-react";
import { useMemo, useState } from "react";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { PersonaPicker } from "@/features/profiles/PersonaPicker";
import { EpisodeEditorModal } from "@/features/series/EpisodeEditorModal";
import { LockPlanModal } from "@/features/series/LockPlanModal";
import { StageHeaderNextButton } from "@/features/series/StageHeaderNextButton";
import {
  useAddEpisode,
  useAssignEpisodeProfiles,
  useEpisodePlan,
  useGenerateEpisodeDraft,
  useLockEpisodePlan,
  useRemoveEpisode,
  useReorderEpisodes,
  useUpdateEpisode
} from "@/features/series/hooks";
import type {
  Episode,
  EpisodeAssignmentPayload,
  EpisodeDraftPayload,
  ProfileKind
} from "@/shared/types/series";

type EditorState =
  | { mode: "add"; episode: null }
  | { mode: "edit"; episode: Episode };

export function EpisodePlanStagePage({ seriesId }: { seriesId: string }) {
  const planQuery = useEpisodePlan(seriesId);
  const addEpisode = useAddEpisode(seriesId);
  const updateEpisode = useUpdateEpisode(seriesId);
  const removeEpisode = useRemoveEpisode(seriesId);
  const reorderEpisodes = useReorderEpisodes(seriesId);
  const assignProfiles = useAssignEpisodeProfiles(seriesId);
  const generateDraft = useGenerateEpisodeDraft(seriesId);
  const lockPlan = useLockEpisodePlan(seriesId);
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [isLockModalOpen, setIsLockModalOpen] = useState(false);

  const mutationError = [
    addEpisode.error,
    updateEpisode.error,
    removeEpisode.error,
    reorderEpisodes.error,
    assignProfiles.error,
    lockPlan.error
  ].find(Boolean);

  if (planQuery.isLoading) {
    return <EpisodePlanSkeleton />;
  }

  if (planQuery.isError || !planQuery.data) {
    return (
      <ErrorState
        actionLabel="Retry"
        description="Episode planning could not be loaded."
        onAction={() => void planQuery.refetch()}
        title="Plan unavailable"
      />
    );
  }

  const plan = planQuery.data;
  const episodes = plan.episodes;
  const isLocked = plan.is_locked;
  const isMutating =
    addEpisode.isPending ||
    updateEpisode.isPending ||
    removeEpisode.isPending ||
    reorderEpisodes.isPending ||
    assignProfiles.isPending ||
    lockPlan.isPending;

  async function submitEpisode(payload: EpisodeDraftPayload) {
    if (!editor) {
      return;
    }

    if (editor.mode === "add") {
      await addEpisode.mutateAsync(payload);
    } else {
      await updateEpisode.mutateAsync({ episodeId: editor.episode.id, payload });
    }
    setEditor(null);
  }

  async function moveEpisode(episodeId: string, direction: "up" | "down") {
    const index = episodes.findIndex((episode) => episode.id === episodeId);
    const nextIndex = direction === "up" ? index - 1 : index + 1;
    if (index < 0 || nextIndex < 0 || nextIndex >= episodes.length) {
      return;
    }

    const nextOrder = episodes.map((episode) => episode.id);
    [nextOrder[index], nextOrder[nextIndex]] = [nextOrder[nextIndex], nextOrder[index]];
    await reorderEpisodes.mutateAsync(nextOrder);
  }

  async function deleteEpisode(episode: Episode) {
    const confirmed = window.confirm(`Remove episode ${episode.episode_number}: ${episode.title}?`);
    if (!confirmed) {
      return;
    }
    await removeEpisode.mutateAsync(episode.id);
  }

  async function assignEpisode(episodeId: string, payload: EpisodeAssignmentPayload) {
    await assignProfiles.mutateAsync({ episodeId, payload });
  }

  async function lockCurrentPlan() {
    await lockPlan.mutateAsync();
    setIsLockModalOpen(false);
  }

  return (
    <main className="space-y-5">
      <div className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge label={isLocked ? "locked" : "editable"} tone={isLocked ? "complete" : "planning"} />
              <StatusBadge
                label={`${plan.outlines.length} outline${plan.outlines.length === 1 ? "" : "s"}`}
                tone={plan.outlines.length ? "generated" : "neutral"}
              />
            </div>
            <h2 className="mt-3 font-streamly-platform text-2xl font-extrabold text-streamly-coal">
              Episode plan
            </h2>
            <p className="mt-2 max-w-3xl font-streamly-body text-sm leading-6 text-streamly-purpleBlue">
              Shape the model-generated arc into a producer-approved plan before production begins.
            </p>
          </div>

          <div className="flex w-full flex-wrap justify-end gap-3 sm:w-auto">
            {!isLocked ? (
              <>
                <button
                  className="inline-flex items-center gap-2 rounded-streamly-pill bg-white px-4 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-wash disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={isMutating}
                  onClick={() => setEditor({ mode: "add", episode: null })}
                  type="button"
                >
                  <Plus aria-hidden className="h-4 w-4" />
                  Add episode
                </button>
                <button
                  className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-coal px-4 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={!plan.lock_readiness.is_ready || isMutating}
                  onClick={() => setIsLockModalOpen(true)}
                  type="button"
                >
                  <LockKeyhole aria-hidden className="h-4 w-4" />
                  Lock plan
                </button>
              </>
            ) : null}
            <StageHeaderNextButton
              disabled={!isLocked}
              disabledTitle="Lock the plan before moving to Outlines."
              nextStage="outlines"
              seriesId={seriesId}
            />
          </div>
        </div>
      </div>

      <section className="space-y-3">
        {mutationError ? (
          <ErrorState
            description={errorMessage(mutationError)}
            title="Episode plan action failed"
          />
        ) : null}

        {episodes.length ? (
          episodes.map((episode, index) => (
            <EpisodeCard
              episode={episode}
              isAssigning={assignProfiles.isPending}
              isLocked={isLocked}
              isMutating={isMutating}
              key={episode.id}
              onAssign={assignEpisode}
              onDelete={deleteEpisode}
              onEdit={(selectedEpisode) =>
                setEditor({ mode: "edit", episode: selectedEpisode })
              }
              onMove={moveEpisode}
              totalEpisodes={episodes.length}
              visualIndex={index}
            />
          ))
        ) : (
          <div className="space-y-3">
            <EmptyState
              description="The generated plan has been fully cleared. Add a curated episode to continue toward lock."
              title="No episodes in the plan"
            />
            {!isLocked ? (
              <button
                className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-electric px-4 py-2 text-sm font-extrabold text-white shadow-streamly-button"
                onClick={() => setEditor({ mode: "add", episode: null })}
                type="button"
              >
                <Plus aria-hidden className="h-4 w-4" />
                Add episode
              </button>
            ) : null}
          </div>
        )}
      </section>

      <EpisodeEditorModal
        episode={editor?.mode === "edit" ? editor.episode : null}
        isGeneratingDraft={generateDraft.isPending}
        isOpen={editor !== null}
        isSubmitting={addEpisode.isPending || updateEpisode.isPending}
        mode={editor?.mode ?? "add"}
        onClose={() => setEditor(null)}
        onGenerateDraft={(payload) =>
          generateDraft.mutateAsync({
            ...payload,
            episode_id: editor?.mode === "edit" ? editor.episode.id : null
          })
        }
        onSubmit={submitEpisode}
      />

      <LockPlanModal
        episodeCount={episodes.length}
        isOpen={isLockModalOpen}
        isSubmitting={lockPlan.isPending}
        onClose={() => setIsLockModalOpen(false)}
        onConfirm={() => void lockCurrentPlan()}
        readiness={plan.lock_readiness}
      />
    </main>
  );
}

function EpisodeCard({
  episode,
  isAssigning,
  isLocked,
  isMutating,
  onAssign,
  onDelete,
  onEdit,
  onMove,
  totalEpisodes,
  visualIndex
}: {
  episode: Episode;
  isAssigning: boolean;
  isLocked: boolean;
  isMutating: boolean;
  onAssign: (episodeId: string, payload: EpisodeAssignmentPayload) => Promise<void>;
  onDelete: (episode: Episode) => Promise<void>;
  onEdit: (episode: Episode) => void;
  onMove: (episodeId: string, direction: "up" | "down") => Promise<void>;
  totalEpisodes: number;
  visualIndex: number;
}) {
  const isReadOnly = isLocked || !episode.can_edit;
  const hostRequirement = useMemo(
    () => personaRequirementForEpisode(episode, "host"),
    [episode]
  );
  const guestRequirement = useMemo(
    () => personaRequirementForEpisode(episode, "guest"),
    [episode]
  );

  return (
    <article className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
      <div className="grid gap-4 lg:grid-cols-[4.5rem_minmax(0,1fr)_12rem]">
        <div className="flex lg:block">
          <div className="grid h-14 w-14 place-items-center rounded-streamly-lg bg-streamly-lavender font-streamly-platform text-xl font-extrabold text-streamly-electric">
            {episode.episode_number}
          </div>
          <div className="ml-3 flex gap-1 lg:ml-0 lg:mt-3">
            <button
              aria-label={`Move episode ${episode.episode_number} up`}
              className="grid h-8 w-8 place-items-center rounded-streamly-pill text-streamly-purpleBlue hover:bg-streamly-wash disabled:cursor-not-allowed disabled:opacity-35"
              disabled={isReadOnly || visualIndex === 0 || isMutating}
              onClick={() => void onMove(episode.id, "up")}
              title="Move up"
              type="button"
            >
              <ArrowUp aria-hidden className="h-4 w-4" />
            </button>
            <button
              aria-label={`Move episode ${episode.episode_number} down`}
              className="grid h-8 w-8 place-items-center rounded-streamly-pill text-streamly-purpleBlue hover:bg-streamly-wash disabled:cursor-not-allowed disabled:opacity-35"
              disabled={isReadOnly || visualIndex === totalEpisodes - 1 || isMutating}
              onClick={() => void onMove(episode.id, "down")}
              title="Move down"
              type="button"
            >
              <ArrowDown aria-hidden className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge label={episode.status} tone={episode.status} />
            {episode.missing_assignments.length ? (
              <span className="inline-flex items-center gap-1 rounded-streamly-pill bg-red-50 px-2.5 py-1 text-xs font-extrabold text-red-700">
                <AlertTriangle aria-hidden className="h-3.5 w-3.5" />
                Missing {episode.missing_assignments.join(", ")}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-streamly-pill bg-emerald-50 px-2.5 py-1 text-xs font-extrabold text-emerald-700">
                <CheckCircle2 aria-hidden className="h-3.5 w-3.5" />
                Ready
              </span>
            )}
          </div>
          <h3 className="mt-3 font-streamly-platform text-lg font-extrabold text-streamly-coal">
            {episode.title}
          </h3>
          <p className="mt-2 text-sm leading-6 text-streamly-purpleBlue">{episode.premise}</p>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <PersonaPicker
                context={{ type: "episode", seriesId: episode.series_id, episodeId: episode.id }}
                disabled={isReadOnly || isAssigning}
                excludedProfileId={episode.guest_profile_id}
                kind="host"
                label="Host"
                onSelect={(profile) =>
                  onAssign(episode.id, { host_profile_id: profile?.id ?? null })
                }
                placeholder="Select host"
                selectedLabel={episode.host_profile_name}
                value={episode.host_profile_id}
              />
              <PersonaSuggestionStrip
                kind="host"
                requirement={hostRequirement}
                selectedProfileName={episode.host_profile_name}
              />
            </div>
            <div className="space-y-2">
              <PersonaPicker
                context={{ type: "episode", seriesId: episode.series_id, episodeId: episode.id }}
                disabled={isReadOnly || isAssigning}
                excludedProfileId={episode.host_profile_id}
                kind="guest"
                label="Guest profile"
                placeholder="Select guest"
                onSelect={(profile) =>
                  onAssign(episode.id, { guest_profile_id: profile?.id ?? null })
                }
                selectedLabel={episode.guest_profile_name}
                value={episode.guest_profile_id}
              />
              <PersonaSuggestionStrip
                kind="guest"
                requirement={guestRequirement}
                selectedProfileName={episode.guest_profile_name}
              />
            </div>
          </div>
        </div>

        <div className="flex gap-2 lg:flex-col">
          <button
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-streamly-pill bg-streamly-wash px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue hover:bg-streamly-lavender disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isReadOnly || isMutating}
            onClick={() => onEdit(episode)}
            type="button"
          >
            <Pencil aria-hidden className="h-4 w-4" />
            Edit
          </button>
          <button
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-streamly-pill bg-red-50 px-3 py-2 text-sm font-extrabold text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isReadOnly || isMutating}
            onClick={() => void onDelete(episode)}
            type="button"
          >
            <Trash2 aria-hidden className="h-4 w-4" />
            Remove
          </button>
        </div>
      </div>
    </article>
  );
}

type PersonaRequirement = {
  rationale: string;
  title: string;
  traits: string[];
};

function PersonaSuggestionStrip({
  kind,
  requirement,
  selectedProfileName
}: {
  kind: ProfileKind;
  requirement: PersonaRequirement;
  selectedProfileName: string | null;
}) {
  return (
    <div className="min-w-0 rounded-streamly-lg border border-streamly-lavenderStrong/70 bg-white/70 px-3 py-2">
      <div className="flex items-center gap-2 text-[0.68rem] font-extrabold uppercase text-streamly-purpleBlue">
        <Sparkles aria-hidden className="h-3.5 w-3.5 text-streamly-electric" />
        Required {kind === "host" ? "host" : "guest"} persona
      </div>
      <p className="mt-2 text-sm font-extrabold leading-5 text-streamly-coal">
        {requirement.title}
      </p>
      <p className="mt-1 text-xs font-semibold leading-5 text-streamly-purpleBlue">
        {requirement.rationale}
      </p>
      <div className="mt-2 flex min-w-0 flex-wrap gap-2">
        {selectedProfileName ? (
          <span
            className="inline-flex max-w-full items-center gap-1 rounded-streamly-pill bg-emerald-50 px-2.5 py-1 text-xs font-extrabold text-emerald-700"
            title="Current assignment"
          >
            <CheckCircle2 aria-hidden className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">Current: {selectedProfileName}</span>
          </span>
        ) : null}
        {requirement.traits.map((trait) => (
          <span
            className="inline-flex max-w-[13rem] items-center rounded-streamly-pill bg-streamly-wash px-2.5 py-1 text-xs font-extrabold text-streamly-purpleBlue"
            key={trait}
          >
            <span className="truncate">{trait}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function personaRequirementForEpisode(
  episode: Episode,
  kind: ProfileKind
): PersonaRequirement {
  const text = `${episode.title} ${episode.premise}`.toLowerCase();
  const hasAny = (terms: string[]) => terms.some((term) => text.includes(term));

  if (hasAny(["trap", "risk", "cost", "hidden", "mirage", "unchecked"])) {
    return kind === "host"
      ? {
          title: "Skeptical risk-framing host",
          rationale:
            "Needs a host who can challenge vanity metrics, expose tradeoffs, and keep the conversation tied to executive decisions.",
          traits: ["Risk framing", "Cost scrutiny", "Contrarian follow-ups"]
        }
      : {
          title: "AI economics or operations expert",
          rationale:
            "Needs a guest who can explain resource costs, dependency risk, and practical controls from operating experience.",
          traits: ["Cost modeling", "Resource tradeoffs", "Operational realism"]
        };
  }

  if (hasAny(["presentation", "client", "skills", "coaching", "mastering"])) {
    return kind === "host"
      ? {
          title: "Practical coaching host",
          rationale:
            "Needs a host who can turn the lesson into repeatable tactics and keep the episode useful for day-to-day execution.",
          traits: ["Actionable coaching", "Clear structure", "Audience empathy"]
        }
      : {
          title: "Client success or communication practitioner",
          rationale:
            "Needs a guest who can ground the episode in presentation craft, stakeholder trust, and real client moments.",
          traits: ["Presentation craft", "Client trust", "Practical examples"]
        };
  }

  if (hasAny(["excellence", "achievement", "journey", "honor", "standard", "success"])) {
    return kind === "host"
      ? {
          title: "Human-story narrative host",
          rationale:
            "Needs a host who can make the achievement feel personal while connecting it back to the organization-wide lesson.",
          traits: ["Warm pacing", "Achievement framing", "Emotional clarity"]
        }
      : {
          title: "Culture and leadership storyteller",
          rationale:
            "Needs a guest who can speak to standards of excellence, recognition, and what the story signals for teams.",
          traits: ["Leadership signal", "Culture context", "Personal insight"]
        };
  }

  if (hasAny(["playbook", "operator", "implementation", "workflow", "process"])) {
    return kind === "host"
      ? {
          title: "Operator-playbook host",
          rationale:
            "Needs a host who can sequence the conversation into choices, steps, and operating implications.",
          traits: ["Process clarity", "Decision sequence", "Execution focus"]
        }
      : {
          title: "Hands-on operator or implementation lead",
          rationale:
            "Needs a guest who can pressure-test the idea against workflow reality and team constraints.",
          traits: ["Workflow detail", "Team constraints", "Implementation lessons"]
        };
  }

  if (hasAny(["future", "market", "wins", "trend", "strategy"])) {
    return kind === "host"
      ? {
          title: "Strategic market-framing host",
          rationale:
            "Needs a host who can connect evidence to market movement and keep the stakes clear for the audience.",
          traits: ["Market framing", "Strategic stakes", "Signal synthesis"]
        }
      : {
          title: "Market analyst or strategic advisor",
          rationale:
            "Needs a guest who can compare signals, name who benefits, and explain what would change the conclusion.",
          traits: ["Trend analysis", "Audience impact", "Strategic comparison"]
        };
  }

  return kind === "host"
    ? {
        title: "Editorial decision-framing host",
        rationale:
          "Needs a host who can clarify the central question, surface choices, and keep the episode moving toward a useful takeaway.",
        traits: ["Decision framing", "Evidence synthesis", "Tight transitions"]
      }
    : {
        title: "Domain expert with applied examples",
        rationale:
          "Needs a guest who can bring credible examples, explain the tradeoffs, and make the topic concrete for the audience.",
        traits: ["Domain credibility", "Applied examples", "Tradeoff clarity"]
      };
}

function EpisodePlanSkeleton() {
  return (
    <main className="space-y-4">
      <div className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <div className="h-5 w-40 animate-pulse rounded-streamly-pill bg-streamly-lavender" />
        <div className="mt-4 h-8 w-72 animate-pulse rounded-streamly-md bg-streamly-wash" />
        <div className="mt-3 h-4 w-full max-w-2xl animate-pulse rounded-streamly-pill bg-streamly-wash" />
      </div>
      {[0, 1, 2].map((item) => (
        <div
          className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card"
          key={item}
        >
          <div className="grid gap-4 lg:grid-cols-[4.5rem_minmax(0,1fr)_12rem]">
            <div className="h-14 w-14 animate-pulse rounded-streamly-lg bg-streamly-lavender" />
            <div className="space-y-3">
              <div className="h-5 w-24 animate-pulse rounded-streamly-pill bg-streamly-lavender" />
              <div className="h-6 w-2/3 animate-pulse rounded-streamly-md bg-streamly-wash" />
              <div className="h-4 w-full animate-pulse rounded-streamly-pill bg-streamly-wash" />
              <div className="grid gap-3 md:grid-cols-2">
                <div className="h-20 animate-pulse rounded-streamly-lg bg-streamly-wash" />
                <div className="h-20 animate-pulse rounded-streamly-lg bg-streamly-wash" />
              </div>
            </div>
            <div className="h-20 animate-pulse rounded-streamly-lg bg-streamly-wash" />
          </div>
        </div>
      ))}
    </main>
  );
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "The request could not be completed.";
}
