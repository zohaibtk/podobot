import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Activity,
  BarChart3,
  CalendarDays,
  Gauge,
  Info,
  Layers3,
  Radio,
  TrendingUp
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  CartesianGrid,
  Area,
  AreaChart,
  Bar,
  BarChart,
  ComposedChart,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { PageHeader } from "@/design-system/components/PageHeader";
import { useDashboardAnalytics } from "@/features/dashboard/hooks";
import type {
  ConfidencePoint,
  DashboardAnalytics,
  DashboardGroupBy,
  DashboardRange,
  EpisodeVelocityPoint,
  PipelineStage,
  PublishingVelocityPoint,
  ResearchOverview as ResearchOverviewData,
  SeriesVelocityPoint
} from "@/shared/types/dashboard";

const RANGE_OPTIONS: Array<{ label: string; value: DashboardRange }> = [
  { label: "Today", value: "today" },
  { label: "7 Days", value: "7d" },
  { label: "30 Days", value: "30d" },
  { label: "90 Days", value: "90d" },
  { label: "Custom", value: "custom" }
];

const TREND_VIEW_OPTIONS: Array<{ label: string; value: DashboardGroupBy }> = [
  { label: "Day", value: "day" },
  { label: "Week", value: "week" },
  { label: "Month", value: "month" }
];

const PUBLISHING_COLORS = {
  scheduled: "#8646ee",
  published: "#2fbf9b"
};

const RANGE_STORAGE_KEY = "podobot.dashboard.range";
const GROUP_STORAGE_KEY = "podobot.dashboard.group_by";
const START_STORAGE_KEY = "podobot.dashboard.start_date";
const END_STORAGE_KEY = "podobot.dashboard.end_date";

export function DashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const range = useDashboardRange(searchParams.get("range"));
  const groupBy = useTrendGroupBy(searchParams.get("group_by"), range);
  const startDate = useDashboardDate(searchParams.get("start_date"), START_STORAGE_KEY, daysAgo(30));
  const endDate = useDashboardDate(searchParams.get("end_date"), END_STORAGE_KEY, todayDate());

  const dashboardQuery = useMemo(
    () => ({
      range,
      groupBy,
      ...(range === "custom" ? { startDate, endDate } : {})
    }),
    [endDate, groupBy, range, startDate]
  );

  const { data, isLoading, isError, refetch } = useDashboardAnalytics(dashboardQuery);

  useEffect(() => {
    const nextParams = dashboardSearchParams(range, groupBy, startDate, endDate);
    window.localStorage.setItem(RANGE_STORAGE_KEY, range);
    window.localStorage.setItem(GROUP_STORAGE_KEY, groupBy);
    window.localStorage.setItem(START_STORAGE_KEY, startDate);
    window.localStorage.setItem(END_STORAGE_KEY, endDate);
    if (searchParams.toString() !== nextParams.toString()) {
      setSearchParams(nextParams, { replace: true });
    }
  }, [endDate, groupBy, range, searchParams, setSearchParams, startDate]);

  function updateDashboardParams(next: {
    endDate?: string;
    groupBy?: DashboardGroupBy;
    range?: DashboardRange;
    startDate?: string;
  }) {
    const nextRange = next.range ?? range;
    const nextGroupBy = next.groupBy ?? groupBy;
    const nextStartDate = next.startDate ?? startDate;
    const nextEndDate = next.endDate ?? endDate;
    setSearchParams(
      dashboardSearchParams(nextRange, nextGroupBy, nextStartDate, nextEndDate)
    );
  }

  return (
    <section className="streamly-page">
      <PageHeader
        actions={
          <DateFilter
            endDate={endDate}
            onChange={updateDashboardParams}
            range={range}
            startDate={startDate}
          />
        }
        description="What needs attention, where work is blocked, and whether research and publishing are healthy."
        kicker="Executive Overview"
        title="Dashboard"
      />

      {isLoading ? <DashboardSkeleton /> : null}

      {isError ? (
        <ErrorState
          actionLabel="Retry"
          description="The dashboard could not load operational metrics."
          onAction={() => void refetch()}
          title="Dashboard unavailable"
        />
      ) : null}

      {!isLoading && !isError && data ? (
        <DashboardContent
          data={data}
          groupBy={groupBy}
          onGroupByChange={(nextGroupBy) => updateDashboardParams({ groupBy: nextGroupBy })}
        />
      ) : null}
    </section>
  );
}

