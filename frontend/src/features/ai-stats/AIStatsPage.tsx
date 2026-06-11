import {
  BarChart3,
  Bot,
  CircleDollarSign,
  Gauge,
  Info,
  RefreshCw,
  TrendingUp,
  Zap
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { PageHeader } from "@/design-system/components/PageHeader";
import { useAgentTokenStats } from "@/features/agents/hooks";
import type {
  AgentTokenRequestUsage,
  AgentTokenStats,
  AgentTokenStatsPeriod
} from "@/shared/types/agents";

const PERIOD_OPTIONS: Array<{ label: string; value: AgentTokenStatsPeriod }> = [
  { label: "Day", value: "day" },
  { label: "Week", value: "week" },
  { label: "Month", value: "month" }
];

const TOKEN_COLORS = {
  completion: "#2fbf9b",
  estimated: "#f59e0b",
  other: "#b999ff",
  prompt: "#8646ee"
};

const REQUEST_GRAPH_LIMIT = 30;
const COST_MODEL_LABEL = "Gemini 2.5 Flash";
const COST_LONG_CONTEXT_THRESHOLD = 200_000;
const TOKEN_COST_RATES_PER_MILLION = {
  longContext: {
    cachedInput: 0.1,
    input: 1,
    output: 10
  },
  standard: {
    cachedInput: 0.03,
    input: 0.3,
    output: 2.5
  }
};
const numberFormatter = new Intl.NumberFormat("en-US");
const compactFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 1,
  notation: "compact"
});
const currencyFormatter = new Intl.NumberFormat("en-US", {
  currency: "USD",
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
  style: "currency"
});
const preciseCurrencyFormatter = new Intl.NumberFormat("en-US", {
  currency: "USD",
  maximumFractionDigits: 6,
  minimumFractionDigits: 4,
  style: "currency"
});

type AgentRequestMetric = {
  agent_key: string;
  agent_name: string;
  average_tokens_per_request: number;
  captured_requests: number;
  estimated_requests: number;
  peak_request_detail: string;
  peak_request_display_label: string;
  peak_request_label: string;
  peak_request_tokens: number;
  request_count: number;
  total_tokens: number;
};

type SeriesRequestMetric = {
  captured_requests: number;
  chart_label: string;
  completion_tokens: number;
  estimated_requests: number;
  latest_request_label: string;
  other_tokens: number;
  peak_request_detail: string;
  peak_request_label: string;
  peak_request_tokens: number;
  prompt_tokens: number;
  request_count: number;
  request_count_label: string;
  series_id: string;
  series_name: string;
  total_tokens: number;
};

type CostAnalysis = {
  average_cost_per_request: number;
  cached_input_cost: number;
  cached_input_tokens: number;
  captured_cost: number;
  estimated_cost: number;
  input_cost: number;
  input_tokens: number;
  long_context_requests: number;
  output_cost: number;
  output_tokens: number;
  total_cost: number;
};

type RequestMetrics = {
  agent_metrics: AgentRequestMetric[];
  average_tokens_per_request: number;
  captured_request_count: number;
  cost_analysis: CostAnalysis;
  estimated_request_count: number;
  peak_request: AgentTokenRequestUsage | null;
  series_metrics: SeriesRequestMetric[];
  request_count: number;
  request_rows: AgentTokenRequestUsage[];
  total_request_tokens: number;
};

export function AIStatsPage() {
  const [period, setPeriod] = useState<AgentTokenStatsPeriod>("day");
  const statsQuery = useAgentTokenStats(period);
  const stats = statsQuery.data;
  const metrics = useMemo(() => (stats ? buildRequestMetrics(stats) : null), [stats]);

  if (statsQuery.isLoading) {
    return <LoadingState label="Loading AI stats" />;
  }

  if (statsQuery.isError || !stats || !metrics) {
    return (
      <ErrorState
        actionLabel="Retry"
        description="Token utilization could not be loaded."
        onAction={() => void statsQuery.refetch()}
        title="AI stats unavailable"
      />
    );
  }

  return (
    <main className="space-y-5">
      <PageHeader
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <PeriodSwitch period={period} onChange={setPeriod} />
            <button
              className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-electric px-3 py-2 text-sm font-extrabold text-white shadow-streamly-button disabled:opacity-50"
              disabled={statsQuery.isFetching}
              onClick={() => void statsQuery.refetch()}
              type="button"
            >
              <RefreshCw aria-hidden className="h-4 w-4" />
              Refresh
            </button>
          </div>
        }
        description={`${periodLabel(period)} token usage per agent request, with captured provider counts used before estimated request totals.`}
        kicker="AI Stats"
        title="Token Utilization"
      />

      <RequestSummary metrics={metrics} />
      <CostAnalysisPanel metrics={metrics} />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(22rem,0.65fr)]">
        <SeriesTokenColumnChart metrics={metrics} />
        <AgentAverageChart metrics={metrics} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <AgentRequestKpiPanel metrics={metrics} />
        <RequestSourcePanel metrics={metrics} stats={stats} />
      </div>
    </main>
  );
}

