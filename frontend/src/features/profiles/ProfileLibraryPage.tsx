import {
  BriefcaseBusiness,
  Eye,
  Pencil,
  Plus,
  Search,
  Sparkles,
  Trash2,
  UserRound,
  UsersRound
} from "lucide-react";
import { useMemo, useState } from "react";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Pagination } from "@/design-system/components/Pagination";
import { ProfileDetailDrawer } from "@/features/profiles/ProfileDetailDrawer";
import { ProfileEditorModal } from "@/features/profiles/ProfileEditorModal";
import {
  useDeleteProfile,
  useProfileList,
  useProfileRecommendations
} from "@/features/profiles/hooks";
import { usePaginationParams } from "@/shared/hooks/usePaginationParams";
import type { Profile, ProfileFilters, ProfileKind } from "@/shared/types/series";

type KindFilter = "all" | ProfileKind;

export function ProfileLibraryPage() {
  const [kindFilter, setKindFilter] = useState<KindFilter>("all");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null);
  const [detailProfile, setDetailProfile] = useState<Profile | null>(null);
  const deleteProfile = useDeleteProfile();
  const pagination = usePaginationParams({
    defaultPageSize: 20,
    defaultSort: "name",
    storageKey: "podobot.profiles.page_size"
  });

  const filters = useMemo<ProfileFilters>(
    () => ({
      search: pagination.search,
      kind: kindFilter === "all" ? undefined : kindFilter,
      page: pagination.page,
      pageSize: pagination.pageSize,
      sort: pagination.sort
    }),
    [
      kindFilter,
      pagination.page,
      pagination.pageSize,
      pagination.search,
      pagination.sort
    ]
  );

  const profilesQuery = useProfileList(filters);
  const allProfilesQuery = useProfileList({ pageSize: 200, sort: "name" });
  const recommendationKind: ProfileKind = kindFilter === "guest" ? "guest" : "host";
  const recommendationsQuery = useProfileRecommendations({
    kind: recommendationKind,
    limit: 4
  });

  const profiles = useMemo(() => profilesQuery.data?.items ?? [], [profilesQuery.data?.items]);
  const allProfiles = useMemo(
    () => allProfilesQuery.data?.items ?? [],
    [allProfilesQuery.data?.items]
  );
  const hostCount = allProfiles.filter((profile) => profile.kind === "host").length;
  const guestCount = allProfiles.filter((profile) => profile.kind === "guest").length;

  async function removeProfile(profile: Profile) {
    const confirmed = window.confirm(
      `Delete ${profile.name}? This removes the profile from active pickers and the profile library.`
    );
    if (!confirmed) {
      return;
    }
    await deleteProfile.mutateAsync(profile.id);
    setEditingProfile((current) => (current?.id === profile.id ? null : current));
    setDetailProfile((current) => (current?.id === profile.id ? null : current));
  }

  return (
    <main className="space-y-5">
      <PageHeader
        actions={
          <button
            className="streamly-button-primary"
            onClick={() => setIsCreateOpen(true)}
            type="button"
          >
            <Plus aria-hidden className="h-4 w-4" />
            Create profile
          </button>
        }
        description="Curate the voices producers assign across series plans, episode boards, and later production stages."
        kicker="Profile Library"
        title="Reusable host and guest personas"
      >
        <dl className="grid gap-3 sm:grid-cols-3">
          <LibraryMetric icon="host" label="Hosts" value={hostCount} />
          <LibraryMetric icon="guest" label="Guests" value={guestCount} />
          <LibraryMetric icon="active" label="Active profiles" value={allProfiles.length} />
        </dl>
      </PageHeader>

      <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash/75 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <label className="relative min-w-0 flex-1">
            <span className="sr-only">Search profile library</span>
            <Search
              aria-hidden
              className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-streamly-purpleBlue"
            />
            <input
              className="streamly-search w-full max-w-none pl-9"
              onChange={(event) => pagination.setSearch(event.target.value)}
              placeholder="Search names, roles, and bios"
              value={pagination.search}
            />
          </label>
          <KindFilterButton
            count={allProfiles.length}
            isActive={kindFilter === "all"}
            label="All"
            onClick={() => {
              setKindFilter("all");
              pagination.setPage(1);
            }}
          />
          <KindFilterButton
            count={hostCount}
            isActive={kindFilter === "host"}
            label="Hosts"
            onClick={() => {
              setKindFilter("host");
              pagination.setPage(1);
            }}
          />
          <KindFilterButton
            count={guestCount}
            isActive={kindFilter === "guest"}
            label="Guests"
            onClick={() => {
              setKindFilter("guest");
              pagination.setPage(1);
            }}
          />
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <section className="space-y-3">
          {deleteProfile.error ? (
            <ErrorState
              description={errorMessage(deleteProfile.error)}
              title="Profile delete failed"
            />
          ) : null}
          {profilesQuery.isLoading ? (
            <LoadingState label="Loading profiles" />
          ) : profilesQuery.isError ? (
            <ErrorState
              actionLabel="Retry"
              description={errorMessage(profilesQuery.error)}
              onAction={() => void profilesQuery.refetch()}
              title="Profiles unavailable"
            />
          ) : profiles.length ? (
            profiles.map((profile) => (
              <ProfileLibraryRow
                isDeleting={deleteProfile.isPending}
                key={profile.id}
                onDelete={() => void removeProfile(profile)}
                onEdit={() => setEditingProfile(profile)}
                onView={() => setDetailProfile(profile)}
                profile={profile}
              />
            ))
          ) : (
            <EmptyState
              description="No reusable profile matches the current search and filter set."
              title="No profiles found"
            />
          )}
          {!profilesQuery.isLoading && !profilesQuery.isError && profiles.length ? (
            <Pagination
              hasNext={profilesQuery.data?.has_next ?? false}
              hasPrevious={profilesQuery.data?.has_previous ?? false}
              label="profiles"
              onPageChange={pagination.setPage}
              onPageSizeChange={pagination.setPageSize}
              page={profilesQuery.data?.page ?? pagination.page}
              pageSize={profilesQuery.data?.page_size ?? pagination.pageSize}
              total={profilesQuery.data?.total ?? profiles.length}
              totalPages={profilesQuery.data?.total_pages ?? 1}
            />
          ) : null}
        </section>

        <aside className="space-y-4">
          <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
            <div className="flex items-center gap-2 text-streamly-violet">
              <Sparkles aria-hidden className="h-4 w-4" />
              <p className="text-xs font-extrabold uppercase">Recommendation chips</p>
            </div>
            <p className="mt-2 text-sm font-semibold leading-6 text-[var(--streamly-text-muted)]">
              Fast picks for the active library lane.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {recommendationsQuery.isLoading ? (
                <span className="streamly-chip animate-pulse">Loading</span>
              ) : recommendationsQuery.data?.items.length ? (
                recommendationsQuery.data.items.map((recommendation) => (
                  <button
                    className="streamly-chip transition hover:bg-streamly-wash"
                    key={recommendation.profile.id}
                    onClick={() => setDetailProfile(recommendation.profile)}
                    title={recommendation.reason}
                    type="button"
                  >
                    {recommendation.profile.name}
                  </button>
                ))
              ) : (
                <span className="text-sm font-bold text-[var(--streamly-text-muted)]">
                  No recommendations available.
                </span>
              )}
            </div>
          </section>

          <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash/80 p-4">
            <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
              Assignment rule
            </p>
            <p className="mt-3 text-sm font-bold leading-6 text-streamly-coal">
              Host and guest lanes are separate. Episode assignment blocks the same profile from filling both roles.
            </p>
          </section>
        </aside>
      </div>

      <ProfileEditorModal
        isOpen={isCreateOpen}
        mode="create"
        onClose={() => setIsCreateOpen(false)}
      />

      <ProfileEditorModal
        isOpen={editingProfile !== null}
        mode="edit"
        onClose={() => setEditingProfile(null)}
        onSaved={(profile) => setDetailProfile(profile)}
        profile={editingProfile}
      />

      <ProfileDetailDrawer
        isOpen={detailProfile !== null}
        onClose={() => setDetailProfile(null)}
        onEdit={(profile) => {
          setDetailProfile(null);
          setEditingProfile(profile);
        }}
        isDeleting={deleteProfile.isPending}
        onDelete={(profile) => void removeProfile(profile)}
        profile={detailProfile}
      />
    </main>
  );
}

