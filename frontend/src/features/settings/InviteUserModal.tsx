import { zodResolver } from "@hookform/resolvers/zod";
import { MailPlus } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Modal } from "@/design-system/components/Modal";
import { useInviteUser } from "@/features/settings/hooks";
import type { Role, UserInvitation } from "@/shared/types/settings";

const inviteSchema = z.object({
  email: z.string().trim().email("A valid email address is required").max(240),
  full_name: z.string().trim().max(180).optional(),
  role_id: z.string().trim().min(1, "Role is required")
});

type InviteFormValues = z.infer<typeof inviteSchema>;

type InviteUserModalProps = {
  isOpen: boolean;
  roles: Role[];
  onClose: () => void;
  onInvited?: (invitation: UserInvitation) => void;
};

export function InviteUserModal({
  isOpen,
  roles,
  onClose,
  onInvited
}: InviteUserModalProps) {
  const inviteMutation = useInviteUser();
  const assignableRoles = roles.filter((role) => role.is_assignable);
  const defaultRoleId = assignableRoles[0]?.id ?? "";
  const {
    formState: { errors, isValid },
    handleSubmit,
    register,
    reset
  } = useForm<InviteFormValues>({
    resolver: zodResolver(inviteSchema),
    mode: "onChange",
    defaultValues: { email: "", full_name: "", role_id: defaultRoleId }
  });

  useEffect(() => {
    reset({ email: "", full_name: "", role_id: defaultRoleId });
  }, [defaultRoleId, isOpen, reset]);

  async function submit(values: InviteFormValues) {
    const invitation = await inviteMutation.mutateAsync({
      email: values.email,
      full_name: values.full_name?.trim() || null,
      role_id: values.role_id
    });
    onInvited?.(invitation);
    reset({ email: "", full_name: "", role_id: defaultRoleId });
    onClose();
  }

  function close() {
    if (!inviteMutation.isPending) {
      onClose();
    }
  }

  return (
    <Modal
      description="Create a prototype invitation and add the user to the workspace list as invited."
      isOpen={isOpen}
      onClose={close}
      title="Invite User"
    >
      <form className="space-y-4" onSubmit={(event) => void handleSubmit(submit)(event)}>
        <Field label="Email" message={errors.email?.message}>
          <input
            className="streamly-search w-full max-w-none"
            placeholder="producer@example.com"
            {...register("email")}
          />
        </Field>

        <Field label="Full name" message={errors.full_name?.message}>
          <input
            className="streamly-search w-full max-w-none"
            placeholder="New Producer"
            {...register("full_name")}
          />
        </Field>

        <Field label="Role" message={errors.role_id?.message}>
          <select
            className="streamly-search w-full max-w-none"
            {...register("role_id")}
          >
            {assignableRoles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.name}
              </option>
            ))}
          </select>
        </Field>

        {inviteMutation.error ? (
          <p className="rounded-streamly-md bg-red-50 px-3 py-2 text-sm font-bold text-red-700">
            {errorMessage(inviteMutation.error)}
          </p>
        ) : null}

        <div className="flex flex-wrap justify-end gap-3 border-t border-streamly-lavenderStrong pt-5">
          <button
            className="streamly-button-secondary"
            disabled={inviteMutation.isPending}
            onClick={close}
            type="button"
          >
            Cancel
          </button>
          <button
            className="streamly-button-primary disabled:opacity-50"
            disabled={!isValid || inviteMutation.isPending}
            type="submit"
          >
            <MailPlus aria-hidden className="h-4 w-4" />
            {inviteMutation.isPending ? "Inviting..." : "Send invite"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function Field({
  children,
  label,
  message
}: {
  children: ReactNode;
  label: string;
  message?: string;
}) {
  return (
    <label className="grid gap-2">
      <span className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
        {label}
      </span>
      {children}
      {message ? <span className="text-xs font-bold text-red-600">{message}</span> : null}
    </label>
  );
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Invitation failed.";
}
