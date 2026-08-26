import { useEffect, useRef } from 'react';
import { AlertTriangle, Info, Loader2, X } from 'lucide-react';

interface ConfirmDialogProps {
  title: string;
  message: string;
  confirmLabel?: string;
  tone?: 'danger' | 'info';
  pending?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

export function ConfirmDialog({
  title,
  message,
  confirmLabel = 'Confirm',
  tone = 'danger',
  pending = false,
  onConfirm,
  onClose,
}: ConfirmDialogProps) {
  const isDanger = tone === 'danger';
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape' && !pending) {
        e.stopPropagation();
        onClose();
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose, pending]);

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4 backdrop-blur-sm"
      onMouseDown={(e) => {
        if (e.target === overlayRef.current && !pending) onClose();
      }}
    >
      <div className="animate-confirmIn max-h-[90vh] w-full max-w-md overflow-y-auto rounded-xl border border-border bg-surface shadow-overlay">
        <div
          className={`h-1 w-full ${isDanger ? 'bg-danger' : 'bg-info'}`}
          aria-hidden="true"
        />
        <div className="p-6">
          <div className="flex items-start gap-4">
            <div
              className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${
                isDanger ? 'bg-dangerSoft text-danger' : 'bg-infoSoft text-info'
              }`}
            >
              {isDanger ? (
                <AlertTriangle className="h-5 w-5" />
              ) : (
                <Info className="h-5 w-5" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="text-base font-semibold tracking-tight text-ink">{title}</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">{message}</p>
            </div>
            <button
              onClick={onClose}
              disabled={pending}
              aria-label="Close"
              className="mt-0.5 shrink-0 rounded-md p-1 text-muted transition hover:bg-surfaceWarm hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="mt-6 flex justify-end gap-2.5">
            <button
              onClick={onClose}
              disabled={pending}
              className="inline-flex h-10 items-center justify-center rounded-lg border border-border bg-surface px-4 text-sm font-medium text-ink transition hover:bg-surfaceWarm focus:outline-none focus-visible:ring-2 focus-visible:ring-navy/40 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              disabled={pending}
              className={`inline-flex h-10 items-center justify-center gap-2 rounded-lg px-5 text-sm font-medium text-white transition focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${
                isDanger
                  ? 'bg-danger hover:bg-danger/90 focus-visible:ring-danger/40'
                  : 'bg-orange hover:bg-orangeDark focus-visible:ring-orange/40'
              }`}
            >
              {pending && <Loader2 className="h-4 w-4 animate-spin" />}
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
