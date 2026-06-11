import { useMemo, useState } from "react";
import {
  AlertTriangle,
  Braces,
  CheckCircle2,
  FlaskConical,
  History,
  ServerCog,
  ShieldAlert,
  Wrench
} from "lucide-react";

import { EmptyState } from "@/design-system/components/EmptyState";
import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { MCPRunHistoryDrawer } from "@/features/mcp/MCPRunHistoryDrawer";
import { useMCPRuns, useMCPServers, useMCPTools, useTestMCPServer } from "@/features/mcp/hooks";
import type { MCPServer, MCPTool } from "@/shared/types/mcp";

export function MCPAdminPanel() {
  const serversQuery = useMCPServers();
  const toolsQuery = useMCPTools();
  const [runCursor, setRunCursor] = useState<string | null>(null);
  const [runPageSize] = useState(30);
  const runsQuery = useMCPRuns({ limit: runPageSize, cursor: runCursor });
  const testServer = useTestMCPServer();
  const [selectedServerKey, setSelectedServerKey] = useState<string | null>(null);
  const [selectedTool, setSelectedTool] = useState<MCPTool | null>(null);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const servers = useMemo(
    () => serversQuery.data?.items ?? [],
    [serversQuery.data?.items]
  );
  const tools = useMemo(() => toolsQuery.data?.items ?? [], [toolsQuery.data?.items]);
  const filteredTools = useMemo(
    () =>
      selectedServerKey
        ? tools.filter((tool) => tool.server_key === selectedServerKey)
        : tools,
    [selectedServerKey, tools]
  );
  const criticalBroken = servers.filter(
    (server) => server.is_critical && ["broken", "disabled"].includes(server.status)
  );

  async function handleTest(server: MCPServer) {
    setFeedback(null);
    const result = await testServer.mutateAsync(server.key);
    setFeedback(result.message);
    setSelectedRunId(result.run.id);
  }

  return (
    <section className="space-y-5">
      <div className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="streamly-kicker">MCP layer</p>
            <h2 className="font-streamly-platform text-2xl font-extrabold text-streamly-coal">
              Tool contracts and execution health
            </h2>
            <p className="mt-2 max-w-3xl text-sm font-bold leading-6 text-streamly-purpleBlue">
              MCP keeps agents and workflow services behind stable tool contracts, with
              auditable runs, masked auth state, retries, and critical-path blockers.
            </p>
          </div>
          <button
            className="inline-flex items-center gap-2 rounded-streamly-pill bg-white px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card hover:bg-streamly-wash"
            onClick={() => setIsHistoryOpen(true)}
            type="button"
          >
            <History aria-hidden className="h-4 w-4" />
            Run history
          </button>
        </div>
      </div>

      {serversQuery.isLoading || toolsQuery.isLoading ? (
        <LoadingState label="Loading MCP registry" />
      ) : null}

      {serversQuery.isError || toolsQuery.isError ? (
        <ErrorState
          actionLabel="Retry"
          description="MCP servers and tools could not be loaded."
          onAction={() => {
            void serversQuery.refetch();
            void toolsQuery.refetch();
          }}
          title="MCP registry unavailable"
        />
      ) : null}

      {!serversQuery.isLoading && !serversQuery.isError ? (
        <>
          {criticalBroken.length ? (
            <div className="rounded-streamly-xl border border-red-100 bg-red-50 p-4 text-red-700">
              <div className="flex items-start gap-3">
                <ShieldAlert aria-hidden className="mt-0.5 h-5 w-5 shrink-0" />
                <div>
                  <p className="font-streamly-platform text-base font-extrabold">
                    Critical MCP server blocking dependent workflows
                  </p>
                  <div className="mt-2 space-y-1 text-sm font-bold">
                    {criticalBroken.map((server) => (
                      <p key={server.id}>
                        {server.name}: {server.failure_reason ?? server.status}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {feedback ? (
            <div className="rounded-streamly-xl border border-emerald-100 bg-emerald-50 p-4 text-sm font-extrabold text-emerald-700">
              {feedback}
            </div>
          ) : null}

          <ServerCards
            isTesting={testServer.isPending}
            onSelect={setSelectedServerKey}
            onTest={(server) => void handleTest(server)}
            selectedServerKey={selectedServerKey}
            servers={servers}
          />

          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_22rem]">
            <ToolsTable
              onSelect={setSelectedTool}
              selectedTool={selectedTool}
              tools={filteredTools}
            />
            <ToolDetail tool={selectedTool} />
          </div>
        </>
      ) : null}

      <MCPRunHistoryDrawer
        isError={runsQuery.isError}
        isLoading={runsQuery.isLoading}
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onLoadMore={() => setRunCursor(runsQuery.data?.next_cursor ?? null)}
        onReset={() => setRunCursor(null)}
        onSelectRun={setSelectedRunId}
        hasNext={runsQuery.data?.has_next ?? false}
        pageSize={runsQuery.data?.page_size ?? runPageSize}
        runs={runsQuery.data?.items ?? []}
        selectedRunId={selectedRunId}
      />
    </section>
  );
}

function ServerCards({
  servers,
  selectedServerKey,
  isTesting,
  onSelect,
  onTest
}: {
  servers: MCPServer[];
  selectedServerKey: string | null;
  isTesting: boolean;
  onSelect: (serverKey: string | null) => void;
  onTest: (server: MCPServer) => void;
}) {
  if (!servers.length) {
    return (
      <EmptyState
        description="MCP server records are registered by the backend when adapters are available."
        title="No MCP servers configured"
      />
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {servers.map((server) => {
        const isSelected = selectedServerKey === server.key;
        return (
          <article
            className={[
              "rounded-streamly-xl border bg-white p-4 shadow-streamly-card",
              isSelected ? "border-streamly-electric" : "border-streamly-lavenderStrong"
            ].join(" ")}
            key={server.id}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric">
                <ServerCog aria-hidden className="h-5 w-5" />
              </div>
              <StatusBadge label={server.status} tone={server.status} />
            </div>
            <h3 className="mt-3 font-streamly-platform text-lg font-extrabold text-streamly-coal">
              {server.name}
            </h3>
            <p className="mt-1 line-clamp-2 text-sm font-bold leading-5 text-streamly-purpleBlue">
              {server.purpose}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge
                label={server.is_critical ? "critical" : "optional"}
                tone={server.is_critical ? "broken" : "neutral"}
              />
              <StatusBadge label={`${server.tool_count} tools`} tone="neutral" />
              <StatusBadge
                label={server.auth_config?.has_secret ? "masked auth" : "no secret"}
                tone="neutral"
              />
            </div>
            {server.failure_reason ? (
              <p className="mt-3 flex gap-2 text-xs font-bold leading-5 text-amber-800">
                <AlertTriangle aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {server.failure_reason}
              </p>
            ) : null}
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                className="rounded-streamly-pill bg-streamly-wash px-3 py-2 text-xs font-extrabold text-streamly-purpleBlue hover:bg-streamly-lavender"
                onClick={() => onSelect(isSelected ? null : server.key)}
                type="button"
              >
                {isSelected ? "All tools" : "Filter tools"}
              </button>
              <button
                className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-electric px-3 py-2 text-xs font-extrabold text-white shadow-streamly-button disabled:opacity-50"
                disabled={isTesting}
                onClick={() => onTest(server)}
                type="button"
              >
                <FlaskConical aria-hidden className="h-3.5 w-3.5" />
                Test
              </button>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function ToolsTable({
  tools,
  selectedTool,
  onSelect
}: {
  tools: MCPTool[];
  selectedTool: MCPTool | null;
  onSelect: (tool: MCPTool) => void;
}) {
  if (!tools.length) {
    return (
      <EmptyState
        description="Select another server or clear the filter to view registered MCP tools."
        title="No MCP tools match"
      />
    );
  }

  return (
    <section className="overflow-hidden rounded-streamly-xl border border-streamly-lavenderStrong bg-white shadow-streamly-card">
      <div className="hidden grid-cols-[minmax(0,1.2fr)_8rem_9rem_10rem] border-b border-streamly-lavenderStrong px-4 py-3 text-xs font-extrabold uppercase text-streamly-purpleBlue lg:grid">
        <span>Tool</span>
        <span>Server</span>
        <span>Status</span>
        <span>Callers</span>
      </div>
      {tools.map((tool) => {
        const isSelected = selectedTool?.id === tool.id;
        return (
          <button
            className={[
              "grid w-full gap-3 border-b border-streamly-lavenderStrong px-4 py-4 text-left transition last:border-b-0 lg:grid-cols-[minmax(0,1.2fr)_8rem_9rem_10rem] lg:items-center",
              isSelected ? "bg-streamly-lavender" : "hover:bg-streamly-wash"
            ].join(" ")}
            key={tool.id}
            onClick={() => onSelect(tool)}
            type="button"
          >
            <span className="flex items-start gap-3">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric">
                <Wrench aria-hidden className="h-4 w-4" />
              </span>
              <span>
                <span className="block font-streamly-platform text-sm font-extrabold text-streamly-coal">
                  {tool.display_name}
                </span>
                <span className="mt-1 block text-xs font-bold text-[var(--streamly-text-muted)]">
                  {tool.key}
                </span>
              </span>
            </span>
            <StatusBadge label={tool.server_key} tone="neutral" />
            <StatusBadge label={tool.status} tone={tool.status} />
            <span className="text-xs font-extrabold text-streamly-purpleBlue">
              {tool.allowed_callers.join(", ")}
            </span>
          </button>
        );
      })}
    </section>
  );
}

function ToolDetail({ tool }: { tool: MCPTool | null }) {
  if (!tool) {
    return (
      <aside className="rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash/70 p-5">
        <div className="grid h-10 w-10 place-items-center rounded-streamly-pill bg-white text-streamly-electric shadow-streamly-card">
          <Braces aria-hidden className="h-5 w-5" />
        </div>
        <h3 className="mt-3 font-streamly-platform text-lg font-extrabold text-streamly-coal">
          Select a tool contract
        </h3>
        <p className="mt-2 text-sm font-bold leading-6 text-streamly-purpleBlue">
          Inspect schemas, retry policy, caller permissions, and circuit breaker settings.
        </p>
      </aside>
    );
  }

  return (
    <aside className="space-y-4 rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-5 shadow-streamly-card">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge label={tool.status} tone={tool.status} />
          <StatusBadge
            label={tool.auth_required ? "auth required" : "no auth"}
            tone="neutral"
          />
          {tool.is_critical ? <StatusBadge label="critical" tone="broken" /> : null}
        </div>
        <h3 className="mt-3 font-streamly-platform text-xl font-extrabold text-streamly-coal">
          {tool.display_name}
        </h3>
        <p className="mt-2 text-sm font-bold leading-6 text-streamly-purpleBlue">
          {tool.description}
        </p>
      </div>
      <PolicyMetric label="Timeout" value={`${tool.timeout_ms} ms`} />
      <PolicyMetric label="Allowed callers" value={tool.allowed_callers.join(", ")} />
      <SchemaPreview label="Input schema" value={tool.input_schema} />
      <SchemaPreview label="Output schema" value={tool.output_schema} />
    </aside>
  );
}

function PolicyMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-streamly-lg border border-streamly-lavenderStrong bg-streamly-wash/70 px-3 py-3">
      <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">{label}</p>
      <p className="mt-1 text-sm font-extrabold text-streamly-coal">{value}</p>
    </div>
  );
}

function SchemaPreview({ label, value }: { label: string; value: Record<string, unknown> }) {
  return (
    <section>
      <div className="flex items-center gap-2 text-streamly-violet">
        <CheckCircle2 aria-hidden className="h-4 w-4" />
        <p className="text-xs font-extrabold uppercase">{label}</p>
      </div>
      <pre className="mt-2 max-h-44 overflow-auto rounded-streamly-lg bg-streamly-coal p-3 text-xs font-bold leading-5 text-white">
        {JSON.stringify(value, null, 2)}
      </pre>
    </section>
  );
}