function LibraryMetric({
  icon,
  label,
  value
}: {
  icon: "host" | "guest" | "active";
  label: string;
  value: number;
}) {
  const Icon = icon === "guest" ? UsersRound : icon === "host" ? UserRound : BriefcaseBusiness;

  return (
    <div className="rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash/70 p-4">
      <div className="flex items-center gap-2 text-streamly-purpleBlue">
        <Icon aria-hidden className="h-4 w-4" />
        <dt className="text-xs font-extrabold uppercase">{label}</dt>
      </div>
      <dd className="mt-2 font-streamly-platform text-2xl font-extrabold text-streamly-coal">
        {value}
      </dd>
    </div>
  );
}

function KindFilterButton({
  count,
  isActive,
  label,
  onClick
}: {
  count: number;
  isActive: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      aria-pressed={isActive}
      className={[
        "rounded-streamly-pill px-4 py-2 text-sm font-extrabold transition",
        isActive
          ? "bg-streamly-electric text-white shadow-streamly-button"
          : "bg-white text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-lavender"
      ].join(" ")}
      onClick={onClick}
      type="button"
    >
      {label} <span className="opacity-75">{count}</span>
    </button>
  );
}

function ProfileLibraryRow({
  isDeleting,
  onDelete,
  onEdit,
  onView,
  profile
}: {
  isDeleting: boolean;
  onDelete: () => void;
  onEdit: () => void;
  onView: () => void;
  profile: Profile;
}) {
  const KindIcon = profile.kind === "host" ? UserRound : UsersRound;

  return (
    <article className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_14rem]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-lavender px-3 py-1 text-xs font-extrabold uppercase text-streamly-violet">
              <KindIcon aria-hidden className="h-3.5 w-3.5" />
              {profile.kind}
            </span>
            <span className="streamly-chip">{profile.archetype}</span>
          </div>
          <h2 className="mt-3 font-streamly-platform text-xl font-extrabold text-streamly-coal">
            {profile.name}
          </h2>
          <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
            {profile.role_title}
          </p>
          <p className="mt-2 line-clamp-2 text-sm font-semibold leading-6 text-[var(--streamly-text-muted)]">
            {profile.bio || "No bio has been added yet."}
          </p>
        </div>

        <div className="flex gap-2 lg:flex-col lg:justify-center">
          <button
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-streamly-pill bg-streamly-wash px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue hover:bg-streamly-lavender"
            onClick={onView}
            type="button"
          >
            <Eye aria-hidden className="h-4 w-4" />
            View
          </button>
          <button
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-streamly-pill bg-white px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-wash"
            onClick={onEdit}
            type="button"
          >
            <Pencil aria-hidden className="h-4 w-4" />
            Edit
          </button>
          <button
            aria-label={`Delete ${profile.name}`}
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-streamly-pill bg-red-50 px-3 py-2 text-sm font-extrabold text-red-700 shadow-streamly-card hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isDeleting}
            onClick={onDelete}
            type="button"
          >
            <Trash2 aria-hidden className="h-4 w-4" />
            Delete
          </button>
        </div>
      </div>
    </article>
  );
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "The profile library could not be loaded.";
}
