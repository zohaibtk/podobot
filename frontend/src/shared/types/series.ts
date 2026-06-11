import type { SeriesStageId } from "@/routes/routeRegistry";
import type { PaginatedResponse } from "@/shared/types/pagination";
import type {
  ResearchConfidenceLevel,
  ResearchRun,
  ResearchSourceUsageStatus,
  ScoreExplanation
} from "@/shared/types/research";

export type SeriesStatus =
  | "researching"
  | "planning"
  | "in_production"
  | "partially_published"
  | "complete"
  | "archived";

export type DiscoveryStatus = "pending" | "running" | "complete" | "failed";
export type ResearchSourceStatus = "pending" | "running" | "complete" | "failed";
export type NarrativeStatus = "candidate" | "selected" | "retired";
export type ProfileKind = "host" | "guest";
export type EpisodeStatus =
  | "planned"
  | "outlined"
  | "profiles_set"
  | "brief_ready"
  | "approved"
  | "recorded"
  | "captioning"
  | "scheduled"
  | "partially_published"
  | "published";
export type EpisodeOutlineStatus = "placeholder" | "generated" | "draft" | "approved";
export type OutlineVersionSource = "lock_generated" | "manual_edit" | "regeneration";
export type BriefKind = "host" | "guest";
export type BriefStatus = "generated" | "draft" | "approved";
export type BriefVersionSource = "generation" | "manual_edit" | "regeneration";
export type VideoStatus = "missing" | "uploaded" | "complete" | "locked" | "failed";
export type TranscriptStatus = "uploaded" | "processed" | "failed";
export type ThumbnailStatus = "uploaded" | "selected";
export type ClipSuggestionStatus = "suggested" | "approved" | "rejected";
export type MediaAssetKind = "video" | "transcript" | "thumbnail";
export type MediaAssetStatus =
  | "uploaded"
  | "processing"
  | "ready"
  | "failed"
  | "archived"
  | "deleted";
export type MediaProcessingJobStatus = "queued" | "running" | "succeeded" | "failed";
export type MediaProcessingJobType =
  | "metadata_extraction"
  | "transcript_parsing"
  | "thumbnail_generation";
export type CaptionStatus = "not_started" | "ready" | "failed";
export type CaptionVideoKind = "full_episode" | "short_clip";
export type CaptionPlatform =
  | "linkedin"
  | "facebook"
  | "youtube"
  | "instagram"
  | "tiktok"
  | "x";
export type ScheduleStatus = "scheduled" | "published" | "failed" | "cancelled";
export type BufferPostStatus = "queued" | "published" | "failed" | "cancelled";
export type BufferAccountStatus =
  | "disconnected"
  | "oauth_pending"
  | "connected"
  | "expired"
  | "revoked";
export type BufferWebhookStatus = "received" | "processed" | "ignored" | "failed";
export type PublishingAuditStatus =
  | "succeeded"
  | "failed"
  | "rate_limited"
  | "retry_scheduled";

