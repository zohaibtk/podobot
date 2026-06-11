import type {
  ResearchSourceStatus as ResearchRegistrySourceStatus
} from "@/shared/types/researchSources";
import type {
  ResearchRunStatus,
  ResearchSourceUsageStatus
} from "@/shared/types/research";
import type {
  MCPServerStatus,
  MCPToolRunStatus,
  MCPToolStatus
} from "@/shared/types/mcp";
import type {
  AgentRunStatus,
  AgentOutputValidationStatus,
  PromptVersionStatus
} from "@/shared/types/agents";
import type {
  UserInvitationStatus,
  WorkspaceUserStatus
} from "@/shared/types/settings";
import type {
  BufferPostStatus,
  BriefStatus,
  CaptionStatus,
  ClipSuggestionStatus,
  DiscoveryStatus,
  EpisodeOutlineStatus,
  EpisodeStatus,
  ScheduleStatus,
  MediaAssetStatus,
  MediaProcessingJobStatus,
  SeriesStatus,
  ThumbnailStatus,
  TranscriptStatus,
  VideoStatus
} from "@/shared/types/series";
import type { StrategyIdeaStatus } from "@/shared/types/strategy";

type StatusBadgeProps = {
  label: string;
  tone?:
    | SeriesStatus
    | DiscoveryStatus
    | EpisodeStatus
    | EpisodeOutlineStatus
    | BriefStatus
    | CaptionStatus
    | VideoStatus
    | TranscriptStatus
    | ThumbnailStatus
    | ClipSuggestionStatus
    | ScheduleStatus
    | MediaAssetStatus
    | MediaProcessingJobStatus
    | BufferPostStatus
    | StrategyIdeaStatus
    | AgentRunStatus
    | AgentOutputValidationStatus
    | PromptVersionStatus
    | ResearchRegistrySourceStatus
    | ResearchRunStatus
    | ResearchSourceUsageStatus
    | MCPServerStatus
    | MCPToolStatus
    | MCPToolRunStatus
    | WorkspaceUserStatus
    | UserInvitationStatus
    | "neutral";
};

const toneClass: Record<string, string> = {
  researching: "bg-streamly-lavender text-streamly-violet",
  running: "bg-streamly-lavender text-streamly-violet",
  pending: "bg-streamly-wash text-streamly-purpleBlue",
  planning: "bg-streamly-wash text-streamly-purpleBlue",
  in_production: "bg-white text-streamly-purpleBlue",
  partially_published: "bg-streamly-lavender text-streamly-violet",
  complete: "bg-emerald-50 text-emerald-700",
  planned: "bg-streamly-wash text-streamly-purpleBlue",
  outlined: "bg-emerald-50 text-emerald-700",
  profiles_set: "bg-streamly-lavender text-streamly-violet",
  brief_ready: "bg-emerald-50 text-emerald-700",
  approved: "bg-emerald-50 text-emerald-700",
  recorded: "bg-white text-streamly-purpleBlue",
  captioning: "bg-streamly-lavender text-streamly-violet",
  scheduled: "bg-emerald-50 text-emerald-700",
  published: "bg-emerald-50 text-emerald-700",
  placeholder: "bg-streamly-wash text-streamly-purpleBlue",
  generated: "bg-emerald-50 text-emerald-700",
  draft: "bg-amber-50 text-amber-800",
  uploaded: "bg-streamly-lavender text-streamly-violet",
  locked: "bg-emerald-50 text-emerald-700",
  missing: "bg-amber-50 text-amber-800",
  processed: "bg-emerald-50 text-emerald-700",
  selected: "bg-emerald-50 text-emerald-700",
  suggested: "bg-streamly-lavender text-streamly-violet",
  not_started: "bg-streamly-wash text-streamly-purpleBlue",
  ready: "bg-emerald-50 text-emerald-700",
  queued: "bg-streamly-lavender text-streamly-violet",
  succeeded: "bg-emerald-50 text-emerald-700",
  requires_human: "bg-amber-50 text-amber-800",
  completed: "bg-emerald-50 text-emerald-700",
  partial_success: "bg-amber-50 text-amber-800",
  needs_review: "bg-amber-50 text-amber-800",
  cancelled: "bg-zinc-100 text-zinc-600",
  passed: "bg-emerald-50 text-emerald-700",
  warning: "bg-amber-50 text-amber-800",
  regression: "bg-red-50 text-red-700",
  reviewed: "bg-emerald-50 text-emerald-700",
  not_required: "bg-streamly-wash text-streamly-purpleBlue",
  proposed: "bg-streamly-wash text-streamly-purpleBlue",
  in_review: "bg-streamly-lavender text-streamly-violet",
  dismissed: "bg-zinc-100 text-zinc-600",
  converted: "bg-emerald-50 text-emerald-700",
  healthy: "bg-emerald-50 text-emerald-700",
  degraded: "bg-amber-50 text-amber-800",
  broken: "bg-red-50 text-red-700",
  not_configured: "bg-streamly-wash text-streamly-purpleBlue",
  disabled: "bg-zinc-100 text-zinc-600",
  unknown: "bg-streamly-wash text-streamly-purpleBlue",
  enabled: "bg-emerald-50 text-emerald-700",
  deprecated: "bg-amber-50 text-amber-800",
  active: "bg-emerald-50 text-emerald-700",
  invited: "bg-streamly-lavender text-streamly-violet",
  suspended: "bg-zinc-100 text-zinc-600",
  accepted: "bg-emerald-50 text-emerald-700",
  revoked: "bg-zinc-100 text-zinc-600",
  expired: "bg-amber-50 text-amber-800",
  rejected: "bg-red-50 text-red-700",
  archived: "bg-zinc-100 text-zinc-600",
  failed: "bg-red-50 text-red-700",
  used: "bg-emerald-50 text-emerald-700",
  skipped_disabled: "bg-zinc-100 text-zinc-600",
  no_results: "bg-streamly-wash text-streamly-purpleBlue",
  neutral: "bg-white text-streamly-purpleBlue"
};

export function StatusBadge({ label, tone = "neutral" }: StatusBadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 rounded-streamly-pill px-3 py-1.5 text-xs font-extrabold capitalize shadow-[inset_0_0_0_1px_rgba(255,255,255,0.5)]",
        toneClass[tone] ?? toneClass.neutral
      ].join(" ")}
    >
      <span className="h-1.5 w-1.5 rounded-streamly-pill bg-current opacity-70" />
      {label.replaceAll("_", " ")}
    </span>
  );
}
