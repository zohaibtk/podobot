from enum import StrEnum


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class AgentRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REQUIRES_HUMAN = "requires_human"


class PromptVersionStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class AgentOutputValidationStatus(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


class SeriesStatus(StrEnum):
    RESEARCHING = "researching"
    PLANNING = "planning"
    IN_PRODUCTION = "in_production"
    PARTIALLY_PUBLISHED = "partially_published"
    COMPLETE = "complete"
    ARCHIVED = "archived"


class DiscoveryStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class DiscoverySourceStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class ResearchSourceStatus(StrEnum):
    HEALTHY = "healthy"
    WARNING = "warning"
    FAILED = "failed"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


class ResearchSourceProviderType(StrEnum):
    REDDIT_JSON = "reddit_json"
    HN_ALGOLIA = "hn_algolia"
    YOUTUBE_DATA_API = "youtube_data_api"
    EXA = "exa"
    FIRECRAWL = "firecrawl"
    SERPAPI = "serpapi"
    PYTRENDS = "pytrends"
    OPENAI = "openai"
    GROK_X = "grok_x"
    GROQ = "groq"
    GEMINI = "gemini"


class ResearchSourceCategory(StrEnum):
    DISCOVERY = "discovery"
    SCRAPING = "scraping"
    TRENDS = "trends"
    LLM = "llm"


class ResearchRunType(StrEnum):
    DISCOVERY = "discovery"
    STRATEGY = "strategy"
    NARRATIVE_REGENERATION = "narrative_regeneration"
    TOPIC_GENERATION = "topic_generation"
    BRIEF_CONTEXT = "brief_context"
    MANUAL_RESEARCH = "manual_research"


class ResearchRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResearchRunSourceUsageStatus(StrEnum):
    USED = "used"
    SKIPPED_DISABLED = "skipped_disabled"
    FAILED = "failed"
    NO_RESULTS = "no_results"


class DiscoveryLedgerType(StrEnum):
    SOURCE = "source"
    SIGNAL = "signal"
    NARRATIVE_SUPPORT = "narrative_support"
    NARRATIVE_COUNTER = "narrative_counter"
    TOPIC_SUPPORT = "topic_support"
    STRATEGY_SUPPORT = "strategy_support"


class ResearchConfidenceLevel(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    WEAK = "Weak"


class ResearchScoreEntityType(StrEnum):
    RESEARCH_DOCUMENT = "research_document"
    NARRATIVE = "narrative"
    EPISODE_TOPIC = "episode_topic"
    STRATEGY_IDEA = "strategy_idea"
    OUTLINE = "outline"
    BRIEF = "brief"


class NarrativeStatus(StrEnum):
    CANDIDATE = "candidate"
    SELECTED = "selected"
    RETIRED = "retired"


class ProfileKind(StrEnum):
    HOST = "host"
    GUEST = "guest"


class EpisodeStatus(StrEnum):
    PLANNED = "planned"
    OUTLINED = "outlined"
    PROFILES_SET = "profiles_set"
    BRIEF_READY = "brief_ready"
    APPROVED = "approved"
    RECORDED = "recorded"
    CAPTIONING = "captioning"
    SCHEDULED = "scheduled"
    PARTIALLY_PUBLISHED = "partially_published"
    PUBLISHED = "published"


class EpisodeOutlineStatus(StrEnum):
    PLACEHOLDER = "placeholder"
    GENERATED = "generated"
    DRAFT = "draft"
    APPROVED = "approved"


class OutlineVersionSource(StrEnum):
    LOCK_GENERATED = "lock_generated"
    MANUAL_EDIT = "manual_edit"
    REGENERATION = "regeneration"


class BriefKind(StrEnum):
    HOST = "host"
    GUEST = "guest"


class BriefStatus(StrEnum):
    GENERATED = "generated"
    DRAFT = "draft"
    APPROVED = "approved"


class BriefVersionSource(StrEnum):
    GENERATION = "generation"
    MANUAL_EDIT = "manual_edit"
    REGENERATION = "regeneration"


class VideoStatus(StrEnum):
    MISSING = "missing"
    UPLOADED = "uploaded"
    COMPLETE = "complete"
    LOCKED = "locked"
    FAILED = "failed"


class TranscriptStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSED = "processed"
    FAILED = "failed"


class ThumbnailStatus(StrEnum):
    UPLOADED = "uploaded"
    SELECTED = "selected"


class ClipSuggestionStatus(StrEnum):
    SUGGESTED = "suggested"
    APPROVED = "approved"
    REJECTED = "rejected"


class MediaAssetKind(StrEnum):
    VIDEO = "video"
    TRANSCRIPT = "transcript"
    THUMBNAIL = "thumbnail"


class MediaAssetStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MediaProcessingJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class MediaProcessingJobType(StrEnum):
    METADATA_EXTRACTION = "metadata_extraction"
    TRANSCRIPT_PARSING = "transcript_parsing"
    THUMBNAIL_GENERATION = "thumbnail_generation"


class CaptionStatus(StrEnum):
    NOT_STARTED = "not_started"
    READY = "ready"
    FAILED = "failed"


class CaptionVideoKind(StrEnum):
    FULL_EPISODE = "full_episode"
    SHORT_CLIP = "short_clip"


class Platform(StrEnum):
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    X = "x"


class ScheduleStatus(StrEnum):
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BufferPostStatus(StrEnum):
    QUEUED = "queued"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BufferAccountStatus(StrEnum):
    DISCONNECTED = "disconnected"
    OAUTH_PENDING = "oauth_pending"
    CONNECTED = "connected"
    EXPIRED = "expired"
    REVOKED = "revoked"


class BufferWebhookStatus(StrEnum):
    RECEIVED = "received"
    PROCESSED = "processed"
    IGNORED = "ignored"
    FAILED = "failed"


class PublishingAuditStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    RETRY_SCHEDULED = "retry_scheduled"


class StrategyIdeaStatus(StrEnum):
    PROPOSED = "proposed"
    IN_REVIEW = "in_review"
    DISMISSED = "dismissed"
    CONVERTED = "converted"


class IntegrationType(StrEnum):
    BUFFER = "buffer"
    OPENAI = "openai"
    RESEARCH_API = "research_api"
    TRANSCRIPTION = "transcription"


class IntegrationStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BROKEN = "broken"
    NOT_CONFIGURED = "not_configured"
    DISABLED = "disabled"


class MCPServerStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BROKEN = "broken"
    NOT_CONFIGURED = "not_configured"
    DISABLED = "disabled"


class MCPToolStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class MCPToolRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkspaceUserStatus(StrEnum):
    ACTIVE = "active"
    INVITED = "invited"
    SUSPENDED = "suspended"


class UserInvitationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class SeriesStage(StrEnum):
    DISCOVERY = "discovery"
    NARRATIVE = "narrative"
    PLAN = "plan"
    OUTLINES = "outlines"
    BRIEFS = "briefs"
    RECORDINGS = "recordings"
    CAPTIONS = "captions"
    SCHEDULE = "schedule"
