import {
  AlertTriangle,
  ExternalLink,
  Link2,
  RefreshCw,
  Share2
} from "lucide-react";

import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { usePermissions } from "@/features/auth/hooks";
import {
  useBufferWorkspace,
  useStartBufferOAuth,
  useSyncBufferChannels,
  useUpdateBufferChannelMapping
} from "@/features/integrations/hooks";
import type {
  BufferChannel,
  BufferChannelMapping,
  CaptionPlatform
} from "@/shared/types/series";

const PLATFORM_ORDER: CaptionPlatform[] = [
  "linkedin",
  "facebook",
  "youtube",
  "instagram",
  "tiktok",
  "x"
];

const PLATFORM_SERVICES: Record<CaptionPlatform, string[]> = {
  linkedin: ["linkedin"],
  facebook: ["facebook", "facebook_pages"],
  youtube: ["youtube"],
  instagram: ["instagram"],
  tiktok: ["tiktok"],
  x: ["x", "twitter"]
};

export function BufferIntegrationSection() {
  const { hasPermission } = usePermissions();
  const canManage = hasPermission("integration.manage");
  const workspaceQuery = useBufferWorkspace();
  const connectMutation = useStartBufferOAuth();
  const syncMutation = useSyncBufferChannels();
  const mappingMutation = useUpdateBufferChannelMapping();
  const workspace = workspaceQuery.data;
  const account = workspace?.account ?? null;
  const warnings = workspace ? visibleWarnings(workspace.warnings, Boolean(account)) : [];
  const isBusy =
    connectMutation.isPending || syncMutation.isPending || mappingMutation.isPending;
  const mappedCount = workspace?.mappings.filter((mapping) => mapping.channel).length ?? 0;

  async function handleMappingChange(platform: CaptionPlatform, channelId: string) {
    if (!channelId) {
      return;
    }
    await mappingMutation.mutateAsync({ platform, channelId });
  }

  return (
    <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="streamly-kicker">Publishing integration</p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h2 className="font-streamly-platform text-2xl font-extrabold text-streamly-coal">
              Buffer
            </h2>
            <StatusBadge
              label={account?.status ?? "not connected"}
              tone={account?.status === "connected" ? "healthy" : "warning"}
            />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            className="streamly-button-secondary disabled:opacity-50"
            disabled={!canManage || isBusy}
            onClick={() => void connectMutation.mutateAsync()}
            type="button"
          >
            <ExternalLink aria-hidden className="h-4 w-4" />
            Connect
          </button>
          <button
            className="streamly-button-primary disabled:opacity-50"
            disabled={!canManage || isBusy || !account}
            onClick={() => void syncMutation.mutateAsync()}
            type="button"
          >
            <RefreshCw aria-hidden className="h-4 w-4" />
            Sync
          </button>
        </div>
      </div>

      {workspaceQuery.isLoading ? (
        <div className="mt-5">
          <LoadingState label="Loading Buffer" />
        </div>
      ) : null}

      {workspaceQuery.isError ? (
        <div className="mt-5">
          <ErrorState
            actionLabel="Retry"
            description="Buffer integration status could not be loaded."
            onAction={() => void workspaceQuery.refetch()}
            title="Buffer unavailable"
          />
        </div>
      ) : null}

      {workspace ? (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <BufferMetric label="Account" value={account?.name ?? "Not connected"} />
            <BufferMetric label="Channels" value={String(workspace.channels.length)} />
            <BufferMetric label="Mapped" value={`${mappedCount}/${workspace.mappings.length}`} />
          </div>

          {warnings.length ? (
            <div className="mt-4 grid gap-2">
              {warnings.map((warning) => (
                <div
                  className="flex items-start gap-3 rounded-streamly-lg border border-amber-100 bg-amber-50 px-3 py-3 text-sm font-bold text-amber-800"
                  key={warning}
                >
                  <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{warning}</span>
                </div>
              ))}
            </div>
          ) : null}

          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {sortedMappings(workspace.mappings).map((mapping) => (
              <ChannelMappingRow
                channels={workspace.channels}
                disabled={!canManage || isBusy || workspace.channels.length === 0}
                key={mapping.id}
                mapping={mapping}
                onChange={handleMappingChange}
              />
            ))}
            {!workspace.mappings.length ? (
              <div className="rounded-streamly-lg bg-streamly-wash px-4 py-3 text-sm font-bold text-streamly-purpleBlue">
                Sync channels to create platform mappings.
              </div>
            ) : null}
          </div>
        </>
      ) : null}
    </section>
  );
}

function BufferMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-streamly-lg bg-streamly-wash px-4 py-3">
      <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">{label}</p>
      <p className="mt-1 truncate text-sm font-extrabold text-streamly-coal">{value}</p>
    </div>
  );
}

function ChannelMappingRow({
  channels,
  disabled,
  mapping,
  onChange
}: {
  channels: BufferChannel[];
  disabled: boolean;
  mapping: BufferChannelMapping;
  onChange: (platform: CaptionPlatform, channelId: string) => Promise<void>;
}) {
  const matchingChannels = channelsForPlatform(channels, mapping.platform);

  return (
    <label className="grid gap-2 rounded-streamly-lg border border-streamly-lavenderStrong px-3 py-3">
      <span className="flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-2 text-xs font-extrabold uppercase text-streamly-purpleBlue">
          <Share2 aria-hidden className="h-3.5 w-3.5" />
          {platformLabel(mapping.platform)}
        </span>
        {mapping.channel ? (
          <span className="inline-flex items-center gap-1.5 text-xs font-extrabold text-emerald-700">
            <Link2 aria-hidden className="h-3.5 w-3.5" />
            mapped
          </span>
        ) : null}
      </span>
      <select
        className="streamly-search w-full max-w-none"
        disabled={disabled || matchingChannels.length === 0}
        onChange={(event) => void onChange(mapping.platform, event.target.value)}
        value={mapping.channel?.id ?? ""}
      >
        <option value="">Select channel</option>
        {matchingChannels.map((channel) => (
          <option key={channel.id} value={channel.id}>
            {channel.display_name || channel.name}
          </option>
        ))}
      </select>
    </label>
  );
}

function sortedMappings(mappings: BufferChannelMapping[]) {
  return [...mappings].sort(
    (left, right) =>
      PLATFORM_ORDER.indexOf(left.platform) - PLATFORM_ORDER.indexOf(right.platform)
  );
}

function channelsForPlatform(channels: BufferChannel[], platform: CaptionPlatform) {
  const services = PLATFORM_SERVICES[platform];
  const matching = channels.filter((channel) =>
    services.includes(channel.service.toLowerCase())
  );
  return matching.length ? matching : channels;
}

function platformLabel(platform: CaptionPlatform) {
  return platform === "x" ? "X" : platform.replaceAll("_", " ");
}

function visibleWarnings(warnings: string[], hasAccount: boolean) {
  if (hasAccount) {
    return warnings;
  }
  return warnings.slice(0, 1);
}
