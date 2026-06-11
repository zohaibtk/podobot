import { zodResolver } from "@hookform/resolvers/zod";
import type { ReactNode } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Modal } from "@/design-system/components/Modal";
import { useCreateSeries } from "@/features/series/hooks";
import type { Series } from "@/shared/types/series";

const createSeriesSchema = z.object({
  name: z.string().trim().min(1, "Series name is required").max(180),
  audience: z.string().trim().min(1, "Audience is required").max(240),
  description: z.string().trim().min(1, "Description is required"),
  guest_name: z.string().trim().max(180).optional()
});

type CreateSeriesFormValues = z.infer<typeof createSeriesSchema>;

type CreateSeriesModalProps = {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (series: Series) => void;
};

export function CreateSeriesModal({ isOpen, onClose, onCreated }: CreateSeriesModalProps) {
  const createMutation = useCreateSeries();
  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    reset
  } = useForm<CreateSeriesFormValues>({
    resolver: zodResolver(createSeriesSchema),
    mode: "onChange",
    defaultValues: {
      name: "",
      audience: "",
      description: "",
      guest_name: ""
    }
  });

  async function onSubmit(values: CreateSeriesFormValues) {
    const created = await createMutation.mutateAsync({
      ...values,
      guest_name: values.guest_name || null
    });
    reset();
    onCreated(created);
  }

  function close() {
    if (!createMutation.isPending) {
      reset();
      onClose();
    }
  }

  return (
    <Modal
      description="Start with only the setup inputs the pipeline actually needs."
      isOpen={isOpen}
      onClose={close}
      title="Create Series"
    >
      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
        <Field label="Series name" message={errors.name?.message}>
          <input
            className="streamly-search w-full max-w-none"
            placeholder="The Executive AI Operating Room"
            {...register("name")}
          />
        </Field>

        <Field label="Audience" message={errors.audience?.message}>
          <input
            className="streamly-search w-full max-w-none"
            placeholder="CIOs, founders, and transformation leaders"
            {...register("audience")}
          />
        </Field>

        <Field label="Description" message={errors.description?.message}>
          <textarea
            className="min-h-32 w-full rounded-streamly-xl border border-streamly-lavenderStrong bg-white px-4 py-3 font-streamly-body text-sm outline-none transition focus:border-streamly-electric focus:ring-4 focus:ring-streamly-electric/15"
            placeholder="Describe the editorial goal, audience need, and business context."
            {...register("description")}
          />
        </Field>

        <Field label="Guest (optional)" message={errors.guest_name?.message}>
          <input
            className="streamly-search w-full max-w-none"
            placeholder="Optional default guest"
            {...register("guest_name")}
          />
        </Field>

        {createMutation.error ? (
          <p className="rounded-streamly-md bg-red-50 px-3 py-2 text-sm font-bold text-red-700">
            Could not create the series. Check the fields and try again.
          </p>
        ) : null}

        <div className="flex justify-end gap-3 border-t border-streamly-lavenderStrong pt-5">
          <button
            className="streamly-button-secondary"
            disabled={createMutation.isPending}
            onClick={close}
            type="button"
          >
            Cancel
          </button>
          <button
            className="streamly-button-primary disabled:opacity-50"
            disabled={!isValid || createMutation.isPending}
            type="submit"
          >
            {createMutation.isPending ? "Creating..." : "Create Series"}
          </button>
        </div>
      </form>
    </Modal>
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
