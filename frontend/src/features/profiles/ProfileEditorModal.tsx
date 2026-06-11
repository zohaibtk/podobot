import { zodResolver } from "@hookform/resolvers/zod";
import { Save, UserRound, UsersRound } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Modal } from "@/design-system/components/Modal";
import { useCreateProfile, useUpdateProfile } from "@/features/profiles/hooks";
import type { Profile, ProfileDraftPayload, ProfileKind } from "@/shared/types/series";

const profileSchema = z.object({
  name: z.string().trim().min(1, "Profile name is required").max(180),
  role_title: z.string().trim().min(1, "Role title is required").max(180),
  kind: z.enum(["host", "guest"]),
  archetype: z.string().trim().min(1, "Archetype is required").max(240),
  bio: z.string().trim().max(1200).optional()
});

type ProfileFormValues = z.infer<typeof profileSchema>;

type ProfileEditorModalProps = {
  isOpen: boolean;
  mode: "create" | "edit";
  profile?: Profile | null;
  initialKind?: ProfileKind;
  lockedKind?: ProfileKind;
  onClose: () => void;
  onSaved?: (profile: Profile) => void;
};

export function ProfileEditorModal({
  isOpen,
  mode,
  profile,
  initialKind = "host",
  lockedKind,
  onClose,
  onSaved
}: ProfileEditorModalProps) {
  const createProfile = useCreateProfile();
  const updateProfile = useUpdateProfile();
  const isSubmitting = createProfile.isPending || updateProfile.isPending;

  const {
    formState: { errors, isValid },
    handleSubmit,
    register,
    reset,
    setValue,
    watch
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    mode: "onChange",
    defaultValues: emptyValues(lockedKind ?? initialKind)
  });

  const selectedKind = watch("kind");

  useEffect(() => {
    if (mode === "edit" && profile) {
      reset({
        name: profile.name,
        role_title: profile.role_title,
        kind: lockedKind ?? profile.kind,
        archetype: profile.archetype,
        bio: profile.bio ?? ""
      });
      return;
    }
    reset(emptyValues(lockedKind ?? initialKind));
  }, [initialKind, isOpen, lockedKind, mode, profile, reset]);

  async function submit(values: ProfileFormValues) {
    const payload: ProfileDraftPayload = {
      ...values,
      kind: lockedKind ?? values.kind,
      bio: values.bio?.trim() || null
    };
    const saved =
      mode === "edit" && profile
        ? await updateProfile.mutateAsync({ profileId: profile.id, payload })
        : await createProfile.mutateAsync(payload);
    onSaved?.(saved);
    reset(emptyValues(lockedKind ?? initialKind));
    onClose();
  }

  function close() {
    if (!isSubmitting) {
      onClose();
    }
  }

  return (
    <Modal
      description={
        lockedKind
          ? `Create a reusable ${lockedKind} profile for this assignment lane.`
          : "Create a reusable persona for planning, assignments, and future production stages."
      }
      isOpen={isOpen}
      onClose={close}
      title={mode === "edit" ? "Edit Profile" : "Create Profile"}
    >
      <form className="space-y-4" onSubmit={(event) => void handleSubmit(submit)(event)}>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Profile name" message={errors.name?.message}>
            <input
              className="streamly-search w-full max-w-none"
              placeholder="Full name"
              {...register("name")}
            />
          </Field>

          <Field label="Role title" message={errors.role_title?.message}>
            <input
              className="streamly-search w-full max-w-none"
              placeholder="Role title"
              {...register("role_title")}
            />
          </Field>
        </div>

        <Field label="Persona lane" message={errors.kind?.message}>
          <div className="grid gap-2 sm:grid-cols-2">
            <KindButton
              disabled={Boolean(lockedKind) || isSubmitting}
              icon="host"
              isSelected={selectedKind === "host"}
              label="Host"
              onClick={() => setValue("kind", "host", { shouldValidate: true })}
            />
            <KindButton
              disabled={Boolean(lockedKind) || isSubmitting}
              icon="guest"
              isSelected={selectedKind === "guest"}
              label="Guest"
              onClick={() => setValue("kind", "guest", { shouldValidate: true })}
            />
          </div>
        </Field>

        <Field label="Archetype" message={errors.archetype?.message}>
          <input
            className="streamly-search w-full max-w-none"
            placeholder="Profile archetype"
            {...register("archetype")}
          />
        </Field>

        <Field label="Bio" message={errors.bio?.message}>
          <textarea
            className="min-h-28 w-full rounded-streamly-xl border border-streamly-lavenderStrong bg-white px-4 py-3 font-streamly-body text-sm leading-6 outline-none transition focus:border-streamly-electric focus:ring-4 focus:ring-streamly-electric/15"
            placeholder="Voice, strengths, and production fit"
            {...register("bio")}
          />
        </Field>

        {createProfile.error || updateProfile.error ? (
          <p className="rounded-streamly-md bg-red-50 px-3 py-2 text-sm font-bold text-red-700">
            {errorMessage(createProfile.error ?? updateProfile.error)}
          </p>
        ) : null}

        <div className="flex flex-wrap justify-end gap-3 border-t border-streamly-lavenderStrong pt-5">
          <button
            className="streamly-button-secondary"
            disabled={isSubmitting}
            onClick={close}
            type="button"
          >
            Cancel
          </button>
          <button
            className="streamly-button-primary disabled:opacity-50"
            disabled={!isValid || isSubmitting}
            type="submit"
          >
            <Save aria-hidden className="h-4 w-4" />
            {isSubmitting ? "Saving..." : "Save profile"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function emptyValues(kind: ProfileKind): ProfileFormValues {
  return {
    name: "",
    role_title: "",
    kind,
    archetype: "",
    bio: ""
  };
}

function KindButton({
  disabled,
  icon,
  isSelected,
  label,
  onClick
}: {
  disabled: boolean;
  icon: ProfileKind;
  isSelected: boolean;
  label: string;
  onClick: () => void;
}) {
  const Icon = icon === "host" ? UserRound : UsersRound;

  return (
    <button
      aria-pressed={isSelected}
      className={[
        "flex items-center justify-center gap-2 rounded-streamly-pill border px-4 py-3 text-sm font-extrabold transition disabled:cursor-not-allowed disabled:opacity-60",
        isSelected
          ? "border-streamly-electric bg-streamly-lavender text-streamly-violet"
          : "border-streamly-lavenderStrong bg-white text-streamly-purpleBlue hover:bg-streamly-wash"
      ].join(" ")}
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      <Icon aria-hidden className="h-4 w-4" />
      {label}
    </button>
  );
}

function Field({
  label,
  message,
  children
}: {
  label: string;
  message?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-sm font-extrabold text-streamly-coal">{label}</span>
      <div className="mt-2">{children}</div>
      {message ? <span className="mt-1 block text-xs font-bold text-red-700">{message}</span> : null}
    </label>
  );
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "The profile could not be saved.";
}
