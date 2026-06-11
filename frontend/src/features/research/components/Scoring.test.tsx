import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  ScoreBreakdownPanel,
  ScoreExplanationPopover,
  WeakEvidenceWarning
} from "@/features/research/components/Scoring";

describe("research scoring components", () => {
  it("shows weak evidence warning for weak scores", () => {
    render(
      <ScoreBreakdownPanel
        score={{
          tier: "D",
          tier_score: 25,
          engagement_score: 20,
          freshness_score: 45,
          author_score: 30,
          composite_score: 30,
          confidence_level: "Weak",
          trend_score: null,
          trend_available: false,
          score_explanation_json: {
            explanation: "Composite score 30 = Tier 25 x 50%.",
            trend_available: false
          }
        }}
      />
    );

    expect(
      screen.getByText(/Evidence is weak. Review source quality before relying/)
    ).toBeInTheDocument();
    expect(screen.getByText("Trend not available")).toBeInTheDocument();
  });

  it("opens the score explanation popover", () => {
    render(
      <ScoreExplanationPopover
        explanation={{
          formula: "tier_score * 0.50",
          explanation: "Composite score 82 = Tier 90 x 50%.",
          trend_available: true
        }}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Why/i }));

    expect(screen.getByText("Composite score 82 = Tier 90 x 50%.")).toBeInTheDocument();
    expect(screen.getByText("tier_score * 0.50")).toBeInTheDocument();
  });

  it("renders the standalone weak evidence warning", () => {
    render(<WeakEvidenceWarning />);

    expect(screen.getByText(/Evidence is weak/)).toBeInTheDocument();
  });
});
