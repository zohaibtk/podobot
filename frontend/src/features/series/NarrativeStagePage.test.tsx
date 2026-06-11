import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { NarrativeStagePage } from "@/features/series/NarrativeStagePage";
import type { DiscoveryWorkspace, Narrative } from "@/shared/types/series";

const hookMocks = vi.hoisted(() => ({
  regenerateState: {
    error: null as Error | null,
    isPending: false,
    mutate: vi.fn()
  },
  refetch: vi.fn(),
  selectState: {
    error: null as Error | null,
    isPending: false,
    mutate: vi.fn()
  },
  workspace: null as DiscoveryWorkspace | null
}));

vi.mock("@/features/series/hooks", () => ({
  useDiscoveryWorkspace: () => ({
    data: hookMocks.workspace,
    isError: false,
    isLoading: false,
    refetch: hookMocks.refetch
  }),
  useRegenerateNarratives: () => hookMocks.regenerateState,
  useSelectNarrative: () => hookMocks.selectState
}));

describe("NarrativeStagePage", () => {
  beforeEach(() => {
    hookMocks.refetch.mockReset();
    hookMocks.regenerateState.error = null;
    hookMocks.regenerateState.isPending = false;
    hookMocks.regenerateState.mutate.mockReset();
    hookMocks.selectState.error = null;
    hookMocks.selectState.isPending = false;
    hookMocks.selectState.mutate.mockReset();
    hookMocks.workspace = workspaceFixture(defaultNarratives());
  });

  it("shows the selection loader only on the clicked narrative", () => {
    const { rerender } = renderPage();

    fireEvent.click(
      within(cardFor("Option A")).getByRole("button", { name: "Select narrative" })
    );

    expect(hookMocks.selectState.mutate).toHaveBeenCalledWith(
      "narrative-a",
      expect.objectContaining({ onSettled: expect.any(Function) })
    );

    hookMocks.selectState.isPending = true;
    rerender(wrappedPage());

    const selectingButton = within(cardFor("Option A")).getByRole("button", {
      name: "Selecting narrative..."
    });
    expect(selectingButton).toBeDisabled();
    expect(selectingButton).toHaveAttribute("aria-busy", "true");
    expect(
      within(cardFor("Option B")).getByRole("button", { name: "Select narrative" })
    ).toBeDisabled();
    expect(
      within(cardFor("Option C")).getByRole("button", { name: "Selected narrative" })
    ).toBeDisabled();
  });

  it("keeps narrative cards in their existing positions after a selected refetch", () => {
    const { container, rerender } = renderPage();

    expect(cardTitles(container)).toEqual(["Option A", "Option B", "Option C"]);

    hookMocks.workspace = workspaceFixture([
      narrativeFixture({ id: "narrative-c", isSelected: true, title: "Option C" }),
      narrativeFixture({ id: "narrative-a", title: "Option A" }),
      narrativeFixture({ id: "narrative-b", title: "Option B" })
    ]);
    rerender(wrappedPage());

    expect(cardTitles(container)).toEqual(["Option A", "Option B", "Option C"]);
  });

  it("uses the selected narrative id as the selected card state", () => {
    hookMocks.workspace = {
      ...workspaceFixture([
        narrativeFixture({ id: "narrative-a", title: "Option A" }),
        narrativeFixture({ id: "narrative-b", title: "Option B" }),
        narrativeFixture({ id: "narrative-c", title: "Option C" })
      ]),
      selected_narrative_id: "narrative-b"
    };

    renderPage();

    expect(
      within(cardFor("Option B")).getByRole("button", { name: "Selected narrative" })
    ).toBeDisabled();
    expect(
      within(cardFor("Option A")).getByRole("button", { name: "Select narrative" })
    ).not.toBeDisabled();
  });

  it("disables narrative changes after the episode plan is locked", () => {
    hookMocks.workspace = {
      ...workspaceFixture(defaultNarratives()),
      series: {
        ...workspaceFixture(defaultNarratives()).series,
        plan_locked_at: "2026-06-09T00:00:00Z"
      }
    };

    renderPage();

    const lockedButton = within(cardFor("Option A")).getByRole("button", {
      name: "Plan locked"
    });
    expect(lockedButton).toBeDisabled();
    expect(lockedButton).toHaveAttribute(
      "title",
      "Narrative selection cannot change after the episode plan is locked."
    );
    expect(
      within(cardFor("Option C")).getByRole("button", { name: "Selected narrative" })
    ).toBeDisabled();
  });

  it("does not render narrative mutation errors as an inline banner", () => {
    hookMocks.selectState.error = new Error(
      "Episode plan generation failed: Gemini request failed with status 503"
    );

    renderPage();

    expect(screen.queryByText("Narrative action failed")).not.toBeInTheDocument();
    expect(
      screen.queryByText(
        "Episode plan generation failed: Gemini request failed with status 503"
      )
    ).not.toBeInTheDocument();
  });
});

