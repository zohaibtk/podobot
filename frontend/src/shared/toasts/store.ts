export type ToastKind = "failure" | "processing" | "success";

export type Toast = {
  createdAt: number;
  description?: string;
  id: string;
  kind: ToastKind;
  title: string;
};

type ToastInput = {
  description?: string;
  durationMs?: number | null;
  kind: ToastKind;
  title: string;
};

type ToastListener = () => void;

const DEFAULT_DURATION_MS = 4200;
const MAX_TOASTS = 4;

let toasts: Toast[] = [];
let toastId = 0;
const listeners = new Set<ToastListener>();
const timers = new Map<string, number>();

export function getToasts() {
  return toasts;
}

export function subscribeToasts(listener: ToastListener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function showToast(input: ToastInput) {
  const id = `toast-${Date.now()}-${toastId++}`;
  const toast: Toast = {
    createdAt: Date.now(),
    id,
    kind: input.kind,
    title: input.title,
    ...(input.description ? { description: input.description } : {})
  };

  toasts = [toast, ...toasts].slice(0, MAX_TOASTS);
  scheduleDismiss(id, input.durationMs);
  emit();
  return id;
}

export function updateToast(id: string, input: ToastInput) {
  const existing = toasts.find((toast) => toast.id === id);
  if (!existing) {
    return showToast(input);
  }

  toasts = toasts.map((toast) =>
    toast.id === id
      ? {
          ...toast,
          kind: input.kind,
          title: input.title,
          description: input.description
        }
      : toast
  );
  scheduleDismiss(id, input.durationMs);
  emit();
  return id;
}

export function dismissToast(id: string) {
  clearDismissTimer(id);
  toasts = toasts.filter((toast) => toast.id !== id);
  emit();
}

export function clearToasts() {
  timers.forEach((timer) => window.clearTimeout(timer));
  timers.clear();
  toasts = [];
  emit();
}

function scheduleDismiss(id: string, durationMs: number | null | undefined) {
  clearDismissTimer(id);
  if (durationMs === null) {
    return;
  }
  const timeout = window.setTimeout(() => dismissToast(id), durationMs ?? DEFAULT_DURATION_MS);
  timers.set(id, timeout);
}

function clearDismissTimer(id: string) {
  const timer = timers.get(id);
  if (timer) {
    window.clearTimeout(timer);
    timers.delete(id);
  }
}

function emit() {
  listeners.forEach((listener) => listener());
}
