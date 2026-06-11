import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Save, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Modal } from "@/design-system/components/Modal";
import type {
  Episode,
  EpisodeDraftGenerationPayload,
  EpisodeDraftGenerationResponse,
  EpisodeDraftPayload
} from "@/shared/types/series";

const episodeSchema = z.object({
  title: z.string().trim().min(1, "Episode title is required").max(220),
  premise: z.string().trim().min(1, "Episode premise is required")
});

type EpisodeFormValues = z.infer<typeof episodeSchema>;

type EpisodeEditorModalProps = {
  isOpen: boolean;
  mode: "add" | "edit";
  episode?: Episode | null;
  isGeneratingDraft: boolean;
  isSubmitting: boolean;
  onClose: () => void;
  onGenerateDraft: (
    payload: Omit<EpisodeDraftGenerationPayload, "episode_id">
  ) => Promise<EpisodeDraftGenerationResponse>;
  onSubmit: (payload: EpisodeDraftPayload) => Promise<void>;
};

export function EpisodeEditorModal({
  isOpen,
  mode,
  episode,
  isGeneratingDraft,
  isSubmitting,
  onClose,
  onGenerateDraft,
  onSubmit
}: EpisodeEditorModalProps) {
  const [draftInstruction, setDraftInstruction] = useState("");
  const [draftError, setDraftError] = useState<string | null>(null);
  const {
    formState: { errors },
    getValues,
    handleSubmit,
    register,
    reset,
    setValue
  } = useForm<EpisodeFormValues>({
    resolver: zodResolver(episodeSchema),
    defaultValues: {
      title: "",
      premise: ""
    }
  });

  useEffect(() => {
    reset({
      title: episode?.title ?? "",
      premise: episode?.premise ?? ""
    });
    setDraftInstruction("");
    setDraftError(null);
  }, [episode, reset, isOpen]);

  const submit = handleSubmit(async (values) => {
    await onSubmit(values);
    reset({ title: "", premise: "" });
  });

  async function regenerateDraft() {
    const instruction = draftInstruction.trim();
    if (!instruction) {
      setDraftError("Tell the generator what you want to change.");
      return;
    }

    setDraftError(null);
    try {
      const draft = await onGenerateDraft({
        instruction,
        current_title: getValues("title"),
        current_premise: getValues("premise")
      });
      setValue("title", draft.title, { shouldDirty: true, shouldValidate: true });
      setValue("premise", draft.premise, { shouldDirty: true, shouldValidate: true });
    } catch (error) {
      setDraftError(errorMessage(error));
    }
  }

  return (
    <Modal
      description={
        mode === "add"
          ? "Add a curated episode to the model-generated plan."
          : "Adjust the editorial promise before the plan is locked."
      }
      isOpen={isOpen}
      onClose={onClose}
      title={mode === "add" ? "Add Episode" : "Edit Episode"}
    >
      <form className="space-y-4" onSubmit={(event) => void submit(event)}>
        <label className="block">
          <span className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
            Episode title
          </span>
          <input
            className="mt-2 w-full rounded-streamly-md border border-streamly-lavenderStrong px-3 py-2 text-sm font-semibold text-streamly-coal outline-none focus:border-streamly-electric focus:ring-2 focus:ring-streamly-lavender"
            {...register("title")}
          />
          {errors.title ? (
            <span className="mt-1 block text-xs font-bold text-red-700">
              {errors.title.message}
            </span>
          ) : null}
        </label>

        <label className="block">
          <span className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
            Premise
          </span>
          <textarea
            className="mt-2 min-h-32 w-full rounded-streamly-md border border-streamly-lavenderStrong px-3 py-2 text-sm font-semibold leading-6 text-streamly-coal outline-none focus:border-streamly-electric focus:ring-2 focus:ring-streamly-lavender"
            {...register("premise")}
          />
          {errors.premise ? (
            <span className="mt-1 block text-xs font-bold text-red-700">
              {errors.premise.message}
            </span>
          ) : null}
        </label>

        <section className="rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash/70 p-3">
          <div className="flex items-center gap-2 text-xs font-extrabold uppercase text-streamly-purpleBlue">
            <Sparkles aria-hidden className="h-4 w-4 text-streamly-electric" />
            Regenerate title and premise
          </div>
          <textarea
            className="mt-2 min-h-24 w-full rounded-streamly-md border border-streamly-lavenderStrong bg-white px-3 py-2 text-sm font-semibold leading-6 text-streamly-coal outline-none focus:border-streamly-electric focus:ring-2 focus:ring-streamly-lavender disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isGeneratingDraft || isSubmitting}
            onChange={(event) => setDraftInstruction(event.target.value)}
            placeholder="Example: make this more practical for CEOs and focus on client success tradeoffs."
            value={draftInstruction}
          />
          <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
            {draftError ? (
              <span className="text-xs font-bold text-red-700">{draftError}</span>
            ) : (
              <span className="text-xs font-bold text-streamly-purpleBlue">
                Uses the current title, premise, series, and selected narrative as context.
              </span>
            )}
            <button
              className="inline-flex items-center gap-2 rounded-streamly-pill bg-white px-3 py-2 text-xs font-extrabold text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-lavender disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isGeneratingDraft || isSubmitting}
              onClick={() => void regenerateDraft()}
              type="button"
            >
              {isGeneratingDraft ? (
                <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles aria-hidden className="h-4 w-4" />
              )}
              {isGeneratingDraft ? "Generating" : "Regenerate"}
            </button>
          </div>
        </section>

        <div className="flex flex-wrap justify-end gap-3 pt-2">
          <button
            className="rounded-streamly-pill px-4 py-2 text-sm font-extrabold text-streamly-purpleBlue hover:bg-streamly-wash"
            onClick={onClose}
            type="button"
          >
            Cancel
          </button>
          <button
            className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-electric px-4 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubmitting}
            type="submit"
          >
            <Save aria-hidden className="h-4 w-4" />
            {isSubmitting ? "Saving" : "Save episode"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Episode draft generation failed.";
}
