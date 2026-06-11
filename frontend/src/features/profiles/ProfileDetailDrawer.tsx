import { createPortal } from "react-dom";
import {
  BriefcaseBusiness,
  Sparkles,
  Trash2,
  UserRound,
  UsersRound,
  X
} from "lucide-react";

import { useBodyScrollLock } from "@/design-system/hooks/useBodyScrollLock";
import type { Profile } from "@/shared/types/series";

type ProfileDetailDrawerProps = {
  profile: Profile | null;
  isOpen: boolean;
  onClose: () => void;
  isDeleting?: boolean;
  onDelete?: (profile: Profile) => void;
  onEdit?: (profile: Profile) => void;
};

export function ProfileDetailDrawer({
  profile,
  isDeleting = false,
  isOpen,
  onClose,
  onDelete,
  onEdit
}: ProfileDetailDrawerProps) {
  useBodyScrollLock(isOpen);

  if (!isOpen || !profile) {
    return null;
  }

  const KindIcon = profile.kind === "host" ? UserRound : UsersRound;

  const drawer = (
    <div
      aria-modal="true"
      className="fixed inset-0 z-[1000] overflow-hidden bg-streamly-coal/35 backdrop-blur-sm"
      role="dialog"
    >
      <button
        aria-label="Close profile detail"
        className="absolute inset-0 h-full w-full cursor-default"
        onClick={onClose}
        type="button"
      />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-md flex-col border-l border-streamly-lavenderStrong bg-white shadow-streamly-soft">
        <div className="border-b border-streamly-lavenderStrong p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <span className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-lavender px-3 py-1 text-xs font-extrabold uppercase text-streamly-violet">
                <KindIcon aria-hidden className="h-3.5 w-3.5" />
                {profile.kind}
              </span>
              <h2 className="mt-4 font-streamly-platform text-2xl font-extrabold text-streamly-coal">
                {profile.name}
              </h2>
              <p className="mt-1 text-sm font-bold text-streamly-purpleBlue">
                {profile.role_title}
              </p>
            </div>
            <button
              aria-label="Close profile detail"
              className="grid h-9 w-9 place-items-center rounded-streamly-pill text-streamly-purpleBlue hover:bg-streamly-wash"
              onClick={onClose}
              type="button"
            >
              <X aria-hidden className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain p-5">
          <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash/70 p-4">
            <div className="flex items-center gap-2 text-streamly-violet">
              <Sparkles aria-hidden className="h-4 w-4" />
              <p className="text-xs font-extrabold uppercase">Archetype</p>
            </div>
            <p className="mt-3 text-sm font-bold leading-6 text-streamly-coal">
              {profile.archetype}
            </p>
          </section>

          <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
            <div className="flex items-center gap-2 text-streamly-purpleBlue">
              <BriefcaseBusiness aria-hidden className="h-4 w-4" />
              <p className="text-xs font-extrabold uppercase">Production fit</p>
            </div>
            <p className="mt-3 text-sm font-semibold leading-6 text-[var(--streamly-text-muted)]">
              {profile.bio || "No bio has been added yet."}
            </p>
          </section>

          <dl className="grid grid-cols-2 gap-3">
            <Metric label="Status" value={profile.is_active ? "Active" : "Inactive"} />
            <Metric label="Updated" value={new Date(profile.updated_at).toLocaleDateString()} />
          </dl>
        </div>

        {onEdit || onDelete ? (
          <div className="flex gap-2 border-t border-streamly-lavenderStrong p-5">
            {onDelete ? (
              <button
                className="inline-flex flex-1 items-center justify-center gap-2 rounded-streamly-pill bg-red-50 px-4 py-3 text-sm font-extrabold text-red-700 shadow-streamly-card hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isDeleting}
                onClick={() => onDelete(profile)}
                type="button"
              >
                <Trash2 aria-hidden className="h-4 w-4" />
                Delete
              </button>
            ) : null}
            {onEdit ? (
            <button
              className="streamly-button-primary flex-1"
              onClick={() => onEdit(profile)}
              type="button"
            >
              Edit profile
            </button>
            ) : null}
          </div>
        ) : null}
      </aside>
    </div>
  );

  if (typeof document === "undefined") {
    return drawer;
  }

  return createPortal(drawer, document.body);
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash/70 p-3">
      <dt className="text-xs font-extrabold uppercase text-streamly-purpleBlue">{label}</dt>
      <dd className="mt-1 text-sm font-bold text-streamly-coal">{value}</dd>
    </div>
  );
}
