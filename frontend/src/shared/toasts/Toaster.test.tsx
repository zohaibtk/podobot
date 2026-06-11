import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { Toaster } from "@/shared/toasts/Toaster";
import { clearToasts, showToast } from "@/shared/toasts/store";

describe("Toaster", () => {
  afterEach(() => {
    clearToasts();
  });

  it("renders concise processing, success, and failure notifications", () => {
    showToast({ durationMs: null, kind: "processing", title: "Running discovery" });
    showToast({ kind: "success", title: "Profile saved" });
    showToast({
      description: "File type is not supported.",
      kind: "failure",
      title: "Upload failed"
    });

    render(<Toaster />);

    expect(screen.getByText("Running discovery")).toBeInTheDocument();
    expect(screen.getByText("Profile saved")).toBeInTheDocument();
    expect(screen.getByText("Upload failed")).toBeInTheDocument();
    expect(screen.getByText("File type is not supported.")).toBeInTheDocument();
  });
});
