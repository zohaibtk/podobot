import { useSyncExternalStore } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  X,
  type LucideIcon
} from "lucide-react";

import {
  dismissToast,
  getToasts,
  subscribeToasts,
  type Toast,
  type ToastKind
} from "@/shared/toasts/store";

export function Toaster() {
  const toasts = useSyncExternalStore(subscribeToasts, getToasts, getToasts);

  if (!toasts.length) {
    return null;
  }

  return (
    <div
      aria-live="polite"
      aria-relevant="additions text"
      className="pointer-events-none fixed right-4 top-4 z-[1200] flex w-[min(27rem,calc(100vw-2rem))] flex-col gap-3 sm:right-6 sm:top-6"
    >
      {toasts.map((toast) => (
        <ToastCard key={toast.id} toast={toast} />
      ))}
    </div>
  );
}

function ToastCard({ toast }: { toast: Toast }) {
  const visual = toastVisual(toast.kind);
  const Icon = visual.Icon;

  return (
    <div
      className={[
        "pointer-events-auto overflow-hidden rounded-streamly-xl border bg-white shadow-[0_24px_70px_rgba(13,0,13,0.28),0_0_0_1px_rgba(217,200,255,0.72)] motion-safe:animate-[streamly-toast-in_260ms_var(--streamly-ease)_both]",
        visual.card
      ].join(" ")}
      role={toast.kind === "failure" ? "alert" : "status"}
    >
      <div className={["h-1 w-full", visual.accent].join(" ")} />
      <div className="flex items-start gap-3 px-4 py-3.5">
        <span
          className={[
            "mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-streamly-pill shadow-streamly-card",
            visual.iconShell
          ].join(" ")}
        >
          <Icon
            aria-hidden
            className={[
              "h-[1.125rem] w-[1.125rem]",
              visual.icon,
              toast.kind === "processing" ? "animate-spin" : ""
            ].join(" ")}
          />
        </span>
        <div className="min-w-0 flex-1 pt-0.5">
          <p className="font-streamly-platform text-sm font-extrabold leading-5 text-streamly-coal">
            {toast.title}
          </p>
          {toast.description ? (
            <p className="mt-1 line-clamp-2 font-streamly-body text-xs font-bold leading-5 text-streamly-purpleBlue">
              {toast.description}
            </p>
          ) : null}
        </div>
        <button
          aria-label="Dismiss notification"
          className="grid h-8 w-8 shrink-0 place-items-center rounded-streamly-pill bg-white text-streamly-purpleBlue shadow-[inset_0_0_0_1px_rgba(217,200,255,0.72)] transition hover:bg-streamly-wash hover:text-streamly-violet"
          onClick={() => dismissToast(toast.id)}
          type="button"
        >
          <X aria-hidden className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

type ToastVisual = {
  Icon: LucideIcon;
  accent: string;
  card: string;
  icon: string;
  iconShell: string;
};

function toastVisual(kind: ToastKind): ToastVisual {
  if (kind === "success") {
    return {
      Icon: CheckCircle2,
      accent: "bg-gradient-to-r from-emerald-400 via-emerald-300 to-streamly-lavenderStrong",
      card: "border-emerald-200/90",
      icon: "text-emerald-700",
      iconShell: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200"
    };
  }
  if (kind === "failure") {
    return {
      Icon: AlertTriangle,
      accent: "bg-gradient-to-r from-red-500 via-red-300 to-amber-200",
      card: "border-red-200/90",
      icon: "text-red-700",
      iconShell: "bg-red-50 text-red-700 ring-1 ring-red-200"
    };
  }
  return {
    Icon: Loader2,
    accent: "bg-gradient-to-r from-streamly-electric via-streamly-pastel to-streamly-lavenderStrong",
    card: "border-streamly-lavenderStrong",
    icon: "text-streamly-electric",
    iconShell: "bg-streamly-wash text-streamly-electric ring-1 ring-streamly-lavenderStrong"
  };
}