function renderPage() {
  return render(wrappedPage());
}

function wrappedPage() {
  return (
    <MemoryRouter>
      <NarrativeStagePage seriesId="series-1" />
    </MemoryRouter>
  );
}

function cardFor(title: string) {
  const article = screen.getByRole("heading", { name: title }).closest("article");
  if (!article) {
    throw new Error(`Could not find card for ${title}.`);
  }
  return article;
}

function cardTitles(container: HTMLElement) {
  return Array.from(container.querySelectorAll("article h3")).map((heading) =>
    heading.textContent?.trim()
  );
}

function defaultNarratives() {
  return [
    narrativeFixture({ id: "narrative-a", title: "Option A" }),
    narrativeFixture({ id: "narrative-b", title: "Option B" }),
    narrativeFixture({ id: "narrative-c", isSelected: true, title: "Option C" })
  ];
}

function workspaceFixture(narratives: Narrative[]): DiscoveryWorkspace {
  return {
    ledger: [
      {
        id: "ledger-1",
        series_id: "series-1",
        source_name: "Source",
        source_type: "article",
        source_url: "https://example.com",
        status: "complete",
        signal_title: "Signal",
        signal_summary: "A useful signal.",
        confidence_score: 80,
        sort_order: 1,
        created_at: "2026-06-09T00:00:00Z",
        updated_at: "2026-06-09T00:00:00Z"
      }
    ],
    narratives,
    progress_percent: 100,
    research_activity: {
      documents_found: 1,
      documents_used: 1,
      latest_run: null,
      run_count: 1,
      sources_failed: 0,
      sources_queried: 1,
      sources_skipped: 0
    },
    selected_narrative_id: narratives.find((narrative) => narrative.is_selected)?.id ?? null,
    series: {
      audience: "Operators",
      briefs_approved_at: null,
      captions_unlocked_at: null,
      created_at: "2026-06-09T00:00:00Z",
      current_stage: "narrative",
      description: "A test series.",
      discovery_status: "complete",
      episode_plan_generated_at: null,
      guest_name: null,
      id: "series-1",
      name: "Series",
      plan_locked_at: null,
      scheduling_unlocked_at: null,
      status: "planning",
      updated_at: "2026-06-09T00:00:00Z"
    }
  };
}

function narrativeFixture({
  id,
  isSelected = false,
  title
}: {
  id: string;
  isSelected?: boolean;
  title: string;
}): Narrative {
  return {
    confidence_score: 72,
    created_at: "2026-06-09T00:00:00Z",
    generation: 1,
    id,
    is_selected: isSelected,
    selected_at: isSelected ? "2026-06-09T00:00:00Z" : null,
    series_id: "series-1",
    status: isSelected ? "selected" : "candidate",
    summary: `${title} summary.`,
    supporting_signals: [],
    thesis: `${title} thesis.`,
    title,
    updated_at: "2026-06-09T00:00:00Z"
  };
}
