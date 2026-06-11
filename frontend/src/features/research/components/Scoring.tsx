import { useState } from "react";
import { AlertTriangle, ChevronDown, Info, TrendingUp } from "lucide-react";

import type {
  ResearchConfidenceLevel,
  ResearchScoreSummary,
  ScoreExplanation
} from "@/shared/types/research";

type ScoreLike = {
  tier: string | null;
  tier_score: number | null;
  engagement_score: number | null;
  freshness_score: number | null;
  author_score: number | null;
  composite_score: number | null;
  confidence_level: ResearchConfidenceLevel | null;
  trend_score: number | null;
  trend_available: boolean | null;
  score_explanation_json: ScoreExplanation | null;
};

const confidenceTone: Record<ResearchConfidenceLevel, string> = {
  High: "bg-emerald-50 text-emerald-700",
  Medium: "bg-streamly-lavender text-streamly-violet",
  Low: "bg-amber-50 text-amber-800",
  Weak: "bg-red-50 text-red-700"
};

const tierTone: Record<string, string> = {
  S: "bg-emerald-50 text-emerald-700",
  A: "bg-streamly-lavender text-streamly-violet",
  B: "bg-sky-50 text-sky-700",
  C: "bg-amber-50 text-amber-800",
  D: "bg-red-50 text-red-700"
};

export function CompositeScoreBadge({ score }: { score: number | null }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-streamly-pill bg-white px-3 py-1.5 text-xs font-extrabold text-streamly-coal shadow-[inset_0_0_0_1px_rgba(123,72,241,0.16)]">
      <span className="h-1.5 w-1.5 rounded-streamly-pill bg-streamly-electric" />
      Composite {score ?? 0}
    </span>
  );
}

export function ConfidenceLevelBadge({
  level
}: {
  level: ResearchConfidenceLevel | null;
}) {
  const safeLevel = level ?? "Weak";
  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 rounded-streamly-pill px-3 py-1.5 text-xs font-extrabold",
        confidenceTone[safeLevel]
      ].join(" ")}
    >
      <span className="h-1.5 w-1.5 rounded-streamly-pill bg-current opacity-70" />
      {safeLevel} confidence
    </span>
  );
}

export function TrendScoreBadge({
  available,
  score
}: {
  available: boolean | null;
  score: number | null;
}) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 rounded-streamly-pill px-3 py-1.5 text-xs font-extrabold",
        available ? "bg-streamly-lavender text-streamly-violet" : "bg-zinc-100 text-zinc-600"
      ].join(" ")}
    >
      <TrendingUp aria-hidden className="h-3.5 w-3.5" />
      {available ? `Trend ${score ?? 0}` : "Trend not available"}
    </span>
  );
}

export function TierBadge({ tier }: { tier: string | null }) {
  const safeTier = tier ?? "D";
  return (
    <span
      className={[
        "inline-flex items-center rounded-streamly-pill px-3 py-1.5 text-xs font-extrabold",
        tierTone[safeTier] ?? tierTone.D
      ].join(" ")}
    >
      Tier {safeTier}
    </span>
  );
}

