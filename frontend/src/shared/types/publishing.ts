import type {
  BufferAccount,
  BufferChannel,
  BufferPostStatus,
  BufferWebhook,
  CaptionPlatform,
  CaptionVideoKind,
  PublishingAuditLog,
  ScheduleStatus
} from "@/shared/types/series";
import type {
  CursorPaginatedResponse,
  PaginatedResponse
} from "@/shared/types/pagination";

export type PublishingAnalytics = {
  scheduled_count: number;
  published_count: number;
  failed_count: number;
  cancelled_count: number;
  retryable_count: number;
  active_channel_count: number;
  unhealthy_channel_count: number;
  audit_event_count: number;
  webhook_event_count: number;
  buffer_account_status: BufferAccount["status"] | null;
  warnings: string[];
};

export type PublishingQueueItem = {
  id: string;
  series_id: string;
  series_name: string;
  episode_id: string;
  episode_number: number;
  episode_title: string;
  caption_id: string;
  video_kind: CaptionVideoKind;
  video_key: string;
  platform: CaptionPlatform;
  status: ScheduleStatus;
  buffer_status: BufferPostStatus;
  buffer_post_id: string | null;
  scheduled_for: string;
  scheduled_caption_text: string;
  failure_reason: string | null;
  live_url: string | null;
  retry_count: number;
  next_retry_at: string | null;
  last_synced_at: string | null;
  rate_limit_reset_at: string | null;
  channel: BufferChannel | null;
  latest_audit: PublishingAuditLog | null;
  created_at: string;
  updated_at: string;
};

export type PublishingQueue = PaginatedResponse<PublishingQueueItem> & {
  total_count: number;
  filters: Record<string, unknown>;
};

export type ChannelHealthCard = {
  channel: BufferChannel;
  mapped_platforms: CaptionPlatform[];
  scheduled_count: number;
  published_count: number;
  failed_count: number;
  health_status: "healthy" | "degraded" | "broken";
  warnings: string[];
};

export type PublishingTimelineEvent = {
  id: string;
  event_type: string;
  title: string;
  status: string;
  description: string;
  occurred_at: string;
  schedule_id: string | null;
  series_id: string | null;
  platform: CaptionPlatform | null;
};

export type PublishingActivityFeedItem = PublishingTimelineEvent & {
  source: "audit" | "webhook";
};

export type PublishingTimelineResponse = CursorPaginatedResponse<PublishingTimelineEvent>;

export type PublishingAuditLogResponse = CursorPaginatedResponse<PublishingAuditLog>;

export type PublishingOperationsWorkspace = {
  analytics: PublishingAnalytics;
  queue: PublishingQueue;
  failed: PublishingQueue;
  retry_center: PublishingQueue;
  channel_health: ChannelHealthCard[];
  timeline: PublishingTimelineEvent[];
  activity_feed: PublishingActivityFeedItem[];
  audit_logs: PublishingAuditLog[];
  webhooks: BufferWebhook[];
  buffer_account: BufferAccount | null;
};

export type PublishingQueueFilters = {
  statuses?: ScheduleStatus[];
  platforms?: CaptionPlatform[];
  query?: string;
  limit?: number;
  page?: number;
  pageSize?: number;
};

export type PublishingBulkActionPayload = {
  schedule_ids: string[];
};

export type PublishingBulkActionItemResult = {
  schedule_id: string;
  success: boolean;
  message: string;
  status: ScheduleStatus | null;
};

export type PublishingBulkActionResponse = {
  action: "retry" | "sync" | "stop";
  requested_count: number;
  succeeded_count: number;
  failed_count: number;
  results: PublishingBulkActionItemResult[];
  workspace: PublishingOperationsWorkspace;
};
