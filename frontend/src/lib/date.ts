const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** Formats an ISO date (date-only or datetime) as "14 Aug 2026". Returns '—' for empty/invalid input. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(`${iso.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(d.getTime())) return '—';
  return `${d.getDate()} ${MONTHS_SHORT[d.getMonth()]} ${d.getFullYear()}`;
}

/** Formats a leave date range: single day, "14–16 Aug 2026", or "14 Aug – 16 Sep 2026". */
export function formatDateRange(from: string, to: string): string {
  const f = new Date(`${from.slice(0, 10)}T00:00:00`);
  const e = new Date(`${to.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(f.getTime()) || Number.isNaN(e.getTime())) return formatDate(from);
  if (from === to) return formatDate(from);
  if (f.getFullYear() === e.getFullYear()) {
    if (f.getMonth() === e.getMonth()) {
      return `${f.getDate()}–${e.getDate()} ${MONTHS_SHORT[f.getMonth()]} ${f.getFullYear()}`;
    }
    return `${f.getDate()} ${MONTHS_SHORT[f.getMonth()]} – ${e.getDate()} ${MONTHS_SHORT[e.getMonth()]} ${f.getFullYear()}`;
  }
  return `${formatDate(from)} – ${formatDate(to)}`;
}

/** Formats a backend day count as "1 day", "2 days", or "0.5 day". */
export function formatDayCount(totalDays: string | number | null | undefined): string {
  if (totalDays === null || totalDays === undefined || totalDays === '') return '—';
  const n = Number(totalDays);
  if (!Number.isFinite(n)) return '—';
  const text = String(Math.round(n * 100) / 100);
  return `${text} ${n === 1 ? 'day' : 'days'}`;
}

export interface CalendarCell {
  date: Date;
  inMonth: boolean;
}

/** Builds a 6-row calendar grid (42 cells) for the given year/month. */
export function buildMonthGrid(year: number, month: number): CalendarCell[] {
  const first = new Date(year, month, 1);
  const startOffset = first.getDay();
  const start = new Date(year, month, 1 - startOffset);
  return Array.from({ length: 42 }, (_, i) => {
    const date = new Date(start);
    date.setDate(start.getDate() + i);
    return { date, inMonth: date.getMonth() === month };
  });
}

export function toISODate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return `${d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })} · ${d.toLocaleTimeString(
    'en-IN',
    { hour: '2-digit', minute: '2-digit' },
  )}`;
}

export function formatTime(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

export function weekStartFor(date: Date): string {
  const d = new Date(date);
  const day = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - day);
  return toISODate(d);
}

export function addDays(date: Date, days: number): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

export function monthLabel(year: number, month: number): string {
  return new Date(year, month, 1).toLocaleDateString('en-IN', {
    month: 'long',
    year: 'numeric',
  });
}

/** Formats a minute count as a human-readable duration: 8h 42m / 45m / 0m. */
export function formatMinutesDuration(totalMinutes: number): string {
  if (!Number.isFinite(totalMinutes) || totalMinutes <= 0) return '0m';
  if (totalMinutes < 60) return `${Math.round(totalMinutes)}m`;
  const rounded = Math.round(totalMinutes);
  return `${Math.floor(rounded / 60)}h ${rounded % 60}m`;
}

/** Formats decimal hours from the backend as a duration. Returns '' for null/undefined. */
export function formatDuration(hours: string | number | null | undefined): string {
  if (hours === null || hours === undefined || hours === '') return '';
  const h = Number(hours);
  if (!Number.isFinite(h)) return '';
  return formatMinutesDuration(Math.round(h * 60));
}

export { WEEKDAYS };
