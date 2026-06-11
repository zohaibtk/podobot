import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import {
  AlertTriangle,
  CheckCircle2,
  FlaskConical,
  Power,
  Save,
  Settings2,
  X,
  XCircle
} from "lucide-react";

import { ErrorState } from "@/design-system/components/ErrorState";
import { LoadingState } from "@/design-system/components/LoadingState";
import { StatusBadge } from "@/design-system/components/StatusBadge";
import { useBodyScrollLock } from "@/design-system/hooks/useBodyScrollLock";
import {
  useDisableResearchSource,
  useEnableResearchSource,
  useResearchSource,
  useTestResearchSource,
  useUpdateResearchSource
} from "@/features/integrations/hooks";
import type {
  ResearchSource,
  ResearchSourceUpdatePayload
} from "@/shared/types/researchSources";

type ResearchSourceConfigDrawerProps = {
  canManage: boolean;
  isOpen: boolean;
  onClose: () => void;
  sourceId: string | null;
};

export function ResearchSourceConfigDrawer({
  canManage,
  isOpen,
  onClose,
  sourceId
}: ResearchSourceConfigDrawerProps) {
  const sourceQuery = useResearchSource(isOpen ? sourceId ?? undefined : undefined);
  const source = sourceQuery.data;
  const updateMutation = useUpdateResearchSource(sourceId ?? undefined);
  const enableMutation = useEnableResearchSource();
  const disableMutation = useDisableResearchSource();
  const testMutation = useTestResearchSource();
  const [priority, setPriority] = useState(0);
  const [critical, setCritical] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [clearApiKey, setClearApiKey] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ isSuccess: boolean; message: string } | null>(
    null
  );
  useBodyScrollLock(isOpen);

  useEffect(() => {
    if (!source) {
      return;
    }
    setPriority(source.priority);
    setCritical(source.critical);
    setApiKey("");
    setClearApiKey(false);
    setLocalError(null);
    setFeedback(null);
  }, [source]);

  const isDirty = useMemo(() => {
    if (!source) {
      return false;
    }
    return (
      priority !== source.priority ||
      critical !== source.critical ||
      apiKey.trim().length > 0 ||
      clearApiKey
    );
  }, [apiKey, clearApiKey, critical, priority, source]);

  if (!isOpen) {
    return null;
  }

  const isBusy =
    updateMutation.isPending ||
    enableMutation.isPending ||
    disableMutation.isPending ||
    testMutation.isPending;

  async function handleSave() {
    if (!source || !canManage) {
      return;
    }
    setLocalError(null);
    setFeedback(null);
    try {
      await savePendingChanges();
      setFeedback({ isSuccess: true, message: `${source.name} configuration saved.` });
    } catch (error) {
      setLocalError(errorMessage(error));
    }
  }

  function updatePayload(): ResearchSourceUpdatePayload {
    return {
      critical,
      priority,
      ...(apiKey.trim() ? { api_key: apiKey.trim() } : {}),
      ...(clearApiKey ? { clear_api_key: true } : {})
    };
  }

  async function savePendingChanges() {
    const updated = await updateMutation.mutateAsync(updatePayload());
    setApiKey("");
    setClearApiKey(false);
    return updated;
  }

  async function handleToggle(nextSource: ResearchSource) {
    if (!canManage) {
      return;
    }
    setLocalError(null);
    setFeedback(null);
    try {
      if (nextSource.enabled) {
        await disableMutation.mutateAsync(nextSource.id);
        setFeedback({ isSuccess: true, message: `${nextSource.name} disabled.` });
      } else {
        await enableMutation.mutateAsync(nextSource.id);
        setFeedback({ isSuccess: true, message: `${nextSource.name} enabled.` });
      }
    } catch (error) {
      setLocalError(errorMessage(error));
    }
  }

  async function handleTest(nextSource: ResearchSource) {
    if (!canManage) {
      return;
    }
    setLocalError(null);
    setFeedback(null);
    try {
      const sourceToTest = isDirty ? await savePendingChanges() : nextSource;
      const result = await testMutation.mutateAsync(sourceToTest.id);
      setFeedback({ isSuccess: result.success, message: result.message });
    } catch (error) {
      setLocalError(errorMessage(error));
    }
  }

  const drawer = (
    <div
      aria-modal="true"
      className="fixed inset-0 z-[1000] overflow-hidden bg-streamly-coal/35 backdrop-blur-sm"
      role="dialog"
    >
      <button
        aria-label="Close research source configuration"
        className="absolute inset-0 h-full w-full cursor-default"
        onClick={onClose}
        type="button"
      />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-xl flex-col border-l border-streamly-lavenderStrong bg-white shadow-streamly-soft">
        <div className="border-b border-streamly-lavenderStrong p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="streamly-kicker">Research source</p>
              <h2 className="mt-2 font-streamly-platform text-2xl font-extrabold text-streamly-coal">
                {source?.name ?? "Source configuration"}
              </h2>
              {source ? (
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <StatusBadge label={source.status} tone={source.status} />
                  <span className="text-sm font-bold text-streamly-purpleBlue">
                    {formatLabel(source.provider_type)}
                  </span>
                </div>
              ) : null}
            </div>
            <button
              aria-label="Close research source configuration"
              className="grid h-9 w-9 place-items-center rounded-streamly-pill text-streamly-purpleBlue hover:bg-streamly-wash"
              onClick={onClose}
              type="button"
            >
              <X aria-hidden className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-5">
          {sourceQuery.isLoading ? <LoadingState label="Loading source configuration" /> : null}

          {sourceQuery.isError ? (
            <ErrorState
              actionLabel="Retry"
              description="Research source configuration could not be loaded."
              onAction={() => void sourceQuery.refetch()}
              title="Source unavailable"
            />
          ) : null}

          {source ? (
            <div className="space-y-5">
              <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-streamly-wash/70 p-4">
                <div className="grid gap-3 sm:grid-cols-3">
                  <StatusTile
                    label="API key"
                    value={source.missing_configuration ? "Missing" : "Saved"}
                  />
                  <StatusTile label="Priority" value={String(source.priority)} />
                  <StatusTile
                    label="Type"
                    value={source.critical ? "Critical" : "Optional"}
                  />
                </div>
                {source.missing_configuration ? (
                  <div className="mt-4 flex items-start gap-3 rounded-streamly-lg border border-amber-100 bg-amber-50 px-3 py-3 text-sm font-bold text-amber-800">
                    <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>API key required.</span>
                  </div>
                ) : null}
                {source.last_failure_reason ? (
                  <div className="mt-4 flex items-start gap-3 rounded-streamly-lg border border-amber-100 bg-amber-50 px-3 py-3 text-sm font-bold text-amber-800">
                    <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>{source.last_failure_reason}</span>
                  </div>
                ) : null}
              </section>

              {feedback ? (
                <ResultBanner
                  isSuccess={feedback.isSuccess}
                  message={feedback.message}
                />
              ) : null}

              {localError ? <ResultBanner isSuccess={false} message={localError} /> : null}

              <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
                <div className="flex items-center gap-2 text-streamly-violet">
                  <Settings2 aria-hidden className="h-4 w-4" />
                  <h3 className="font-streamly-platform text-base font-extrabold text-streamly-coal">
                    Source settings
                  </h3>
                </div>
                <div className="mt-4 grid gap-4">
                  <label className="grid gap-2">
                    <span className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
                      Priority
                    </span>
                    <input
                      className="streamly-search w-full max-w-none"
                      disabled={!canManage}
                      max={1000}
                      min={0}
                      onChange={(event) => setPriority(Number(event.target.value))}
                      type="number"
                      value={priority}
                    />
                  </label>
                  <label className="flex items-center justify-between gap-4 rounded-streamly-xl bg-streamly-wash px-4 py-3">
                    <span className="text-sm font-extrabold text-streamly-coal">
                      Critical source
                    </span>
                    <input
                      checked={critical}
                      className="h-5 w-5 accent-streamly-electric"
                      disabled={!canManage}
                      onChange={(event) => setCritical(event.target.checked)}
                      type="checkbox"
                    />
                  </label>
                </div>
              </section>

              <section className="rounded-streamly-xl border border-streamly-lavenderStrong bg-white p-4 shadow-streamly-card">
                <h3 className="font-streamly-platform text-base font-extrabold text-streamly-coal">
                  API key
                </h3>
                <div className="mt-4 grid gap-4">
                  <label className="grid gap-2">
                    <span className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
                      New API key
                    </span>
                    <input
                      autoComplete="off"
                      className="streamly-search w-full max-w-none"
                      disabled={!canManage || clearApiKey}
                      onChange={(event) => setApiKey(event.target.value)}
                      placeholder={
                        source.missing_configuration
                          ? "Paste provider API key"
                          : "Leave blank to keep saved key"
                      }
                      type="password"
                      value={apiKey}
                    />
                  </label>
                  <label className="flex items-center justify-between gap-4 rounded-streamly-xl bg-streamly-wash px-4 py-3">
                    <span className="text-sm font-extrabold text-streamly-coal">
                      Clear saved API key
                    </span>
                    <input
                      checked={clearApiKey}
                      className="h-5 w-5 accent-streamly-electric"
                      disabled={!canManage}
                      onChange={(event) => {
                        setClearApiKey(event.target.checked);
                        if (event.target.checked) {
                          setApiKey("");
                        }
                      }}
                      type="checkbox"
                    />
                  </label>
                </div>
              </section>
            </div>
          ) : null}
        </div>

        {source ? (
          <div className="border-t border-streamly-lavenderStrong p-5">
            {canManage ? (
              <div className="flex flex-wrap justify-between gap-3">
                <button
                  className="streamly-button-secondary disabled:opacity-50"
                  disabled={isBusy}
                  onClick={() => void handleToggle(source)}
                  type="button"
                >
                  <Power aria-hidden className="h-4 w-4" />
                  {source.enabled ? "Disable" : "Enable"}
                </button>
                <div className="flex flex-wrap gap-3">
                  <button
                    className="streamly-button-secondary disabled:opacity-50"
                    disabled={isBusy || !source.enabled}
                    onClick={() => void handleTest(source)}
                    type="button"
                  >
                    <FlaskConical aria-hidden className="h-4 w-4" />
                    Test
                  </button>
                  <button
                    className="streamly-button-primary disabled:opacity-50"
                    disabled={isBusy || !isDirty}
                    onClick={() => void handleSave()}
                    type="button"
                  >
                    <Save aria-hidden className="h-4 w-4" />
                    Save
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-sm font-bold leading-6 text-streamly-purpleBlue">
                You can view source status. Configuration changes require integration.manage.
              </p>
            )}
          </div>
        ) : null}
      </aside>
    </div>
  );

  if (typeof document === "undefined") {
    return drawer;
  }

  return createPortal(drawer, document.body);
}

function StatusTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-streamly-lg bg-white px-3 py-3">
      <p className="text-xs font-extrabold uppercase text-streamly-purpleBlue">
        {label}
      </p>
      <p className="mt-1 break-words text-sm font-extrabold text-streamly-coal">
        {value}
      </p>
    </div>
  );
}

function ResultBanner({ isSuccess, message }: { isSuccess: boolean; message: string }) {
  const Icon = isSuccess ? CheckCircle2 : XCircle;
  return (
    <div
      className={[
        "flex items-start gap-3 rounded-streamly-lg border px-3 py-3 text-sm font-bold",
        isSuccess
          ? "border-emerald-100 bg-emerald-50 text-emerald-700"
          : "border-red-100 bg-red-50 text-red-700"
      ].join(" ")}
    >
      <Icon aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ");
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Research source action failed.";
}
