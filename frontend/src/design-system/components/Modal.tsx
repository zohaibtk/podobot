import type { PropsWithChildren } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

import { useBodyScrollLock } from "@/design-system/hooks/useBodyScrollLock";

type ModalProps = PropsWithChildren<{
  title: string;
  description?: string;
  isOpen: boolean;
  onClose: () => void;
}>;

export function Modal({ title, description, isOpen, onClose, children }: ModalProps) {
  useBodyScrollLock(isOpen);

  if (!isOpen) {
    return null;
  }

  const modal = (
    <div
      aria-modal="true"
      className="fixed inset-0 z-[1000] grid place-items-center overflow-hidden bg-streamly-coal/35 px-4 py-4 backdrop-blur-sm"
      role="dialog"
    >
      <div className="relative z-10 flex max-h-[calc(100vh-2rem)] w-full max-w-2xl flex-col overflow-hidden rounded-streamly-panel border border-streamly-lavenderStrong/80 bg-white shadow-streamly-elevated">
        <div className="shrink-0 border-b border-streamly-lavenderStrong/70 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="font-streamly-platform text-2xl font-extrabold leading-tight text-streamly-coal">
                {title}
              </h2>
              {description ? (
                <p className="mt-1 font-streamly-body text-sm leading-6 text-[var(--streamly-text-muted)]">
                  {description}
                </p>
              ) : null}
            </div>
            <button
              aria-label="Close modal"
              className="grid h-10 w-10 shrink-0 place-items-center rounded-streamly-pill bg-streamly-wash text-streamly-purpleBlue transition hover:-translate-y-0.5 hover:bg-streamly-lavender"
              onClick={onClose}
              type="button"
            >
              <X aria-hidden className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-6 py-5">
          {children}
        </div>
      </div>
    </div>
  );

  if (typeof document === "undefined") {
    return modal;
  }

  return createPortal(modal, document.body);
}
