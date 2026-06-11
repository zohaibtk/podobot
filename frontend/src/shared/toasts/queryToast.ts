import type { Mutation } from "@tanstack/react-query";

import { showToast, updateToast } from "@/shared/toasts/store";

export type MutationToastMessages = {
  failure?: string | false;
  processing?: string | false;
  success?: string | false;
};

export type MutationToastMeta = {
  toast?: MutationToastMessages;
};

const mutationToastIds = new WeakMap<object, string>();

export function mutationToast(
  processing: string,
  success: string,
  failure = "Action failed"
): MutationToastMeta {
  return {
    toast: {
      failure,
      processing,
      success
    }
  };
}

export function handleMutationToastStart(mutation: Mutation<unknown, unknown, unknown>) {
  const toast = mutationToastMeta(mutation);
  if (!toast?.processing) {
    return;
  }

  const toastId = showToast({
    durationMs: null,
    kind: "processing",
    title: toast.processing
  });
  mutationToastIds.set(mutation, toastId);
}

export function handleMutationToastSuccess(mutation: Mutation<unknown, unknown, unknown>) {
  const toast = mutationToastMeta(mutation);
  if (!toast?.success) {
    clearMutationToast(mutation);
    return;
  }

  const existingToastId = mutationToastIds.get(mutation);
  const payload = {
    kind: "success" as const,
    title: toast.success
  };
  if (existingToastId) {
    updateToast(existingToastId, payload);
  } else {
    showToast(payload);
  }
  clearMutationToast(mutation);
}

export function handleMutationToastFailure(
  mutation: Mutation<unknown, unknown, unknown>,
  error: unknown
) {
  const toast = mutationToastMeta(mutation);
  if (!toast?.failure) {
    clearMutationToast(mutation);
    return;
  }

  const existingToastId = mutationToastIds.get(mutation);
  const payload = {
    description: errorDescription(error),
    kind: "failure" as const,
    title: toast.failure
  };
  if (existingToastId) {
    updateToast(existingToastId, payload);
  } else {
    showToast(payload);
  }
  clearMutationToast(mutation);
}

function mutationToastMeta(mutation: Mutation<unknown, unknown, unknown>) {
  return (mutation.options.meta as MutationToastMeta | undefined)?.toast;
}

function clearMutationToast(mutation: Mutation<unknown, unknown, unknown>) {
  mutationToastIds.delete(mutation);
}

function errorDescription(error: unknown) {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Please try again.";
}