function DashboardContent({
  data,
  groupBy,
  onGroupByChange
}: {
  data: DashboardAnalytics;
  groupBy: DashboardGroupBy;
  onGroupByChange: (groupBy: DashboardGroupBy) => void;
}) {
  return (
    <div className="space-y-6">
      <WidgetShell
        icon={Gauge}
        isEmpty={!data.pipeline.length}
        subtitle="Discovery through publishing, with bottlenecks highlighted."
        title="Production Pipeline"
      >
        <ProductionPipeline stages={data.pipeline} />
      </WidgetShell>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <WidgetShell
          actions={<TrendViewSelector groupBy={groupBy} onChange={onGroupByChange} />}
          icon={TrendingUp}
          isEmpty={false}
          subtitle="New series created across the selected day, week, or month view."
          title="Series Growth"
        >
          <SeriesVelocityChart points={data.series_velocity} />
        </WidgetShell>
        <WidgetShell
          icon={BarChart3}
          isEmpty={false}
          subtitle="A compact read on production momentum and publishing volume."
          title="Growth Pulse"
        >
          <GrowthPulse
            confidence={data.research_overview.avg_confidence}
            episodes={data.episode_velocity}
            publishing={data.publishing_velocity}
            series={data.series_velocity}
          />
        </WidgetShell>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <WidgetShell
          actions={<TrendViewSelector groupBy={groupBy} onChange={onGroupByChange} />}
          icon={Layers3}
          isEmpty={false}
          subtitle="Episodes planned or created over the selected dashboard period."
          title="Episode Trend Graph"
        >
          <EpisodeVelocityTrend points={data.episode_velocity} />
        </WidgetShell>
        <WidgetShell
          actions={<TrendViewSelector groupBy={groupBy} onChange={onGroupByChange} />}
          icon={Radio}
          isEmpty={false}
          subtitle="Buffer queue scheduled posts compared with published output."
          title="Publishing Cadence"
        >
          <PublishingVelocityTrend points={data.publishing_velocity} />
        </WidgetShell>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <WidgetShell
          icon={Activity}
          isEmpty={!data.research_confidence.length}
          subtitle="Average evidence confidence over the selected range."
          title="Research Confidence Trend"
        >
          <ResearchConfidenceTrend points={data.research_confidence} />
        </WidgetShell>
        <WidgetShell
          icon={Gauge}
          isEmpty={false}
          subtitle="Research health without diagnostics noise."
          title="Research Overview"
        >
          <ResearchOverview overview={data.research_overview} />
        </WidgetShell>
      </div>
    </div>
  );
}

function DateFilter({
  endDate,
  onChange,
  range,
  startDate
}: {
  endDate: string;
  onChange: (next: {
    endDate?: string;
    groupBy?: DashboardGroupBy;
    range?: DashboardRange;
    startDate?: string;
  }) => void;
  range: DashboardRange;
  startDate: string;
}) {
  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap justify-end gap-2 rounded-streamly-pill bg-streamly-wash p-1 shadow-[inset_0_0_0_1px_rgba(217,200,255,0.72)]">
        {RANGE_OPTIONS.map((option) => (
          <button
            key={option.value}
            aria-pressed={range === option.value}
            className={[
              "rounded-streamly-pill px-3 py-2 text-xs font-extrabold transition",
              range === option.value
                ? "bg-white text-streamly-violet shadow-streamly-card"
                : "text-streamly-purpleBlue hover:bg-white/70"
            ].join(" ")}
            onClick={() => onChange({ range: option.value })}
            type="button"
          >
            {option.label}
          </button>
        ))}
      </div>
      {range === "custom" ? (
        <div className="flex flex-wrap justify-end gap-2">
          <DateInput
            label="Start"
            max={endDate}
            onChange={(value) => onChange({ startDate: value })}
            value={startDate}
          />
          <DateInput
            label="End"
            min={startDate}
            onChange={(value) => onChange({ endDate: value })}
            value={endDate}
          />
        </div>
      ) : null}
    </div>
  );
}

