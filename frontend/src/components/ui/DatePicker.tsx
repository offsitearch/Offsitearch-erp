import { useEffect, useMemo, useRef, useState } from 'react';
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-react';
import { buildMonthGrid, monthLabel, toISODate } from '../../lib/date';

const WEEKDAY_HEADERS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

function dayLabel(d: Date): string {
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

/**
 * In-house date picker styled to the app's design system.
 * Contract mirrors <input type="date">: value is "YYYY-MM-DD" ("" = empty).
 */
export default function DatePicker({
  value,
  onChange,
  min,
  max,
  placeholder = 'Select date',
  disabled = false,
  compact = false,
  className = '',
}: {
  value: string;
  onChange: (isoDate: string) => void;
  min?: string;
  max?: string;
  placeholder?: string;
  disabled?: boolean;
  compact?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const selected = value ? new Date(`${value}T00:00:00`) : null;
  const today = new Date();

  const [viewYear, setViewYear] = useState(() => (selected ?? today).getFullYear());
  const [viewMonth, setViewMonth] = useState(() => (selected ?? today).getMonth());

  useEffect(() => {
    if (!open) return;
    const base = selected ?? new Date();
    setViewYear(base.getFullYear());
    setViewMonth(base.getMonth());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const cells = useMemo(() => buildMonthGrid(viewYear, viewMonth), [viewYear, viewMonth]);
  const todayIso = toISODate(today);

  const isDisabledDay = (iso: string): boolean => Boolean((min && iso < min) || (max && iso > max));

  const shiftMonth = (delta: number) => {
    const next = new Date(viewYear, viewMonth + delta, 1);
    setViewYear(next.getFullYear());
    setViewMonth(next.getMonth());
  };

  const pick = (d: Date) => {
    onChange(toISODate(d));
    setOpen(false);
  };

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="dialog"
        aria-expanded={open}
        className={`flex w-full items-center justify-between gap-2 rounded-md border px-3 text-left transition disabled:cursor-not-allowed disabled:opacity-60 ${
          compact ? 'h-8 text-xs' : 'h-10 text-sm'
        } ${open ? 'border-navy ring-2 ring-navy/30' : 'border-border'} bg-surface text-ink focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30`}
      >
        <span className={selected ? '' : 'text-muted'}>{selected ? dayLabel(selected) : placeholder}</span>
        <CalendarDays className="h-4 w-4 shrink-0 text-muted" />
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Choose date"
          className="absolute left-0 top-[calc(100%+6px)] z-30 w-72 rounded-lg border border-border bg-surface p-3 shadow-overlay"
        >
          <div className="mb-2 flex items-center justify-between">
            <button
              type="button"
              onClick={() => shiftMonth(-1)}
              aria-label="Previous month"
              className="rounded-md p-1.5 text-graphite transition hover:bg-surfaceWarm hover:text-ink"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-sm font-semibold text-ink">{monthLabel(viewYear, viewMonth)}</span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => {
                  setViewYear(today.getFullYear());
                  setViewMonth(today.getMonth());
                }}
                className="rounded-md px-2 py-1 text-xs font-medium text-orange transition hover:bg-orange/10"
              >
                Today
              </button>
              <button
                type="button"
                onClick={() => shiftMonth(1)}
                aria-label="Next month"
                className="rounded-md p-1.5 text-graphite transition hover:bg-surfaceWarm hover:text-ink"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-7 gap-1">
            {WEEKDAY_HEADERS.map((w) => (
              <span key={w} className="py-1 text-center text-[10px] font-semibold uppercase tracking-wide text-muted">
                {w}
              </span>
            ))}
            {cells.map(({ date, inMonth }) => {
              const iso = toISODate(date);
              const isSelected = iso === value;
              const isToday = iso === todayIso;
              const out = isDisabledDay(iso);
              return (
                <button
                  key={iso}
                  type="button"
                  disabled={out}
                  onClick={() => pick(date)}
                  className={`h-8 rounded-md text-sm tabular-nums transition ${
                    isSelected
                      ? 'bg-orange font-semibold text-white'
                      : inMonth
                        ? 'text-ink hover:bg-surfaceWarm'
                        : 'text-muted/60 hover:bg-surfaceWarm'
                  } ${isToday && !isSelected ? 'ring-1 ring-inset ring-navy/40' : ''}${
                    out ? ' cursor-not-allowed opacity-30 hover:bg-transparent' : ''
                  }`}
                >
                  {date.getDate()}
                </button>
              );
            })}
          </div>

          <div className="mt-2 flex justify-end border-t border-border pt-2">
            <button
              type="button"
              onClick={() => {
                onChange('');
                setOpen(false);
              }}
              className="rounded-md px-2 py-1 text-xs font-medium text-muted transition hover:bg-surfaceWarm hover:text-ink"
            >
              Clear
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