export function ScoreExplanationPopover({
  explanation,
  showFormula = true,
  showMessage = true
}: {
  explanation: ScoreExplanation | null;
  showFormula?: boolean;
  showMessage?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const message = explanation?.explanation ?? "No score explanation is available yet.";
  const components = [
    ["Tier", explanation?.tier_score],
    ["Engagement", explanation?.engagement_score],
    ["Freshness", explanation?.freshness_score],
    ["Author", explanation?.author_score],
    ["Composite", explanation?.composite_score]
  ] as const;
  const hasComponents = components.some(([, value]) => typeof value === "number");
  return (
    <div className="relative inline-flex">
      <button
        className="inline-flex items-center gap-1.5 rounded-streamly-pill bg-streamly-wash px-3 py-1.5 text-xs font-extrabold text-streamly-purpleBlue transition hover:bg-streamly-lavender"
        onClick={() => setIsOpen((value) => !value)}
        type="button"
      >
        <Info aria-hidden className="h-3.5 w-3.5" />
        Why
        <ChevronDown aria-hidden className="h-3.5 w-3.5" />
      </button>
      {isOpen ? (
        <div className="absolute right-0 top-9 z-20 w-80 rounded-streamly-xl bg-white p-4 text-left shadow-streamly-soft ring-1 ring-streamly-lavenderStrong">
          <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
            Score explanation
          </p>
          {showMessage ? (
            <p className="mt-2 text-sm font-bold leading-6 text-streamly-coal">{message}</p>
          ) : null}
          {showFormula && explanation?.formula ? (
            <p className="mt-3 rounded-streamly-lg bg-streamly-wash p-3 text-xs font-bold leading-5 text-streamly-purpleBlue">
              {explanation.formula}
            </p>
          ) : null}
          {hasComponents ? (
            <dl className="mt-3 grid grid-cols-2 gap-2">
              {components.map(([label, value]) => (
                <div
                  className="rounded-streamly-lg bg-streamly-wash px-3 py-2"
                  key={label}
                >
                  <dt className="text-[0.65rem] font-extrabold uppercase text-streamly-purpleBlue">
                    {label}
                  </dt>
                  <dd className="mt-1 text-sm font-extrabold text-streamly-coal">
                    {typeof value === "number" ? value : "-"}
                  </dd>
                </div>
              ))}
            </dl>
          ) : null}
          {explanation?.trend_available === false ? (
            <p className="mt-3 text-xs font-bold leading-5 text-zinc-600">
              Trend not available. This does not block generation.
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function ScoreBreakdownPanel({
  score,
  title = "Score breakdown"
}: {
  score: ScoreLike;
  title?: string;
}) {
  return (
    <section className="rounded-streamly-xl bg-white p-5 shadow-streamly-card ring-1 ring-streamly-lavenderStrong">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="streamly-kicker">Explainability</p>
          <h3 className="font-streamly-platform text-lg font-extrabold text-streamly-coal">
            {title}
          </h3>
        </div>
        <div className="flex flex-wrap gap-2">
          <CompositeScoreBadge score={score.composite_score} />
          <ConfidenceLevelBadge level={score.confidence_level} />
        </div>
      </div>
      {score.confidence_level === "Weak" ? <WeakEvidenceWarning /> : null}
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <ScoreBar label="Tier" value={score.tier_score} />
        <ScoreBar label="Engagement" value={score.engagement_score} />
        <ScoreBar label="Freshness" value={score.freshness_score} />
        <ScoreBar label="Author" value={score.author_score} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <TierBadge tier={score.tier} />
        <TrendScoreBadge available={score.trend_available} score={score.trend_score} />
        <ScoreExplanationPopover explanation={score.score_explanation_json} />
      </div>
    </section>
  );
}

export function ConfidenceDistributionChart({
  distribution
}: {
  distribution: ResearchScoreSummary["confidence_distribution"];
}) {
  return (
    <DistributionChart
      distribution={distribution}
      labels={["High", "Medium", "Low", "Weak"]}
      title="Confidence distribution"
    />
  );
}

export function TierDistributionChart({
  distribution
}: {
  distribution: ResearchScoreSummary["tier_distribution"];
}) {
  return (
    <DistributionChart
      distribution={distribution}
      labels={["S", "A", "B", "C", "D"]}
      title="Tier distribution"
    />
  );
}

export function WeakEvidenceWarning() {
  return (
    <div className="mt-4 flex items-start gap-3 rounded-streamly-lg bg-red-50 px-4 py-3 text-sm font-bold leading-6 text-red-700">
      <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
      <span>Evidence is weak. Review source quality before relying on this recommendation.</span>
    </div>
  );
}

function ScoreBar({ label, value }: { label: string; value: number | null }) {
  const safeValue = Math.max(0, Math.min(value ?? 0, 100));
  return (
    <div className="rounded-streamly-lg bg-streamly-wash px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
          {label}
        </span>
        <span className="text-sm font-extrabold text-streamly-coal">{safeValue}</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-streamly-pill bg-white">
        <div
          className="h-full rounded-streamly-pill bg-streamly-electric"
          style={{ width: `${safeValue}%` }}
        />
      </div>
    </div>
  );
}

function DistributionChart({
  distribution,
  labels,
  title
}: {
  distribution: Record<string, number>;
  labels: string[];
  title: string;
}) {
  const total = labels.reduce((sum, label) => sum + (distribution[label] ?? 0), 0);
  return (
    <section className="rounded-streamly-xl bg-streamly-wash/70 p-4">
      <h3 className="font-streamly-platform text-base font-extrabold text-streamly-coal">
        {title}
      </h3>
      <div className="mt-4 space-y-3">
        {labels.map((label) => {
          const count = distribution[label] ?? 0;
          const width = total ? Math.round((count / total) * 100) : 0;
          return (
            <div key={label}>
              <div className="flex items-center justify-between gap-3 text-xs font-extrabold text-streamly-purpleBlue">
                <span>{label}</span>
                <span>{count}</span>
              </div>
              <div className="mt-1 h-2 overflow-hidden rounded-streamly-pill bg-white">
                <div
                  className="h-full rounded-streamly-pill bg-streamly-electric"
                  style={{ width: `${width}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