function DateInput({
  label,
  max,
  min,
  onChange,
  value
}: {
  label: string;
  max?: string;
  min?: string;
  onChange: (value: string) => void;
  value: string;
}) {
  return (
    <label className="flex items-center gap-2 rounded-streamly-pill border border-streamly-lavenderStrong bg-white px-3 py-2 text-xs font-extrabold text-streamly-purpleBlue shadow-streamly-card">
      <CalendarDays aria-hidden className="h-4 w-4 text-streamly-electric" />
      <span>{label}</span>
      <input
        className="bg-transparent text-streamly-coal outline-none"
        max={max}
        min={min}
        onChange={(event) => onChange(event.target.value)}
        type="date"
        value={value}
      />
    </label>
  );
}

function TrendViewSelector({
  groupBy,
  onChange
}: {
  groupBy: DashboardGroupBy;
  onChange: (groupBy: DashboardGroupBy) => void;
}) {
  return (
    <div className="flex rounded-streamly-pill bg-streamly-wash p-1">
      {TREND_VIEW_OPTIONS.map((option) => (
        <button
          key={option.value}
          aria-pressed={groupBy === option.value}
          className={[
            "rounded-streamly-pill px-3 py-1.5 text-xs font-extrabold transition",
            groupBy === option.value
              ? "bg-white text-streamly-violet shadow-streamly-card"
              : "text-streamly-purpleBlue hover:bg-white/70"
          ].join(" ")}
          onClick={() => onChange(option.value)}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function WidgetShell({
  actions,
  children,
  icon: Icon,
  isEmpty,
  subtitle,
  title
}: {
  actions?: ReactNode;
  children: ReactNode;
  icon: LucideIcon;
  isEmpty: boolean;
  subtitle: string;
  title: string;
}) {
  return (
    <section className="streamly-premium-card p-5">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric">
            <Icon aria-hidden className="h-4 w-4" />
          </span>
          <div>
            <h2 className="font-streamly-platform text-lg font-extrabold text-streamly-coal">
              {title}
            </h2>
            <p className="mt-1 text-sm font-semibold leading-6 text-streamly-purpleBlue">
              {subtitle}
            </p>
          </div>
        </div>
        {actions}
      </div>
      {isEmpty ? (
        <EmptyState
          description="Nothing needs attention in this area right now."
          title="All clear"
        />
      ) : (
        children
      )}
    </section>
  );
}

function ProductionPipeline({ stages }: { stages: PipelineStage[] }) {
  const [activeTooltip, setActiveTooltip] = useState<string | null>(null);
  const total = Math.max(stages.reduce((sum, stage) => sum + stage.count, 0), 1);
  const maxStageCount = Math.max(...stages.map((stage) => stage.count), 0);
  const bottleneckStages = stages
    .filter((stage) => stage.is_bottleneck)
    .map((stage) => stage.stage);
  return (
    <div className="grid gap-3 md:grid-cols-3 2xl:grid-cols-6">
      {stages.map((stage) => {
        const width = `${Math.max((stage.count / total) * 100, stage.count ? 12 : 4)}%`;
        const trendLabel = stage.delta > 0 ? `+${stage.delta}` : String(stage.delta);
        const tooltip = pipelineStageTooltip(stage, maxStageCount, bottleneckStages);
        return (
          <div
            key={stage.stage}
            className={[
              "rounded-streamly-xl border bg-streamly-wash/80 p-4",
              stage.is_bottleneck
                ? "border-amber-200 shadow-[0_18px_44px_rgba(245,158,11,0.12)]"
                : "border-streamly-lavenderStrong"
            ].join(" ")}
          >
            <div className="flex items-center justify-between gap-3">
              <p className="font-streamly-platform text-base font-extrabold text-streamly-coal">
                {stage.stage}
              </p>
              <span className="font-streamly-platform text-2xl font-extrabold text-streamly-violet">
                {stage.count}
              </span>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-streamly-pill bg-white">
              <div className="h-full rounded-streamly-pill bg-streamly-electric" style={{ width }} />
            </div>
            <div className="mt-3 flex items-center justify-between gap-2 text-xs font-extrabold">
              <span
                className={[
                  "relative inline-flex items-center gap-1.5",
                  stage.is_bottleneck ? "text-amber-800" : "text-streamly-purpleBlue"
                ].join(" ")}
              >
                <span>{stage.is_bottleneck ? "Bottleneck" : "Flowing"}</span>
                <button
                  aria-label={tooltip}
                  className="dashboard-stage-tooltip-trigger grid h-5 w-5 place-items-center rounded-streamly-pill bg-white/85 text-current outline-none ring-1 ring-current/15 transition hover:bg-white focus-visible:ring-2 focus-visible:ring-streamly-electric"
                  onBlur={() => setActiveTooltip(null)}
                  onClick={() =>
                    setActiveTooltip((current) => (current === stage.stage ? null : stage.stage))
                  }
                  onFocus={() => setActiveTooltip(stage.stage)}
                  onMouseEnter={() => setActiveTooltip(stage.stage)}
                  onMouseLeave={() => setActiveTooltip(null)}
                  title={tooltip}
                  type="button"
                >
                  <Info aria-hidden className="h-3.5 w-3.5" />
                  <span
                    aria-hidden="true"
                    className={[
                      "dashboard-stage-tooltip pointer-events-none absolute bottom-7 left-0 z-20 w-56 rounded-streamly-md bg-streamly-coal px-3 py-2 text-left text-[11px] font-bold leading-5 text-white shadow-[0_18px_36px_rgba(38,28,65,0.22)] transition",
                      activeTooltip === stage.stage ? "opacity-100" : "opacity-0"
                    ].join(" ")}
                  >
                    {tooltip}
                  </span>
                </button>
              </span>
              <span className="text-streamly-purpleBlue">Trend {trendLabel}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function pipelineStageTooltip(
  stage: PipelineStage,
  maxStageCount: number,
  bottleneckStages: string[]
) {
  const queueLabel = "active series";
  const bottleneckStageList = formatStageList(bottleneckStages);
  if (stage.is_bottleneck) {
    if (bottleneckStages.length === 1) {
      return `${stage.stage} is the bottleneck because it has ${stage.count} ${queueLabel}, the highest queue in the production pipeline.`;
    }
    return `${stage.stage} is tied as a bottleneck with ${stage.count} ${queueLabel}. Bottleneck stages: ${bottleneckStageList}.`;
  }
  if (bottleneckStages.length === 0) {
    return `${stage.stage} has ${stage.count} ${queueLabel}. No bottleneck is active because the pipeline queue is empty.`;
  }
  if (bottleneckStages.length === 1) {
    return `${stage.stage} has ${stage.count} ${queueLabel}. The current bottleneck is ${bottleneckStageList} (${maxStageCount} ${queueLabel}).`;
  }
  return `${stage.stage} has ${stage.count} ${queueLabel}. Current bottleneck stages are ${bottleneckStageList} (${maxStageCount} ${queueLabel} each).`;
}

function formatStageList(stages: string[]) {
  if (stages.length <= 1) {
    return stages[0] ?? "None";
  }
  if (stages.length === 2) {
    return stages.join(" and ");
  }
  return `${stages.slice(0, -1).join(", ")}, and ${stages[stages.length - 1]}`;
}

function SeriesVelocityChart({ points }: { points: SeriesVelocityPoint[] }) {
  const total = points.reduce((sum, point) => sum + point.series, 0);
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_12rem]">
      <div className="h-64">
        <ResponsiveContainer height="100%" width="100%">
          <AreaChart data={points} margin={{ bottom: 0, left: 0, right: 12, top: 10 }}>
            <defs>
              <linearGradient id="seriesGrowthFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#8646ee" stopOpacity={0.38} />
                <stop offset="100%" stopColor="#8646ee" stopOpacity={0.04} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#efe7ff" vertical={false} />
            <XAxis dataKey="label" tick={{ fill: "#5a4a91", fontSize: 11 }} tickLine={false} />
            <YAxis allowDecimals={false} tick={{ fill: "#5a4a91", fontSize: 11 }} tickLine={false} width={32} />
            <Tooltip content={<ChartTooltip />} />
            <Area
              dataKey="series"
              fill="url(#seriesGrowthFill)"
              name="Series"
              stroke="#8646ee"
              strokeWidth={3}
              type="monotone"
            />
            <Line
              dataKey="previous_series"
              dot={false}
              name="Previous"
              stroke="#b9a5e8"
              strokeDasharray="5 5"
              strokeWidth={2}
              type="monotone"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-streamly-xl bg-gradient-to-br from-streamly-lavender to-white p-4 shadow-streamly-card">
        <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
          Series created
        </p>
        <p className="mt-2 font-streamly-platform text-4xl font-extrabold text-streamly-coal">
          {total}
        </p>
        <p className="mt-3 text-sm font-bold leading-6 text-streamly-purpleBlue">
          Creation momentum across the selected dashboard window.
        </p>
      </div>
    </div>
  );
}

function GrowthPulse({
  confidence,
  episodes,
  publishing,
  series
}: {
  confidence: number;
  episodes: EpisodeVelocityPoint[];
  publishing: PublishingVelocityPoint[];
  series: SeriesVelocityPoint[];
}) {
  const seriesTotal = series.reduce((sum, point) => sum + point.series, 0);
  const episodeTotal = episodes.reduce((sum, point) => sum + point.episodes, 0);
  const publishingTotal = publishing.reduce(
    (sum, point) => sum + point.scheduled + point.published + point.failed,
    0
  );
  const pulses = [
    {
      label: "Series momentum",
      value: seriesTotal,
      tone: "from-[#8b46f6] to-[#c7a8ff]"
    },
    {
      label: "Episode movement",
      value: episodeTotal,
      tone: "from-[#2fbf9b] to-[#9be7d3]"
    },
    {
      label: "Publishing volume",
      value: publishingTotal,
      tone: "from-[#4f46e5] to-[#9ea7ff]"
    },
    {
      label: "Research confidence",
      value: `${confidence}%`,
      tone: "from-[#f59e0b] to-[#f7d37b]"
    }
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {pulses.map((pulse) => (
        <div
          className="overflow-hidden rounded-streamly-xl border border-streamly-lavenderStrong bg-white shadow-streamly-card"
          key={pulse.label}
        >
          <div className={`h-2 bg-gradient-to-r ${pulse.tone}`} />
          <div className="p-4">
            <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
              {pulse.label}
            </p>
            <p className="mt-2 font-streamly-platform text-3xl font-extrabold text-streamly-coal">
              {pulse.value}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

function EpisodeVelocityTrend({ points }: { points: EpisodeVelocityPoint[] }) {
  const latest = [...points].reverse().find((point) => point.episodes > 0)?.episodes ?? 0;

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_10rem]">
      <div className="h-64">
        <ResponsiveContainer height="100%" width="100%">
          <ComposedChart data={points} margin={{ bottom: 0, left: 0, right: 10, top: 10 }}>
            <CartesianGrid stroke="#efe7ff" vertical={false} />
            <XAxis dataKey="label" tick={{ fill: "#5a4a91", fontSize: 11 }} tickLine={false} />
            <YAxis allowDecimals={false} tick={{ fill: "#5a4a91", fontSize: 11 }} tickLine={false} width={32} />
            <Tooltip content={<ChartTooltip />} />
            <Bar dataKey="episodes" fill="#8646ee" name="Episodes" radius={[8, 8, 0, 0]} />
            <Line
              dataKey="previous_episodes"
              dot={false}
              name="Previous"
              stroke="#2fbf9b"
              strokeWidth={3}
              type="monotone"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-streamly-xl bg-streamly-wash/80 p-4">
        <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
          Latest bucket
        </p>
        <p className="mt-2 font-streamly-platform text-3xl font-extrabold text-streamly-coal">
          {latest}
        </p>
        <p className="mt-3 text-sm font-bold leading-6 text-streamly-purpleBlue">
          Episode trend by selected view.
        </p>
      </div>
    </div>
  );
}

function PublishingVelocityTrend({ points }: { points: PublishingVelocityPoint[] }) {
  const totalScheduled = points.reduce((sum, point) => sum + point.scheduled, 0);
  const totalPublished = points.reduce((sum, point) => sum + point.published, 0);

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_10rem]">
      <div className="h-64">
        <ResponsiveContainer height="100%" width="100%">
          <BarChart data={points} margin={{ bottom: 0, left: 0, right: 10, top: 10 }}>
            <CartesianGrid stroke="#efe7ff" vertical={false} />
            <XAxis dataKey="label" tick={{ fill: "#5a4a91", fontSize: 11 }} tickLine={false} />
            <YAxis allowDecimals={false} tick={{ fill: "#5a4a91", fontSize: 11 }} tickLine={false} width={32} />
            <Tooltip content={<ChartTooltip />} />
            <Bar dataKey="scheduled" fill={PUBLISHING_COLORS.scheduled} name="Buffer queue" radius={[8, 8, 0, 0]} stackId="publishing" />
            <Bar dataKey="published" fill={PUBLISHING_COLORS.published} name="Published" radius={[8, 8, 0, 0]} stackId="publishing" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="space-y-3 rounded-streamly-xl bg-streamly-wash/80 p-4">
        <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
          Buffer queue
        </p>
        <ChartLegendDot color={PUBLISHING_COLORS.scheduled} label="Scheduled" value={totalScheduled} />
        <ChartLegendDot color={PUBLISHING_COLORS.published} label="Published" value={totalPublished} />
      </div>
    </div>
  );
}

function ResearchOverview({ overview }: { overview: ResearchOverviewData }) {
  return (
    <div className="grid gap-3">
      <OverviewMetric label="Sources analyzed" value={String(overview.sources_analyzed)} />
      <OverviewMetric label="Signals extracted" value={String(overview.signals_extracted)} />
      <OverviewMetric label="Avg confidence" value={`${overview.avg_confidence}%`} />
      <div className="rounded-streamly-xl bg-streamly-lavender/55 p-4">
        <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">Top trend</p>
        <p className="mt-2 font-streamly-platform text-lg font-extrabold text-streamly-coal">
          {overview.top_trend}
        </p>
      </div>
    </div>
  );
}

function ResearchConfidenceTrend({ points }: { points: ConfidencePoint[] }) {
  const current = latestConfidence(points);
  const previous = latestPreviousConfidence(points);
  const trendDirection = current > previous ? "Rising" : current < previous ? "Falling" : "Stable";

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_11rem]">
      <div className="h-56">
        <ResponsiveContainer height="100%" width="100%">
          <LineChart data={points} margin={{ bottom: 0, left: 0, right: 8, top: 8 }}>
            <CartesianGrid stroke="#efe7ff" vertical={false} />
            <XAxis dataKey="label" tick={{ fill: "#5a4a91", fontSize: 11 }} tickLine={false} />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: "#5a4a91", fontSize: 11 }}
              tickLine={false}
              width={34}
            />
            <Tooltip content={<ChartTooltip />} />
            <Line
              dataKey="average_confidence"
              dot={false}
              name="Avg confidence"
              stroke="#8646ee"
              strokeWidth={3}
              type="monotone"
            />
            <Line
              dataKey="previous_confidence"
              dot={false}
              name="Previous"
              stroke="#b9a5e8"
              strokeDasharray="5 5"
              strokeWidth={2}
              type="monotone"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-streamly-xl bg-streamly-wash/80 p-4">
        <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
          Average confidence
        </p>
        <p className="mt-2 font-streamly-platform text-3xl font-extrabold text-streamly-coal">
          {current}%
        </p>
        <p className="mt-3 text-sm font-bold text-streamly-purpleBlue">{trendDirection}</p>
      </div>
    </div>
  );
}

function OverviewMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-streamly-xl bg-streamly-wash/80 px-4 py-3">
      <p className="text-sm font-bold text-streamly-purpleBlue">{label}</p>
      <p className="font-streamly-platform text-xl font-extrabold text-streamly-coal">{value}</p>
    </div>
  );
}

function ChartLegendDot({
  color,
  label,
  value
}: {
  color: string;
  label: string;
  value: number;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="flex items-center gap-2 text-xs font-extrabold text-streamly-purpleBlue">
        <span className="h-2.5 w-2.5 rounded-streamly-pill" style={{ background: color }} />
        {label}
      </span>
      <span className="font-streamly-platform text-lg font-extrabold text-streamly-coal">
        {value}
      </span>
    </div>
  );
}

function ChartTooltip({
  active,
  payload
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number | string }>;
}) {
  if (!active || !payload?.length) {
    return null;
  }
  return (
    <div className="rounded-streamly-lg border border-streamly-lavenderStrong bg-white px-3 py-2 shadow-streamly-card">
      {payload.map((item) => (
        <p key={`${item.name}-${item.value}`} className="text-xs font-bold text-streamly-coal">
          {item.name}: {item.value}
        </p>
      ))}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        {Array.from({ length: 6 }, (_, index) => (
          <div key={index} className="h-28 animate-pulse rounded-streamly-xl bg-streamly-lavender/50" />
        ))}
      </div>
      <LoadingState label="Loading dashboard" />
    </div>
  );
}

function useDashboardRange(rawRange: string | null): DashboardRange {
  return useMemo(() => {
    const stored = window.localStorage.getItem(RANGE_STORAGE_KEY);
    const candidate = rawRange ?? stored ?? "30d";
    return isDashboardRange(candidate) ? candidate : "30d";
  }, [rawRange]);
}

function useTrendGroupBy(rawGroupBy: string | null, range: DashboardRange): DashboardGroupBy {
  return useMemo(() => {
    const stored = window.localStorage.getItem(GROUP_STORAGE_KEY);
    const candidate = rawGroupBy ?? stored ?? (range === "90d" ? "week" : "day");
    return isTrendGroupBy(candidate) ? candidate : range === "90d" ? "week" : "day";
  }, [range, rawGroupBy]);
}

function useDashboardDate(rawDate: string | null, storageKey: string, fallback: string) {
  return useMemo(() => {
    const stored = window.localStorage.getItem(storageKey);
    const candidate = rawDate ?? stored ?? fallback;
    return isDateInputValue(candidate) ? candidate : fallback;
  }, [fallback, rawDate, storageKey]);
}

function dashboardSearchParams(
  range: DashboardRange,
  groupBy: DashboardGroupBy,
  startDate: string,
  endDate: string
) {
  const params = new URLSearchParams();
  params.set("range", range);
  params.set("group_by", groupBy);
  if (range === "custom") {
    params.set("start_date", startDate);
    params.set("end_date", endDate);
  }
  return params;
}

function isDashboardRange(value: string): value is DashboardRange {
  return RANGE_OPTIONS.some((option) => option.value === value);
}

function isTrendGroupBy(value: string): value is DashboardGroupBy {
  return TREND_VIEW_OPTIONS.some((option) => option.value === value);
}

function isDateInputValue(value: string) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value);
}

function todayDate() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgo(days: number) {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().slice(0, 10);
}

function latestConfidence(points: ConfidencePoint[]) {
  const point = [...points].reverse().find((item) => item.average_confidence > 0);
  return point ? point.average_confidence : 0;
}

function latestPreviousConfidence(points: ConfidencePoint[]) {
  const point = [...points].reverse().find((item) => item.previous_confidence > 0);
  return point ? point.previous_confidence : 0;
}
