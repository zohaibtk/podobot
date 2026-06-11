import { afterEach, describe, expect, it } from "vitest";

import {
  handleMutationToastFailure,
  handleMutationToastStart,
  handleMutationToastSuccess,
  mutationToast
} from "@/shared/toasts/queryToast";
import { clearToasts, getToasts } from "@/shared/toasts/store";

describe("query toast bridge", () => {
  afterEach(() => {
    clearToasts();
  });

  it("updates a processing toast into a success toast", () => {
    const mutation = mutationFixture(
      mutationToast("Saving profile", "Profile saved", "Profile save failed")
    );

    handleMutationToastStart(mutation);
    expect(getToasts()).toMatchObject([{ kind: "processing", title: "Saving profile" }]);

    handleMutationToastSuccess(mutation);
    expect(getToasts()).toMatchObject([{ kind: "success", title: "Profile saved" }]);
  });

  it("updates a processing toast into a failure toast with error context", () => {
    const mutation = mutationFixture(
      mutationToast("Saving profile", "Profile saved", "Profile save failed")
    );

    handleMutationToastStart(mutation);
    handleMutationToastFailure(mutation, new Error("Name is required"));

    expect(getToasts()).toMatchObject([
      {
        description: "Name is required",
        kind: "failure",
        title: "Profile save failed"
      }
    ]);
  });
});

function mutationFixture(meta: Record<string, unknown>) {
  return {
    options: { meta }
  } as Parameters<typeof handleMutationToastStart>[0];
}
