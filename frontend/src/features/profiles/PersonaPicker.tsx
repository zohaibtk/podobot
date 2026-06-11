import {
  CheckCircle2,
  Eye,
  Plus,
  Search,
  Sparkles,
  UserRound,
  UsersRound
} from "lucide-react";
import { useMemo, useState } from "react";

import { ErrorState } from "@/design-system/components/ErrorState";
import { Modal } from "@/design-system/components/Modal";
import { ProfileDetailDrawer } from "@/features/profiles/ProfileDetailDrawer";
import { ProfileEditorModal } from "@/features/profiles/ProfileEditorModal";
import {
  useProfileList,
  useProfileRecommendations
} from "@/features/profiles/hooks";
import type { Profile, ProfileKind } from "@/shared/types/series";

export type PersonaPickerContext =
  | { type: "series"; seriesId: string }
  | { type: "episode"; seriesId: string; episodeId: string };

type PersonaPickerProps = {
  context: PersonaPickerContext;
  kind: ProfileKind;
  label: string;
  value: string | null;
  selectedLabel?: string | null;
  excludedProfileId?: string | null;
  disabled?: boolean;
  placeholder?: string;
  onSelect: (profile: Profile | null) => Promise<void> | void;
};

export function PersonaPicker({
  context,
  kind,
  label,
  value,
  selectedLabel,
  excludedProfileId,
  disabled = false,
  placeholder,
  onSelect
}: PersonaPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [detailProfile, setDetailProfile] = useState<Profile | null>(null);
  const [search, setSearch] = useState("");
  const profileQuery = useProfileList({ kind, search });
  const recommendationsQuery = useProfileRecommendations({
    kind,
    search,
    limit: 5,
    enabled: isOpen
  });

  const profiles = useMemo(() => profileQuery.data?.items ?? [], [profileQuery.data?.items]);
  const recommendations = useMemo(
    () => recommendationsQuery.data?.items ?? [],
    [recommendationsQuery.data?.items]
  );
  const selectedProfile = profiles.find((profile) => profile.id === value) ?? null;
  const buttonLabel = selectedProfile?.name ?? selectedLabel ?? placeholder ?? `Select ${kind}`;
  const KindIcon = kind === "host" ? UserRound : UsersRound;

  async function selectProfile(profile: Profile | null) {
    if (profile?.id === excludedProfileId) {
      return;
    }
    await onSelect(profile);
    setIsOpen(false);
  }

  async function createAndSelect(profile: Profile) {
    setIsCreateOpen(false);
    await selectProfile(profile);
  }

  return (
    <div className="rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash/60 p-3">
      <span className="flex items-center gap-2 text-xs font-extrabold uppercase text-streamly-purpleBlue">
        <KindIcon aria-hidden className="h-3.5 w-3.5" />
        {label}
      </span>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <button
          className="min-w-0 flex-1 rounded-streamly-md border border-streamly-lavenderStrong bg-white px-3 py-2 text-left text-sm font-bold text-streamly-coal outline-none transition hover:bg-streamly-wash focus:border-streamly-electric focus:ring-2 focus:ring-streamly-lavender disabled:cursor-not-allowed disabled:opacity-60"
          disabled={disabled}
          onClick={() => setIsOpen(true)}
          type="button"
        >
          <span className={value ? "block truncate" : "block truncate text-[var(--streamly-text-muted)]"}>
            {buttonLabel}
          </span>
        </button>
        {value ? (
          <button
            className="rounded-streamly-pill px-3 py-2 text-xs font-extrabold text-streamly-purpleBlue hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
            disabled={disabled}
            onClick={() => void selectProfile(null)}
            type="button"
          >
            Clear
          </button>
        ) : null}
      </div>
      {value === excludedProfileId && value ? (
        <p className="mt-2 rounded-streamly-md bg-red-50 px-2.5 py-2 text-xs font-bold text-red-700">
          Host and guest must be different profiles.
        </p>
      ) : null}

      <Modal
        description={`${context.type === "episode" ? "Episode" : "Series"} assignment uses reusable library profiles.`}
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title={`Select ${kind === "host" ? "Host" : "Guest"} Profile`}
      >
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <label className="relative min-w-0 flex-1">
              <span className="sr-only">Search profiles</span>
              <Search
                aria-hidden
                className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-streamly-purpleBlue"
              />
              <input
                className="streamly-search w-full max-w-none pl-9"
                onChange={(event) => setSearch(event.target.value)}
                placeholder={`Search ${kind} profiles`}
                value={search}
              />
            </label>
            <button
              className="streamly-button-secondary"
              onClick={() => setIsCreateOpen(true)}
              type="button"
            >
              <Plus aria-hidden className="h-4 w-4" />
              New {kind}
            </button>
          </div>

          <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash/70 p-4">
            <div className="flex items-center gap-2 text-streamly-violet">
              <Sparkles aria-hidden className="h-4 w-4" />
              <p className="text-xs font-extrabold uppercase">Recommended picks</p>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {recommendationsQuery.isLoading ? (
                <span className="streamly-chip animate-pulse">Loading recommendations</span>
              ) : recommendations.length ? (
                recommendations.map((recommendation) => {
                  const isBlocked = recommendation.profile.id === excludedProfileId;
                  return (
                    <button
                      className={[
                        "streamly-chip transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-45",
                        recommendation.profile.id === value ? "ring-2 ring-streamly-electric" : ""
                      ].join(" ")}
                      disabled={isBlocked}
                      key={recommendation.profile.id}
                      onClick={() => void selectProfile(recommendation.profile)}
                      title={isBlocked ? "Already selected in the other lane" : recommendation.reason}
                      type="button"
                    >
                      {recommendation.profile.name}
                    </button>
                  );
                })
              ) : (
                <span className="text-sm font-bold text-[var(--streamly-text-muted)]">
                  No recommendations match this search.
                </span>
              )}
            </div>
          </section>

          {profileQuery.isError ? (
            <ErrorState
              actionLabel="Retry"
              description={errorMessage(profileQuery.error)}
              onAction={() => void profileQuery.refetch()}
              title="Profile search failed"
            />
          ) : (
            <div className="max-h-[22rem] space-y-2 overflow-y-auto pr-1">
              {profileQuery.isLoading ? (
                <PickerSkeleton />
              ) : profiles.length ? (
                profiles.map((profile) => (
                  <ProfilePickerRow
                    isBlocked={profile.id === excludedProfileId}
                    isSelected={profile.id === value}
                    key={profile.id}
                    onInspect={() => setDetailProfile(profile)}
                    onSelect={() => void selectProfile(profile)}
                    profile={profile}
                  />
                ))
              ) : (
                <div className="rounded-streamly-xl border border-dashed border-streamly-lavenderStrong bg-white p-6 text-center">
                  <p className="font-streamly-platform text-lg font-extrabold text-streamly-coal">
                    No profiles found
                  </p>
                  <p className="mt-2 text-sm font-semibold leading-6 text-[var(--streamly-text-muted)]">
                    Create a reusable {kind} profile from this picker and assign it immediately.
                  </p>
                  <button
                    className="streamly-button-primary mt-4"
                    onClick={() => setIsCreateOpen(true)}
                    type="button"
                  >
                    <Plus aria-hidden className="h-4 w-4" />
                    Create {kind}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </Modal>

      <ProfileEditorModal
        initialKind={kind}
        isOpen={isCreateOpen}
        lockedKind={kind}
        mode="create"
        onClose={() => setIsCreateOpen(false)}
        onSaved={(profile) => void createAndSelect(profile)}
      />

      <ProfileDetailDrawer
        isOpen={detailProfile !== null}
        onClose={() => setDetailProfile(null)}
        profile={detailProfile}
      />
    </div>
  );
}

function ProfilePickerRow({
  isBlocked,
  isSelected,
  onInspect,
  onSelect,
  profile
}: {
  isBlocked: boolean;
  isSelected: boolean;
  onInspect: () => void;
  onSelect: () => void;
  profile: Profile;
}) {
  return (
    <div
      className={[
        "rounded-streamly-xl border bg-white p-4 shadow-streamly-card",
        isSelected ? "border-streamly-electric" : "border-streamly-lavenderStrong"
      ].join(" ")}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-streamly-platform text-base font-extrabold text-streamly-coal">
              {profile.name}
            </h3>
            {isSelected ? (
              <span className="inline-flex items-center gap-1 rounded-streamly-pill bg-emerald-50 px-2 py-1 text-xs font-extrabold text-emerald-700">
                <CheckCircle2 aria-hidden className="h-3.5 w-3.5" />
                Selected
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
            {profile.role_title}
          </p>
          <p className="mt-2 text-sm font-semibold leading-6 text-[var(--streamly-text-muted)]">
            {profile.archetype}
          </p>
          {isBlocked ? (
            <p className="mt-2 rounded-streamly-md bg-red-50 px-2.5 py-2 text-xs font-bold text-red-700">
              Already selected in the other assignment lane.
            </p>
          ) : null}
        </div>

        <div className="flex gap-2">
          <button
            aria-label={`View ${profile.name}`}
            className="grid h-9 w-9 place-items-center rounded-streamly-pill text-streamly-purpleBlue hover:bg-streamly-wash"
            onClick={onInspect}
            type="button"
          >
            <Eye aria-hidden className="h-4 w-4" />
          </button>
          <button
            className="rounded-streamly-pill bg-streamly-electric px-4 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-45"
            disabled={isBlocked || isSelected}
            onClick={onSelect}
            type="button"
          >
            Select
          </button>
        </div>
      </div>
    </div>
  );
}

function PickerSkeleton() {
  return (
    <div className="space-y-2">
      {[0, 1, 2].map((item) => (
        <div
          className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card"
          key={item}
        >
          <div className="h-5 w-40 animate-pulse rounded-streamly-pill bg-streamly-lavender" />
          <div className="mt-3 h-4 w-64 animate-pulse rounded-streamly-pill bg-streamly-wash" />
          <div className="mt-2 h-4 w-full animate-pulse rounded-streamly-pill bg-streamly-wash" />
        </div>
      ))}
    </div>
  );
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Profiles could not be loaded.";
}
