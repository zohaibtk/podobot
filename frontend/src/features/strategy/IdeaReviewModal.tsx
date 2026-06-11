import type { ReactNode } from "react";
import { CheckCircle2, ExternalLink, Layers3, TrendingUp, Users } from "lucide-react";

import { Modal } from "@/design-system/components/Modal";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import type { StrategyIdea } from "@/shared/types/strategy";

type IdeaReviewModalProps = {
  idea: StrategyIdea | null;
  isOpen: boolean;
  isReviewing: boolean;
  onClose: () => void;
  onMarkReview: (idea: StrategyIdea) => void;
};

export function IdeaReviewModal({
  idea,
  isOpen,
  isReviewing,
  onClose,
  onMarkReview
}: IdeaReviewModalProps) {
  if (!idea) {
    return null;
  }

  const season = idea.season_potential;
  const trend = idea.trend_intelligence;
  const episodePlan = idea.source_proposal.episode_plan ?? [];
  const profileFits = idea.source_proposal.profile_fits;
  const episodeCount =
    idea.potential_episode_count || season.potential_episodes || episodePlan.length || 0;
  const sourceCount = season.research_coverage?.source_count ?? idea.source_count;
  const reviewNotes = [
    idea.audience_intelligence.reason ?? `${idea.audience} is the recommended audience.`,
    season.reason ?? `${episodeCount} episode starting points are available from the scan.`,
    trend.trend_available
      ? `Trend signal is ${trend.velocity_label ?? "available"} at ${trend.current_trend ?? 0}%.`
      : trend.message ?? "Trend signal is not available yet."
  ].filter((note): note is string => Boolean(note));
  const suggestedProfiles = [
    profileFits?.suggested_host?.persona,
    profileFits?.suggested_guest?.persona ?? idea.proposed_guest_name
  ].filter((profile): profile is string => Boolean(profile));

  return (
    <Modal
      description="Confirm whether this opportunity is ready for series production."
      isOpen={isOpen}
      onClose={onClose}
      title="Review opportunity"
    >
      <div className="space-y-2">
        <section className="rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash p-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap gap-2">
                <StatusBadge label={idea.status} tone={idea.status} />
                <span className="rounded-streamly-pill bg-white px-3 py-1 text-xs font-extrabold capitalize text-streamly-purpleBlue">
                  {idea.lifecycle_stage}
                </span>
              </div>
              <h3 className="mt-3 font-streamly-platform text-xl font-extrabold text-streamly-coal">
                {idea.title}
              </h3>
              <p className="mt-2 line-clamp-1 font-streamly-body text-sm leading-6 text-streamly-purpleBlue">
                {idea.description}
              </p>
            </div>
            <div className="min-w-24 rounded-streamly-lg bg-white px-4 py-3 text-center shadow-streamly-soft">
              <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
                Score
              </p>
              <p className="mt-1 font-streamly-platform text-3xl font-extrabold text-streamly-electric">
                {idea.opportunity_score}
              </p>
              <p className="text-xs font-extrabold text-streamly-purpleBlue">/100</p>
            </div>
          </div>
        </section>

        <section className="grid gap-2 sm:grid-cols-4">
          <SnapshotItem
            detail={`${sourceCount} source${sourceCount === 1 ? "" : "s"}`}
            icon={<Users aria-hidden />}
            label="Audience"
            value={idea.audience}
          />
          <SnapshotItem
            detail="Draft season depth"
            icon={<Layers3 aria-hidden />}
            label="Episodes"
            value={String(episodeCount)}
          />
          <SnapshotItem
            detail={trend.trend_source ?? "Research signal"}
            icon={<TrendingUp aria-hidden />}
            label="Trend"
            value={trend.trend_available ? `${trend.current_trend ?? 0}%` : "N/A"}
          />
          <SnapshotItem
            detail={
              suggestedProfiles.length
                ? suggestedProfiles.join(" / ")
                : "Assign profiles during production"
            }
            icon={<CheckCircle2 aria-hidden />}
            label="Persona Fit"
            value={suggestedProfiles.length ? "Suggested" : "Flexible"}
          />
        </section>

        <section className="rounded-streamly-lg border border-streamly-lavenderStrong bg-white p-4">
          <div className="flex items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-streamly-pill bg-streamly-wash text-streamly-electric">
              <CheckCircle2 aria-hidden className="h-4 w-4" />
            </span>
            <h4 className="font-streamly-platform text-sm font-extrabold text-streamly-coal">
              Review Notes
            </h4>
          </div>
          <ul className="mt-3 space-y-2">
            {reviewNotes.slice(0, 2).map((note) => (
              <li
                className="line-clamp-1 rounded-streamly-md bg-streamly-wash px-3 py-2 text-sm font-bold leading-6 text-streamly-purpleBlue"
                key={note}
              >
                {note}
              </li>
            ))}
          </ul>
        </section>

        <div className="flex flex-wrap justify-end gap-2 border-t border-streamly-lavenderStrong pt-3">
          <button className="streamly-button-secondary" onClick={onClose} type="button">
            Close
          </button>
          {idea.status === "proposed" ? (
            <button
              className="streamly-button-primary"
              disabled={isReviewing}
              onClick={() => onMarkReview(idea)}
              type="button"
            >
              <ExternalLink aria-hidden className="h-4 w-4" />
              {isReviewing ? "Marking" : "Mark in review"}
            </button>
          ) : null}
        </div>
      </div>
    </Modal>
  );
}

function SnapshotItem({
  detail,
  icon,
  label,
  value
}: {
  detail: string;
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-streamly-lg border border-streamly-lavenderStrong bg-white p-3">
      <div className="flex items-center gap-2">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-streamly-pill bg-streamly-wash text-streamly-electric [&>svg]:h-4 [&>svg]:w-4">
          {icon}
        </span>
        <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">{label}</p>
      </div>
      <p className="mt-2 truncate font-streamly-platform text-base font-extrabold text-streamly-coal">
        {value}
      </p>
      <p className="mt-1 line-clamp-1 text-xs font-bold leading-5 text-streamly-purpleBlue">
        {detail}
      </p>
    </div>
  );
}