function PeriodSwitch({
  onChange,
  period
}: {
  onChange: (period: AgentTokenStatsPeriod) => void;
  period: AgentTokenStatsPeriod;
}) {
  return (
    <div className="inline-flex rounded-streamly-pill bg-streamly-lavender p-1">
      {PERIOD_OPTIONS.map((option) => (
        <button
          className={[
            "rounded-streamly-pill px-3 py-2 text-sm font-extrabold transition",
            period === option.value
              ? "bg-white text-streamly-violet shadow-streamly-card"
              : "text-streamly-purpleBlue hover:bg-white/70"
          ].join(" ")}
          key={option.value}
          onClick={() => onChange(option.value)}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function RequestSummary({ metrics }: { metrics: RequestMetrics }) {
  const peak = metrics.peak_request;
  const topAgent = metrics.agent_metrics[0];

  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <KpiCard
        icon={Zap}
        label="Request tokens"
        meta={`${formatNumber(metrics.request_count)} agent requests`}
        value={formatNumber(metrics.total_request_tokens)}
      />
      <KpiCard
        icon={Gauge}
        label="Avg/request"
        meta={`${formatNumber(metrics.estimated_request_count)} estimated requests`}
        value={formatNumber(metrics.average_tokens_per_request)}
      />
      <KpiCard
        icon={TrendingUp}
        label="Peak request"
        meta={peak ? `${peak.agent_name} · ${requestDate(peak)}` : "No requests"}
        value={formatNumber(peak?.display_total_tokens ?? 0)}
      />
      <KpiCard
        icon={Bot}
        label="Top agent avg"
        meta={topAgent ? `${topAgent.agent_name} · ${topAgent.request_count} requests` : "No agents"}
        value={formatNumber(topAgent?.average_tokens_per_request ?? 0)}
      />
    </section>
  );
}

function KpiCard({
  icon: Icon,
  label,
  meta,
  value
}: {
  icon: LucideIcon;
  label: string;
  meta: string;
  value: string;
}) {
  return (
    <article className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white/92 p-4 shadow-streamly-card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">{label}</p>
          <p className="mt-2 font-streamly-platform text-3xl font-extrabold text-streamly-coal">
            {value}
          </p>
        </div>
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric">
          <Icon aria-hidden className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-3 text-xs font-bold text-[var(--streamly-text-muted)]">{meta}</p>
    </article>
  );
}

function CostAnalysisPanel({ metrics }: { metrics: RequestMetrics }) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const cost = metrics.cost_analysis;

  return (
    <section className="streamly-premium-card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <PanelHeading
          badge={COST_MODEL_LABEL}
          icon={CircleDollarSign}
          kicker="Estimated cost"
          title="Token Cost Analysis"
        />
        <button
          aria-expanded={detailsOpen}
          aria-label={detailsOpen ? "Hide costing details" : "Show costing details"}
          className="grid h-10 w-10 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-violet transition hover:bg-streamly-electric hover:text-white"
          onClick={() => setDetailsOpen((isOpen) => !isOpen)}
          title={detailsOpen ? "Hide costing details" : "Show costing details"}
          type="button"
        >
          <Info aria-hidden className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MiniStat label="Estimated spend" value={formatCurrency(cost.total_cost)} />
        <MiniStat label="Input cost" value={formatCurrency(cost.input_cost)} />
        <MiniStat label="Output cost" value={formatCurrency(cost.output_cost)} />
        <MiniStat label="Avg/request" value={formatCurrency(cost.average_cost_per_request)} />
      </div>

      {detailsOpen ? (
        <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(16rem,0.7fr)]">
          <div className="rounded-streamly-xl bg-streamly-wash/65 p-4">
            <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
              Token buckets
            </p>
            <div className="mt-3 grid gap-2 text-xs font-bold text-streamly-purpleBlue sm:grid-cols-3">
              <MiniStat
                label="Prompt"
                value={`${formatNumber(cost.input_tokens)} / ${formatCurrency(cost.input_cost)}`}
              />
              <MiniStat
                label="Cached"
                value={`${formatNumber(cost.cached_input_tokens)} / ${formatCurrency(
                  cost.cached_input_cost
                )}`}
              />
              <MiniStat
                label="Output"
                value={`${formatNumber(cost.output_tokens)} / ${formatCurrency(
                  cost.output_cost
                )}`}
              />
            </div>
          </div>

          <div className="rounded-streamly-xl bg-streamly-wash/65 p-4">
            <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
              Billing split
            </p>
            <div className="mt-3 grid gap-2 text-xs font-bold text-streamly-purpleBlue sm:grid-cols-3">
              <MiniStat label="Captured" value={formatCurrency(cost.captured_cost)} />
              <MiniStat label="Estimated" value={formatCurrency(cost.estimated_cost)} />
              <MiniStat label="Long prompts" value={formatNumber(cost.long_context_requests)} />
            </div>
          </div>

          <div className="rounded-streamly-xl bg-streamly-wash/65 p-4">
            <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
              Rates per 1M
            </p>
            <div className="mt-3 space-y-2 text-xs font-bold text-streamly-purpleBlue">
              <div className="flex items-center justify-between gap-3 rounded-streamly-lg bg-white/78 px-3 py-2">
                <span>Prompt</span>
                <span className="text-streamly-coal">
                  {formatTieredRate("input")}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3 rounded-streamly-lg bg-white/78 px-3 py-2">
                <span>Cached</span>
                <span className="text-streamly-coal">
                  {formatTieredRate("cachedInput")}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3 rounded-streamly-lg bg-white/78 px-3 py-2">
                <span>Output</span>
                <span className="text-streamly-coal">
                  {formatTieredRate("output")}
                </span>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function SeriesTokenColumnChart({ metrics }: { metrics: RequestMetrics }) {
  const chartRows = metrics.series_metrics.slice(0, REQUEST_GRAPH_LIMIT);
  const topSeries = chartRows[0];

  return (
    <section className="streamly-premium-card min-w-0">
      <PanelHeading
        badge={`${formatNumber(chartRows.length)} series`}
        icon={BarChart3}
        kicker="Series usage"
        title="Series Request Token Usage"
      />

      {chartRows.length ? (
        <>
          <div className="mt-5 grid gap-5 2xl:grid-cols-[minmax(0,1fr)_17rem]">
            <div className="h-80 min-w-0 overflow-x-auto pb-2">
              <div className="h-full min-w-[30rem]">
                <ResponsiveContainer height="100%" width="100%">
                  <BarChart
                    barCategoryGap="30%"
                    data={chartRows}
                    margin={{ bottom: 20, left: 4, right: 18, top: 18 }}
                  >
                    <CartesianGrid stroke="#efe7ff" vertical={false} />
                    <XAxis
                      dataKey="chart_label"
                      height={44}
                      interval={0}
                      label={{
                        fill: "#51417d",
                        fontSize: 11,
                        fontWeight: 800,
                        offset: -6,
                        position: "insideBottom",
                        value: "Series"
                      }}
                      tick={{ fill: "#51417d", fontSize: 11, fontWeight: 800 }}
                      tickLine={false}
                    />
                    <YAxis
                      allowDecimals={false}
                      label={{
                        angle: -90,
                        fill: "#51417d",
                        fontSize: 11,
                        fontWeight: 800,
                        position: "insideLeft",
                        value: "Token count"
                      }}
                      tick={{ fill: "#51417d", fontSize: 11, fontWeight: 700 }}
                      tickFormatter={(value) => formatCompactNumber(Number(value))}
                      tickLine={false}
                    />
                    <Tooltip content={<SeriesTokenTooltip />} />
                    <Bar
                      dataKey="prompt_tokens"
                      fill={TOKEN_COLORS.prompt}
                      name="Prompt tokens"
                      radius={[0, 0, 0, 0]}
                      stackId="tokens"
                    />
                    <Bar
                      dataKey="completion_tokens"
                      fill={TOKEN_COLORS.completion}
                      name="Completion tokens"
                      radius={[0, 0, 0, 0]}
                      stackId="tokens"
                    />
                    <Bar
                      dataKey="other_tokens"
                      fill={TOKEN_COLORS.other}
                      name="Other tokens"
                      radius={[8, 8, 0, 0]}
                      stackId="tokens"
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="rounded-streamly-xl bg-streamly-lavender/80 p-5">
              <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
                Top series
              </p>
              <p className="mt-3 font-streamly-platform text-5xl font-extrabold text-streamly-coal">
                {formatCompactNumber(topSeries?.total_tokens ?? 0)}
              </p>
              <p className="mt-4 text-sm font-extrabold leading-6 text-streamly-purpleBlue">
                {topSeries?.series_name ?? "No series"}
              </p>
              <div className="mt-5 grid gap-2 text-xs font-bold text-streamly-purpleBlue">
                <MiniStat
                  label="Request hits"
                  value={formatNumber(topSeries?.request_count ?? 0)}
                />
                <MiniStat label="Prompt" value={formatNumber(topSeries?.prompt_tokens ?? 0)} />
                <MiniStat
                  label="Completion"
                  value={formatNumber(topSeries?.completion_tokens ?? 0)}
                />
                <MiniStat
                  label="Peak request"
                  title={topSeries?.peak_request_detail}
                  value={topSeries?.series_name ?? "None"}
                />
              </div>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-3 text-xs font-extrabold text-streamly-purpleBlue">
            <LegendDot color={TOKEN_COLORS.prompt} label="Prompt tokens" />
            <LegendDot color={TOKEN_COLORS.completion} label="Completion tokens" />
            <LegendDot color={TOKEN_COLORS.other} label="Other tokens" />
          </div>
        </>
      ) : (
        <EmptyState
          description="No series requests were recorded in this period."
          title="No series usage yet"
        />
      )}
    </section>
  );
}

function AgentAverageChart({ metrics }: { metrics: RequestMetrics }) {
  const chartRows = metrics.agent_metrics.map((agent) => ({
    ...agent,
    chart_label: agent.agent_name.replace(" Agent", "")
  }));

  return (
    <section className="streamly-premium-card min-w-0">
      <PanelHeading icon={Gauge} kicker="Agent KPI" title="Avg Tokens Per Request" />

      {chartRows.length ? (
        <div className="mt-5 h-72 min-w-0">
          <ResponsiveContainer height="100%" width="100%">
            <BarChart data={chartRows} margin={{ bottom: 0, left: 0, right: 12, top: 12 }}>
              <CartesianGrid stroke="#efe7ff" vertical={false} />
              <XAxis
                dataKey="chart_label"
                tick={{ fill: "#51417d", fontSize: 11, fontWeight: 800 }}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fill: "#51417d", fontSize: 11, fontWeight: 700 }}
                tickFormatter={(value) => formatCompactNumber(Number(value))}
                tickLine={false}
              />
              <Tooltip content={<AgentAverageTooltip />} />
              <Bar
                dataKey="average_tokens_per_request"
                fill={TOKEN_COLORS.prompt}
                name="Avg/request"
                radius={[8, 8, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <EmptyState description="No agents have request usage in this period." title="No agents" />
      )}
    </section>
  );
}

function AgentRequestKpiPanel({ metrics }: { metrics: RequestMetrics }) {
  return (
    <section className="streamly-premium-card">
      <PanelHeading
        badge={`${formatNumber(metrics.agent_metrics.length)} agents`}
        icon={Bot}
        kicker="Agent request KPIs"
        title="Per-Agent Token Usage"
      />

      {metrics.agent_metrics.length ? (
        <div className="mt-5 grid gap-3 2xl:grid-cols-2">
          {metrics.agent_metrics.map((agent) => (
            <article
              className="rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash/55 p-4"
              key={agent.agent_key}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-streamly-platform text-base font-extrabold text-streamly-coal">
                    {agent.agent_name}
                  </h3>
                  <p className="mt-1 text-xs font-bold uppercase text-streamly-purpleBlue">
                    {formatNumber(agent.request_count)} requests
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-streamly-platform text-2xl font-extrabold text-streamly-violet">
                    {formatNumber(agent.average_tokens_per_request)}
                  </p>
                  <p className="text-xs font-extrabold text-[var(--streamly-text-muted)]">
                    avg/request
                  </p>
                </div>
              </div>
              <div className="mt-4 grid gap-2 text-xs font-bold text-streamly-purpleBlue sm:grid-cols-3">
                <MiniStat label="Total" value={formatNumber(agent.total_tokens)} />
                <MiniStat label="Peak" value={formatNumber(agent.peak_request_tokens)} />
                <MiniStat
                  label="Peak run"
                  title={agent.peak_request_detail}
                  value={agent.peak_request_display_label}
                />
                <MiniStat label="Captured" value={formatNumber(agent.captured_requests)} />
                <MiniStat label="Estimated" value={formatNumber(agent.estimated_requests)} />
                <MiniStat
                  label="Capture"
                  value={`${percentage(agent.captured_requests, agent.request_count)}%`}
                />
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState description="No request usage was recorded in this period." title="No usage" />
      )}
    </section>
  );
}

function RequestSourcePanel({
  metrics,
  stats
}: {
  metrics: RequestMetrics;
  stats: AgentTokenStats;
}) {
  const recentRequests = metrics.request_rows.slice(-6).reverse();
  const captureCoverage = percentage(metrics.captured_request_count, metrics.request_count);

  return (
    <aside className="streamly-premium-card">
      <PanelHeading icon={TrendingUp} kicker="Request source" title="Capture Quality" />

      <div className="mt-5 space-y-4">
        <Meter
          detail={`${formatNumber(metrics.captured_request_count)} captured - ${formatNumber(metrics.estimated_request_count)} estimated`}
          label="Provider token capture"
          value={`${captureCoverage}%`}
          width={captureCoverage}
        />
        <Meter
          detail={`${formatNumber(metrics.total_request_tokens)} tokens across selected requests`}
          label="Request window"
          value={periodWindowLabel(stats)}
          width={100}
        />
      </div>

      <div className="mt-6">
        <h3 className="font-streamly-platform text-base font-extrabold text-streamly-coal">
          Recent Requests
        </h3>
        <div className="mt-3 space-y-2">
          {recentRequests.length ? (
            recentRequests.map((request) => {
              const detail = requestDetail(request);
              return (
                <div
                  className="rounded-streamly-lg bg-streamly-wash/70 px-3 py-2 text-xs font-bold"
                  key={request.id}
                  title={detail}
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className="min-w-0 truncate text-streamly-purpleBlue">
                      {requestContextLabel(request)}
                    </span>
                    <span className="text-streamly-coal">
                      {formatNumber(request.display_total_tokens)}
                    </span>
                  </div>
                  <p className="mt-1 text-[10px] font-extrabold uppercase text-[var(--streamly-text-muted)]">
                    {request.is_estimated ? "Estimated" : "Captured"} - {request.agent_name} -{" "}
                    {requestDate(request)}
                  </p>
                </div>
              );
            })
          ) : (
            <p className="text-xs font-bold leading-5 text-[var(--streamly-text-muted)]">
              No recent request rows in this period.
            </p>
          )}
        </div>
      </div>
    </aside>
  );
}

function PanelHeading({
  badge,
  icon: Icon,
  kicker,
  title
}: {
  badge?: string;
  icon: LucideIcon;
  kicker: string;
  title: string;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric">
          <Icon aria-hidden className="h-4 w-4" />
        </span>
        <div>
          <p className="streamly-kicker">{kicker}</p>
          <h2 className="mt-1 font-streamly-platform text-xl font-extrabold text-streamly-coal">
            {title}
          </h2>
        </div>
      </div>
      {badge ? (
        <span className="rounded-streamly-pill bg-streamly-lavender px-3 py-1.5 text-xs font-extrabold text-streamly-violet">
          {badge}
        </span>
      ) : null}
    </div>
  );
}

function MiniStat({ label, title, value }: { label: string; title?: string; value: string }) {
  return (
    <div className="rounded-streamly-lg bg-white/78 px-3 py-2" title={title}>
      <span className="block text-[10px] font-extrabold uppercase text-[var(--streamly-text-muted)]">
        {label}
      </span>
      <span
        className={[
          "mt-1 block break-words leading-4 text-streamly-coal",
          title ? "cursor-help decoration-dotted underline-offset-2 hover:underline" : ""
        ].join(" ")}
      >
        {value}
      </span>
    </div>
  );
}

function Meter({
  detail,
  label,
  value,
  width
}: {
  detail: string;
  label: string;
  value: string;
  width: number;
}) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between gap-3">
        <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">{label}</p>
        <p className="text-xs font-extrabold text-streamly-coal">{value}</p>
      </div>
      <div className="h-2 overflow-hidden rounded-streamly-pill bg-streamly-wash">
        <div
          className="h-full rounded-streamly-pill bg-streamly-electric"
          style={{ width: `${boundedProgress(width)}%` }}
        />
      </div>
      <p className="mt-1 text-xs font-bold leading-5 text-[var(--streamly-text-muted)]">
        {detail}
      </p>
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="h-2 w-2 rounded-streamly-pill" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}

function SeriesTokenTooltip({
  active,
  payload
}: {
  active?: boolean;
  payload?: Array<{ payload?: SeriesRequestMetric }>;
}) {
  const row = payload?.[0]?.payload;
  if (!active || !row) {
    return null;
  }
  return (
    <div className="rounded-streamly-lg border border-streamly-lavenderStrong bg-white px-3 py-2 shadow-streamly-card">
      <p className="text-xs font-extrabold text-streamly-coal">{row.series_name}</p>
      <p className="mt-1 text-xs font-bold text-streamly-purpleBlue">
        Requests hit: {row.request_count_label}
      </p>
      <p className="mt-1 text-xs font-bold text-streamly-purpleBlue">
        Total tokens: {formatNumber(row.total_tokens)}
      </p>
      <p className="text-xs font-bold text-streamly-purpleBlue">
        Prompt: {formatNumber(row.prompt_tokens)}
      </p>
      <p className="text-xs font-bold text-streamly-purpleBlue">
        Completion: {formatNumber(row.completion_tokens)}
      </p>
      {row.other_tokens ? (
        <p className="text-xs font-bold text-streamly-purpleBlue">
          Other: {formatNumber(row.other_tokens)}
        </p>
      ) : null}
      <p className="mt-1 text-[10px] font-extrabold uppercase text-[var(--streamly-text-muted)]">
        {formatNumber(row.captured_requests)} captured -{" "}
        {formatNumber(row.estimated_requests)} estimated
      </p>
    </div>
  );
}

function AgentAverageTooltip({
  active,
  payload
}: {
  active?: boolean;
  payload?: Array<{ payload?: AgentRequestMetric }>;
}) {
  const agent = payload?.[0]?.payload;
  if (!active || !agent) {
    return null;
  }
  return (
    <div className="rounded-streamly-lg border border-streamly-lavenderStrong bg-white px-3 py-2 shadow-streamly-card">
      <p className="text-xs font-extrabold text-streamly-coal">{agent.agent_name}</p>
      <p className="mt-1 text-xs font-bold text-streamly-purpleBlue">
        Avg/request: {formatNumber(agent.average_tokens_per_request)}
      </p>
      <p className="text-xs font-bold text-streamly-purpleBlue">
        Total: {formatNumber(agent.total_tokens)}
      </p>
      <p className="text-xs font-bold text-streamly-purpleBlue">
        Peak: {formatNumber(agent.peak_request_tokens)}
      </p>
    </div>
  );
}

function buildRequestMetrics(stats: AgentTokenStats): RequestMetrics {
  const requestRows = [...(stats.requests ?? [])].sort(
    (left, right) =>
      new Date(left.completed_at ?? left.created_at).getTime() -
      new Date(right.completed_at ?? right.created_at).getTime()
  );
  const totalRequestTokens = requestRows.reduce(
    (total, request) => total + request.display_total_tokens,
    0
  );
  const costAnalysis = buildCostAnalysis(requestRows);
  const capturedRequestCount = requestRows.filter(
    (request) => !request.is_estimated && request.total_tokens > 0
  ).length;
  const estimatedRequestCount = requestRows.filter((request) => request.is_estimated).length;
  const peakRequest = requestRows.reduce<AgentTokenRequestUsage | null>(
    (peak, request) =>
      !peak || request.display_total_tokens > peak.display_total_tokens ? request : peak,
    null
  );

  const agents = new Map<string, AgentRequestMetric>();
  const series = new Map<string, SeriesRequestMetric>();
  for (const request of requestRows) {
    const current =
      agents.get(request.agent_key) ??
      ({
        agent_key: request.agent_key,
        agent_name: request.agent_name,
        average_tokens_per_request: 0,
        captured_requests: 0,
        estimated_requests: 0,
        peak_request_detail: requestDetail(request),
        peak_request_display_label: requestContextLabel(request),
        peak_request_label: request.label,
        peak_request_tokens: 0,
        request_count: 0,
        total_tokens: 0
      } satisfies AgentRequestMetric);

    current.request_count += 1;
    current.total_tokens += request.display_total_tokens;
    current.captured_requests += !request.is_estimated && request.total_tokens > 0 ? 1 : 0;
    current.estimated_requests += request.is_estimated ? 1 : 0;
    if (request.display_total_tokens > current.peak_request_tokens) {
      current.peak_request_tokens = request.display_total_tokens;
      current.peak_request_label = request.label;
      current.peak_request_display_label = requestContextLabel(request);
      current.peak_request_detail = requestDetail(request);
    }
    agents.set(request.agent_key, current);

    const seriesId = requestSeriesId(request);
    if (!seriesId) {
      continue;
    }
    const seriesName = requestSeriesLabel(request, seriesId);
    const otherTokens = requestOtherTokens(request);
    const currentSeries =
      series.get(seriesId) ??
      ({
        captured_requests: 0,
        chart_label: seriesName,
        completion_tokens: 0,
        estimated_requests: 0,
        latest_request_label: request.label,
        other_tokens: 0,
        peak_request_detail: requestDetail(request),
        peak_request_label: request.label,
        peak_request_tokens: 0,
        prompt_tokens: 0,
        request_count: 0,
        request_count_label: "0 requests",
        series_id: seriesId,
        series_name: seriesName,
        total_tokens: 0
      } satisfies SeriesRequestMetric);

    currentSeries.request_count += 1;
    currentSeries.request_count_label = `${formatNumber(currentSeries.request_count)} ${
      currentSeries.request_count === 1 ? "request" : "requests"
    }`;
    currentSeries.total_tokens += request.display_total_tokens;
    currentSeries.prompt_tokens += request.display_prompt_tokens;
    currentSeries.completion_tokens += request.display_completion_tokens;
    currentSeries.other_tokens += otherTokens;
    currentSeries.captured_requests += !request.is_estimated && request.total_tokens > 0 ? 1 : 0;
    currentSeries.estimated_requests += request.is_estimated ? 1 : 0;
    currentSeries.latest_request_label = request.label;
    if (request.display_total_tokens > currentSeries.peak_request_tokens) {
      currentSeries.peak_request_tokens = request.display_total_tokens;
      currentSeries.peak_request_label = request.label;
      currentSeries.peak_request_detail = requestDetail(request);
    }
    series.set(seriesId, currentSeries);
  }

  const agentMetrics = Array.from(agents.values())
    .map((agent) => ({
      ...agent,
      average_tokens_per_request: agent.request_count
        ? Math.round(agent.total_tokens / agent.request_count)
        : 0
    }))
    .sort((left, right) => right.average_tokens_per_request - left.average_tokens_per_request);
  const seriesMetrics = Array.from(series.values()).sort((left, right) => {
    if (right.total_tokens !== left.total_tokens) {
      return right.total_tokens - left.total_tokens;
    }
    if (right.request_count !== left.request_count) {
      return right.request_count - left.request_count;
    }
    return left.series_name.localeCompare(right.series_name);
  });

  return {
    agent_metrics: agentMetrics,
    average_tokens_per_request: requestRows.length
      ? Math.round(totalRequestTokens / requestRows.length)
      : 0,
    captured_request_count: capturedRequestCount,
    cost_analysis: costAnalysis,
    estimated_request_count: estimatedRequestCount,
    peak_request: peakRequest,
    series_metrics: seriesMetrics,
    request_count: requestRows.length,
    request_rows: requestRows,
    total_request_tokens: totalRequestTokens
  };
}

function buildCostAnalysis(requestRows: AgentTokenRequestUsage[]): CostAnalysis {
  const cost = requestRows.reduce<CostAnalysis>(
    (current, request) => {
      const cachedInputTokens = request.cached_tokens;
      const inputTokens = Math.max(request.display_prompt_tokens - cachedInputTokens, 0);
      const outputTokens = request.display_completion_tokens + request.reasoning_tokens;
      const requestRates = getRequestCostRates(request.display_prompt_tokens);
      const inputCost = costForTokens(inputTokens, requestRates.input);
      const cachedInputCost = costForTokens(
        cachedInputTokens,
        requestRates.cachedInput
      );
      const outputCost = costForTokens(outputTokens, requestRates.output);
      const requestCost = inputCost + cachedInputCost + outputCost;

      current.input_tokens += inputTokens;
      current.cached_input_tokens += cachedInputTokens;
      current.output_tokens += outputTokens;
      current.input_cost += inputCost;
      current.cached_input_cost += cachedInputCost;
      current.output_cost += outputCost;
      current.total_cost += requestCost;
      if (request.is_estimated) {
        current.estimated_cost += requestCost;
      } else {
        current.captured_cost += requestCost;
      }
      current.long_context_requests +=
        request.display_prompt_tokens > COST_LONG_CONTEXT_THRESHOLD ? 1 : 0;
      return current;
    },
    {
      average_cost_per_request: 0,
      cached_input_cost: 0,
      cached_input_tokens: 0,
      captured_cost: 0,
      estimated_cost: 0,
      input_cost: 0,
      input_tokens: 0,
      long_context_requests: 0,
      output_cost: 0,
      output_tokens: 0,
      total_cost: 0
    }
  );

  return {
    ...cost,
    average_cost_per_request: requestRows.length ? cost.total_cost / requestRows.length : 0
  };
}

function requestSeriesId(request: AgentTokenRequestUsage) {
  if (request.entity_type !== "series") {
    return null;
  }
  return request.series_id ?? request.entity_id;
}

function requestSeriesLabel(request: AgentTokenRequestUsage, seriesId: string) {
  const seriesName = request.series_name?.trim();
  return seriesName || `Series ${seriesId.slice(0, 8)}`;
}

function requestContextLabel(request: AgentTokenRequestUsage) {
  const seriesId = requestSeriesId(request);
  if (seriesId) {
    return requestSeriesLabel(request, seriesId);
  }
  if (request.entity_type) {
    return humanizeLabel(request.entity_type);
  }
  return request.workflow_stage ? humanizeLabel(request.workflow_stage) : "Workspace";
}

function requestDetail(request: AgentTokenRequestUsage) {
  return [
    `Request: ${request.label}`,
    `Context: ${requestContextLabel(request)}`,
    `Agent: ${request.agent_name}`,
    `Stage: ${request.workflow_stage ? humanizeLabel(request.workflow_stage) : "None"}`,
    `Date: ${requestDate(request)}`,
    `Source: ${request.is_estimated ? "Estimated" : "Captured"}`,
    `Prompt tokens: ${formatNumber(request.display_prompt_tokens)}`,
    `Completion tokens: ${formatNumber(request.display_completion_tokens)}`,
    `Total tokens: ${formatNumber(request.display_total_tokens)}`
  ].join("\n");
}

function humanizeLabel(value: string) {
  return value
    .trim()
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function requestOtherTokens(request: AgentTokenRequestUsage) {
  return Math.max(
    request.display_total_tokens -
      request.display_prompt_tokens -
      request.display_completion_tokens,
    0
  );
}

function boundedProgress(value: number) {
  if (!Number.isFinite(value) || value <= 0) {
    return 0;
  }
  return Math.min(Math.max(value, 4), 100);
}

function percentage(value: number, total: number) {
  if (!total) {
    return 0;
  }
  return Math.round((value / total) * 100);
}

function formatNumber(value: number) {
  return numberFormatter.format(value);
}

function formatCompactNumber(value: number) {
  return compactFormatter.format(value);
}

function costForTokens(tokens: number, ratePerMillion: number) {
  return (tokens / 1_000_000) * ratePerMillion;
}

function getRequestCostRates(promptTokens: number) {
  return promptTokens > COST_LONG_CONTEXT_THRESHOLD
    ? TOKEN_COST_RATES_PER_MILLION.longContext
    : TOKEN_COST_RATES_PER_MILLION.standard;
}

function formatCurrency(value: number) {
  if (Math.abs(value) < 1 && value !== 0) {
    return preciseCurrencyFormatter.format(value);
  }
  return currencyFormatter.format(value);
}

function formatTieredRate(rateKey: "cachedInput" | "input" | "output") {
  return `${currencyFormatter.format(
    TOKEN_COST_RATES_PER_MILLION.standard[rateKey]
  )} <=200K / ${currencyFormatter.format(TOKEN_COST_RATES_PER_MILLION.longContext[rateKey])} >200K`;
}

function requestDate(request: AgentTokenRequestUsage) {
  return formatDate(request.completed_at ?? request.created_at);
}

function formatDate(value: string | null) {
  if (!value) {
    return "None";
  }
  return new Date(value).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short"
  });
}

function periodWindowLabel(stats: AgentTokenStats) {
  return `${formatDate(stats.window_start)} to ${formatDate(stats.window_end)}`;
}

function periodLabel(period: AgentTokenStatsPeriod) {
  if (period === "day") {
    return "Daily";
  }
  if (period === "week") {
    return "Weekly";
  }
  return "Monthly";
}