export type Series = {
  id: string;
  name: string;
  audience: string;
  description: string;
  guest_name: string | null;
  status: SeriesStatus;
  discovery_status: DiscoveryStatus;
  current_stage: SeriesStageId;
  episode_plan_generated_at: string | null;
  plan_locked_at: string | null;
  briefs_approved_at: string | null;
  captions_unlocked_at: string | null;
  scheduling_unlocked_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SeriesListResponse = PaginatedResponse<Series>;

export type CreateSeriesPayload = {
  name: string;
  audience: string;
  description: string;
  guest_name?: string | null;
};

export type DiscoveryLedgerEntry = {
  id: string;
  series_id: string;
  source_name: string;
  source_type: string;
  source_url: string;
  status: ResearchSourceStatus;
  signal_title: string;
  signal_summary: string;
  confidence_score: number;
  tier?: string | null;
  tier_score?: number | null;
  engagement_score?: number | null;
  freshness_score?: number | null;
  author_score?: number | null;
  composite_score?: number | null;
  confidence_level?: ResearchConfidenceLevel | null;
  trend_score?: number | null;
  trend_available?: boolean | null;
  score_explanation_json?: ScoreExplanation | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type SupportingSignal = {
  source_name: string;
  signal_title: string;
  confidence_score: number;
};

export type Narrative = {
  id: string;
  series_id: string;
  title: string;
  thesis: string;
  summary: string;
  confidence_score: number;
  supporting_signals: SupportingSignal[];
  generation: number;
  status: NarrativeStatus;
  is_selected: boolean;
  selected_at: string | null;
  created_at: string;
  updated_at: string;
};

export type DiscoveryWorkspace = {
  series: Series;
  progress_percent: number;
  ledger: DiscoveryLedgerEntry[];
  narratives: Narrative[];
  selected_narrative_id: string | null;
  research_activity: {
    run_count: number;
    latest_run: ResearchRun | null;
    sources_queried: number;
    sources_failed: number;
    sources_skipped: number;
    documents_found: number;
    documents_used: number;
    latest_run_status?: ResearchRun["status"] | null;
    source_activity?: DiscoverySourceActivity[];
  };
};

export type DiscoverySourceActivity = {
  id: string;
  research_run_id: string;
  source_id: string;
  source_key: string;
  source_name: string;
  provider_type: string;
  status: ResearchSourceUsageStatus;
  query_text: string;
  documents_found: number;
  documents_used: number;
  latency_ms: number | null;
  failure_reason: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
};

export type Profile = {
  id: string;
  name: string;
  role_title: string;
  kind: ProfileKind;
  archetype: string;
  bio: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ProfileListResponse = PaginatedResponse<Profile>;

export type ProfileDraftPayload = {
  name: string;
  role_title: string;
  kind: ProfileKind;
  archetype: string;
  bio?: string | null;
};

export type ProfileFilters = {
  search?: string;
  kind?: ProfileKind;
  archetype?: string;
  includeInactive?: boolean;
  page?: number;
  pageSize?: number;
  sort?: string;
};

export type ProfileRecommendation = {
  profile: Profile;
  reason: string;
  confidence_score: number;
};

export type ProfileRecommendationsResponse = {
  items: ProfileRecommendation[];
};

export type Episode = {
  id: string;
  series_id: string;
  episode_number: number;
  title: string;
  premise: string;
  status: EpisodeStatus;
  host_profile_id: string | null;
  guest_profile_id: string | null;
  guest_name_override: string | null;
  host_profile_name: string | null;
  guest_profile_name: string | null;
  effective_host_name: string | null;
  effective_guest_name: string | null;
  can_edit: boolean;
  missing_assignments: string[];
  created_at: string;
  updated_at: string;
};

export type EpisodeOutlineSummary = {
  id: string;
  series_id: string;
  episode_id: string;
  title: string;
  outline_markdown: string;
  status: EpisodeOutlineStatus;
  current_version_id: string | null;
  approved_version_id: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
};

export type OutlineVersion = {
  id: string;
  outline_id: string;
  series_id: string;
  episode_id: string;
  version_number: number;
  title: string;
  outline_markdown: string;
  source: OutlineVersionSource;
  created_at: string;
};

export type OutlineVersionListResponse = PaginatedResponse<OutlineVersion>;

export type EpisodeOutline = EpisodeOutlineSummary & {
  episode_number: number;
  episode_title: string;
  episode_premise: string;
  version_count: number;
  latest_version_number: number | null;
  can_edit: boolean;
  read_only_reason: string | null;
  is_ready_for_brief: boolean;
  versions: OutlineVersion[];
};

export type OutlineWorkspaceReadiness = {
  total_outline_count: number;
  approved_outline_count: number;
  is_ready_for_briefs: boolean;
  warnings: string[];
};

export type OutlineWorkspace = {
  series: Series;
  outlines: EpisodeOutline[];
  readiness: OutlineWorkspaceReadiness;
};

export type OutlineUpdatePayload = {
  title?: string | null;
  outline_markdown: string;
};

export type OutlineRegeneratePayload = {
  instruction?: string | null;
};

export type BriefVersion = {
  id: string;
  brief_id: string;
  series_id: string;
  episode_id: string;
  outline_id: string;
  outline_version_id: string;
  version_number: number;
  title: string;
  brief_markdown: string;
  source: BriefVersionSource;
  created_at: string;
};

export type EpisodeBrief = {
  id: string;
  series_id: string;
  episode_id: string;
  kind: BriefKind;
  title: string;
  brief_markdown: string;
  status: BriefStatus;
  current_version_id: string | null;
  approved_version_id: string | null;
  approved_at: string | null;
  approval_invalidated_at: string | null;
  created_at: string;
  updated_at: string;
  profile_id: string | null;
  profile_name: string | null;
  profile_role_title: string | null;
  version_count: number;
  latest_version_number: number | null;
  can_edit: boolean;
  read_only_reason: string | null;
  versions: BriefVersion[];
};

export type BriefEpisodeRequirement = {
  episode_id: string;
  episode_number: number;
  episode_title: string;
  host_profile_id: string | null;
  host_profile_name: string | null;
  guest_profile_id: string | null;
  guest_profile_name: string | null;
  outline_id: string | null;
  outline_status: EpisodeOutlineStatus | null;
  outline_current_version_id: string | null;
  missing_requirements: string[];
  can_generate: boolean;
};

export type BriefEpisodeWorkspace = {
  episode_id: string;
  episode_number: number;
  episode_title: string;
  episode_premise: string;
  episode_status: EpisodeStatus;
  requirement: BriefEpisodeRequirement;
  host_brief: EpisodeBrief | null;
  guest_brief: EpisodeBrief | null;
  pair_generated: boolean;
  pair_approved: boolean;
  pair_approved_at: string | null;
  approval_invalidated_at: string | null;
};

export type BriefWorkspaceReadiness = {
  total_episode_count: number;
  generated_episode_count: number;
  approved_episode_count: number;
  recordings_unlocked: boolean;
  warnings: string[];
};

export type BriefWorkspace = {
  series: Series;
  episodes: BriefEpisodeWorkspace[];
  readiness: BriefWorkspaceReadiness;
};

export type BriefUpdatePayload = {
  title?: string | null;
  brief_markdown: string;
};

export type BriefDownload = {
  blob: Blob;
  filename: string;
};

export type MediaAsset = {
  id: string;
  series_id: string;
  episode_id: string;
  kind: MediaAssetKind;
  status: MediaAssetStatus;
  storage_provider: string;
  storage_key: string;
  file_name: string;
  content_type: string;
  file_size_bytes: number;
  checksum_sha256: string;
  last_error: string | null;
  uploaded_at: string;
  archived_at: string | null;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
  signed_url: string | null;
  signed_url_expires_at: string | null;
};

export type MediaMetadata = {
  id: string;
  media_asset_id: string;
  series_id: string;
  episode_id: string;
  duration_seconds: number | null;
  width: number | null;
  height: number | null;
  frame_rate: string | null;
  codec: string | null;
  transcript_cue_count: number | null;
  transcript_language: string | null;
  generated_thumbnail_asset_id: string | null;
  metadata: Record<string, unknown>;
  extracted_at: string;
  created_at: string;
  updated_at: string;
};

export type MediaProcessingJob = {
  id: string;
  media_asset_id: string;
  series_id: string;
  episode_id: string;
  job_type: MediaProcessingJobType;
  status: MediaProcessingJobStatus;
  attempts: number;
  max_attempts: number;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SignedMediaUrl = {
  asset_id: string;
  url: string;
  expires_at: string;
};

export type EpisodeVideo = {
  id: string;
  series_id: string;
  episode_id: string;
  status: VideoStatus;
  file_path: string | null;
  file_name: string | null;
  content_type: string | null;
  file_size_bytes: number | null;
  media_asset_id: string | null;
  media_asset: MediaAsset | null;
  metadata: MediaMetadata | null;
  processing_jobs: MediaProcessingJob[];
  uploaded_at: string | null;
  locked_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Transcript = {
  id: string;
  series_id: string;
  episode_id: string;
  status: TranscriptStatus;
  file_path: string;
  file_name: string;
  content_type: string;
  file_size_bytes: number;
  media_asset_id: string | null;
  media_asset: MediaAsset | null;
  metadata: MediaMetadata | null;
  processing_jobs: MediaProcessingJob[];
  uploaded_at: string;
  processed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Thumbnail = {
  id: string;
  series_id: string;
  episode_id: string;
  status: ThumbnailStatus;
  is_selected: boolean;
  file_path: string;
  file_name: string;
  content_type: string;
  file_size_bytes: number;
  media_asset_id: string | null;
  media_asset: MediaAsset | null;
  metadata: MediaMetadata | null;
  processing_jobs: MediaProcessingJob[];
  uploaded_at: string;
  created_at: string;
  updated_at: string;
};

export type ClipSuggestion = {
  id: string;
  series_id: string;
  episode_id: string;
  slot_number: number;
  title: string;
  rationale: string;
  start_timecode: string;
  end_timecode: string;
  clip_file_path: string | null;
  clip_file_name: string | null;
  clip_content_type: string | null;
  clip_file_size_bytes: number | null;
  clip_media_asset_id: string | null;
  clip_uploaded_at: string | null;
  clip_media_uploaded: boolean;
  status: ClipSuggestionStatus;
  created_at: string;
  updated_at: string;
};

export type RecordingEpisodeWorkspace = {
  episode_id: string;
  episode_number: number;
  episode_title: string;
  episode_premise: string;
  episode_status: EpisodeStatus;
  brief_pair_approved: boolean;
  can_upload: boolean;
  upload_blockers: string[];
  video: EpisodeVideo;
  transcript: Transcript | null;
  thumbnails: Thumbnail[];
  selected_thumbnail: Thumbnail | null;
  clip_suggestions: ClipSuggestion[];
  video_file_uploaded: boolean;
  transcript_uploaded: boolean;
  suggested_short_clip_count: number;
  uploaded_short_clip_count: number;
  recording_complete: boolean;
  captions_ready: boolean;
  recording_locked: boolean;
  locked_at: string | null;
};

export type RecordingWorkspaceReadiness = {
  total_episode_count: number;
  complete_episode_count: number;
  transcript_ready_episode_count: number;
  suggested_short_clip_count: number;
  uploaded_short_clip_count: number;
  captions_unlocked: boolean;
  warnings: string[];
};

export type RecordingWorkspace = {
  series: Series;
  episodes: RecordingEpisodeWorkspace[];
  readiness: RecordingWorkspaceReadiness;
};

export type EpisodeVideoPlatformCaption = {
  id: string;
  series_id: string;
  episode_id: string;
  episode_video_id: string;
  clip_suggestion_id: string | null;
  video_kind: CaptionVideoKind;
  video_key: string;
  platform: CaptionPlatform;
  status: CaptionStatus;
  caption_text: string | null;
  generation_count: number;
  generated_at: string | null;
  created_at: string;
  updated_at: string;
  can_schedule: boolean;
  scheduling_locked_reason: string | null;
};

export type CaptionShortClipSlot = {
  clip_suggestion: ClipSuggestion;
  captions: EpisodeVideoPlatformCaption[];
  available_platforms: CaptionPlatform[];
  complete_caption_count: number;
};

export type CaptionEpisodeWorkspace = {
  episode_id: string;
  episode_number: number;
  episode_title: string;
  episode_premise: string;
  episode_status: EpisodeStatus;
  video_status: VideoStatus;
  transcript_status: TranscriptStatus | null;
  transcript_ready: boolean;
  caption_blockers: string[];
  video: EpisodeVideo;
  transcript: Transcript | null;
  full_episode_captions: EpisodeVideoPlatformCaption[];
  full_available_platforms: CaptionPlatform[];
  short_clip_slots: CaptionShortClipSlot[];
  ready_caption_count: number;
  total_caption_count: number;
};

export type CaptionWorkspaceReadiness = {
  total_caption_count: number;
  ready_caption_count: number;
  full_episode_ready_count: number;
  short_clip_ready_count: number;
  scheduling_unlocked: boolean;
  warnings: string[];
};

export type CaptionWorkspace = {
  series: Series;
  episodes: CaptionEpisodeWorkspace[];
  full_episode_platforms: CaptionPlatform[];
  short_clip_platforms: CaptionPlatform[];
  readiness: CaptionWorkspaceReadiness;
};

export type CaptionPlatformCreatePayload = {
  video_kind: CaptionVideoKind;
  platform: CaptionPlatform;
  clip_suggestion_id?: string | null;
};

export type CaptionUpdatePayload = {
  caption_text: string;
};

export type EpisodeVideoPlatformSchedule = {
  id: string;
  series_id: string;
  episode_id: string;
  episode_video_id: string;
  media_asset_id: string | null;
  caption_id: string;
  clip_suggestion_id: string | null;
  video_kind: CaptionVideoKind;
  video_key: string;
  platform: CaptionPlatform;
  status: ScheduleStatus;
  buffer_status: BufferPostStatus;
  buffer_account_id: string | null;
  buffer_channel_id: string | null;
  buffer_post_id: string | null;
  idempotency_key: string | null;
  scheduled_for: string;
  scheduled_caption_text: string;
  failure_reason: string | null;
  live_url: string | null;
  scheduled_at: string | null;
  published_at: string | null;
  cancelled_at: string | null;
  last_synced_at: string | null;
  next_retry_at: string | null;
  buffer_last_event_id: string | null;
  rate_limit_reset_at: string | null;
  retry_count: number;
  channel: BufferChannel | null;
  audit_logs: PublishingAuditLog[];
  created_at: string;
  updated_at: string;
};

export type BufferOAuthStart = {
  authorization_url: string;
  state: string;
  is_configured: boolean;
};

export type BufferAccount = {
  id: string;
  integration_id: string | null;
  buffer_account_id: string | null;
  organization_id: string | null;
  name: string;
  status: BufferAccountStatus;
  scopes: string[];
  token_expires_at: string | null;
  connected_at: string | null;
  last_synced_at: string | null;
  rate_limit: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type BufferChannel = {
  id: string;
  buffer_account_id: string;
  buffer_channel_id: string;
  service: string;
  name: string;
  display_name: string;
  avatar_url: string | null;
  is_enabled: boolean;
  is_queue_paused: boolean;
  raw_payload: Record<string, unknown>;
  last_synced_at: string | null;
  created_at: string;
  updated_at: string;
};

export type BufferChannelMapping = {
  id: string;
  platform: CaptionPlatform;
  buffer_channel_id: string;
  is_active: boolean;
  channel: BufferChannel | null;
  created_at: string;
  updated_at: string;
};

export type PublishingAuditLog = {
  id: string;
  schedule_id: string | null;
  buffer_account_id: string | null;
  buffer_channel_id: string | null;
  action: string;
  status: PublishingAuditStatus;
  idempotency_key: string | null;
  request_payload: Record<string, unknown>;
  response_payload: Record<string, unknown>;
  error_message: string | null;
  created_at: string;
};

export type BufferWebhook = {
  id: string;
  event_id: string | null;
  event_type: string;
  buffer_post_id: string | null;
  schedule_id: string | null;
  status: BufferWebhookStatus;
  signature_valid: boolean;
  payload: Record<string, unknown>;
  received_at: string;
  processed_at: string | null;
  created_at: string;
};

export type BufferWorkspace = {
  account: BufferAccount | null;
  channels: BufferChannel[];
  mappings: BufferChannelMapping[];
  audit_logs: PublishingAuditLog[];
  webhooks: BufferWebhook[];
  required: boolean;
  warnings: string[];
};

export type ScheduleRow = {
  caption_id: string;
  series_id: string;
  episode_id: string;
  episode_video_id: string;
  clip_suggestion_id: string | null;
  video_kind: CaptionVideoKind;
  video_key: string;
  platform: CaptionPlatform;
  caption_status: CaptionStatus;
  caption_text: string | null;
  schedule: EpisodeVideoPlatformSchedule | null;
  is_captioned: boolean;
  media_ready: boolean;
  schedule_ready: boolean;
  media_file_name: string | null;
  can_create_schedule: boolean;
  can_reschedule: boolean;
  schedule_locked_reason: string | null;
};

export type ScheduleShortClipSlot = {
  clip_suggestion: ClipSuggestion;
  rows: ScheduleRow[];
  scheduled_count: number;
  published_count: number;
  failed_count: number;
};

export type ScheduleEpisodeWorkspace = {
  episode_id: string;
  episode_number: number;
  episode_title: string;
  episode_premise: string;
  episode_status: EpisodeStatus;
  full_episode_rows: ScheduleRow[];
  short_clip_slots: ScheduleShortClipSlot[];
  eligible_count: number;
  scheduled_count: number;
  published_count: number;
  failed_count: number;
  locked_count: number;
};

export type BulkScheduleResult = {
  requested_count: number;
  scheduled_count: number;
  failed_count: number;
  skipped_count: number;
};

export type ScheduleWorkspaceReadiness = {
  total_row_count: number;
  eligible_row_count: number;
  scheduled_row_count: number;
  published_row_count: number;
  failed_row_count: number;
  locked_row_count: number;
  bulk_schedulable_count: number;
  warnings: string[];
};

export type ScheduleWorkspace = {
  series: Series;
  episodes: ScheduleEpisodeWorkspace[];
  readiness: ScheduleWorkspaceReadiness;
  buffer: BufferWorkspace | null;
  bulk_result: BulkScheduleResult | null;
};

export type ScheduleCreatePayload = {
  caption_id: string;
  scheduled_for: string;
};

export type BulkSchedulePayload = {
  scheduled_for: string;
  caption_ids?: string[] | null;
  spacing_minutes?: number;
};

export type ScheduleUpdatePayload = {
  scheduled_for?: string | null;
  scheduled_caption_text?: string | null;
};

export type ScheduleReschedulePayload = {
  scheduled_for: string;
  scheduled_caption_text?: string | null;
};

export type PlanLockReadiness = {
  is_ready: boolean;
  missing_episode_count: number;
  missing_episode_ids: string[];
  warnings: string[];
};

export type EpisodePlanWorkspace = {
  series: Series;
  episodes: Episode[];
  outlines: EpisodeOutlineSummary[];
  selected_narrative_id: string;
  is_locked: boolean;
  lock_readiness: PlanLockReadiness;
};

export type EpisodeDraftPayload = {
  title: string;
  premise: string;
};

export type EpisodeDraftGenerationPayload = {
  instruction: string;
  episode_id?: string | null;
  current_title?: string | null;
  current_premise?: string | null;
};

export type EpisodeDraftGenerationResponse = EpisodeDraftPayload;

export type EpisodeAssignmentPayload = {
  host_profile_id?: string | null;
  guest_profile_id?: string | null;
  guest_name_override?: string | null;
};
