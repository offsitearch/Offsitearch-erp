import { createContext, useCallback, useContext, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { CheckCircle2, Info, X, XCircle } from 'lucide-react';

type ToastTone = 'success' | 'error' | 'info';

interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
  leaving: boolean;
}

interface ToastContextValue {
  toast: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const TONE_CONFIG: Record<
  ToastTone,
  {
    wrap: string;
    iconBg: string;
    icon: ReactNode;
    accent: string;
  }
> = {
  success: {
    wrap: 'border-success/30 bg-surface text-ink',
    iconBg: 'bg-successSoft text-success',
    icon: <CheckCircle2 className="h-[18px] w-[18px]" />,
    accent: 'bg-success',
  },
  error: {
    wrap: 'border-danger/30 bg-surface text-ink',
    iconBg: 'bg-dangerSoft text-danger',
    icon: <XCircle className="h-[18px] w-[18px]" />,
    accent: 'bg-danger',
  },
  info: {
    wrap: 'border-info/30 bg-surface text-ink',
    iconBg: 'bg-infoSoft text-info',
    icon: <Info className="h-[18px] w-[18px]" />,
    accent: 'bg-info',
  },
};

const TOAST_DURATION = 5000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);
  const timers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  const dismiss = useCallback((id: number) => {
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
    setItems((prev) => prev.map((t) => (t.id === id ? { ...t, leaving: true } : t)));
    setTimeout(() => {
      setItems((prev) => prev.filter((t) => t.id !== id));
    }, 200);
  }, []);

  const toast = useCallback(
    (message: string, tone: ToastTone = 'info') => {
      const id = nextId.current++;
      setItems((prev) => [...prev.slice(-4), { id, message, tone, leaving: false }]);
      const timer = setTimeout(() => dismiss(id), TOAST_DURATION);
      timers.current.set(id, timer);
    },
    [dismiss],
  );

  const pauseTimer = useCallback((id: number) => {
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
  }, []);

  const resumeTimer = useCallback(
    (id: number) => {
      const timer = setTimeout(() => dismiss(id), 3000);
      timers.current.set(id, timer);
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="pointer-events-none fixed bottom-20 right-5 z-[60] flex w-[360px] max-w-[calc(100vw-2.5rem)] flex-col gap-2.5 sm:bottom-5">
        {items.map((t) => {
          const config = TONE_CONFIG[t.tone];
          return (
            <div
              key={t.id}
              onMouseEnter={() => {
                if (!t.leaving) pauseTimer(t.id);
              }}
              onMouseLeave={() => {
                if (!t.leaving) resumeTimer(t.id);
              }}
              className={`pointer-events-auto relative overflow-hidden rounded-lg border bg-surface shadow-card ${config.wrap} ${
                t.leaving ? 'toast-exit' : 'toast-enter'
              }`}
            >
              <div className="flex items-start gap-3 px-4 py-3">
                <span
                  className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${config.iconBg}`}
                >
                  {config.icon}
                </span>
                <span className="min-w-0 flex-1 pt-0.5 text-sm leading-snug text-ink">{t.message}</span>
                <button
                  onClick={() => dismiss(t.id)}
                  className="mt-0.5 shrink-0 rounded-md p-0.5 text-muted transition hover:bg-surfaceWarm hover:text-ink"
                  aria-label="Dismiss"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
              <div className="h-[3px] w-full bg-border/50">
                <div
                  className={`h-full rounded-full ${config.accent} ${
                    t.leaving ? '' : 'toast-progress'
                  }`}
                  style={{ width: t.leaving ? '0%' : undefined }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
