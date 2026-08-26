import { CalendarRange } from 'lucide-react';
import type { PhaseStatus } from '../../../lib/types';
import { Skeleton } from '../../../components/ui/Skeleton';
import { EmptyState } from '../../../components/ui/EmptyState';

const PHASE_BAR_COLOR: Record<PhaseStatus, string> = {
  not_started: 'bg-graphite/30',
  in_progress: 'bg-info',
  completed: 'bg-success',
  delayed: 'bg-danger',
};

export default function TimelineView({
  start,
  end,
  timeline,
  loading,
}: {
  start: string | null;
  end: string | null;
  timeline: { start_date: string | null; end_date: string | null; rows: { id: number; name: string; order_index: number; status: PhaseStatus; start_date: string | null; end_date: string | null; completion_pct: string }[] } | undefined;
  loading: boolean;
}) {
  const rows = timeline?.rows ?? [];
  const rangeStart = timeline?.start_date ?? start;
  const rangeEnd = timeline?.end_date ?? end;

  if (loading) {
    return <Skeleton className="h-40 w-full" />;
  }
  if (!rangeStart || !rangeEnd) {
    return <EmptyState icon={CalendarRange} title="Set project start and end dates to see the timeline." />;
  }

  const s = new Date(rangeStart);
  const e = new Date(rangeEnd);
  const totalDays = Math.max(1, (e.getTime() - s.getTime()) / 86400000);
  const months: string[] = [];
  const cursor = new Date(s.getFullYear(), s.getMonth(), 1);
  while (cursor <= e) {
    months.push(cursor.toLocaleDateString('en-IN', { month: 'short', year: '2-digit' }));
    cursor.setMonth(cursor.getMonth() + 1);
  }

  const left = (d: string | null) => {
    if (!d) return 0;
    const diff = (new Date(d).getTime() - s.getTime()) / 86400000;
    return Math.max(0, Math.min(100, (diff / totalDays) * 100));
  };
  const width = (a: string | null, b: string | null) => {
    const startPct = left(a);
    const endPct = b ? left(b) : 100;
    return Math.max(2, endPct - startPct);
  };

  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-surface shadow-card">
      <div className="min-w-[640px] p-4">
        <div className="mb-2 grid grid-cols-1" style={{ gridTemplateColumns: `220px 1fr` }}>
          <div />
          <div className="flex">
            {months.map((m, i) => (
              <div key={i} className="flex-1 border-l border-border px-2 text-xs text-muted">
                {m}
              </div>
            ))}
          </div>
        </div>
        {rows.map((r) => {
          return (
            <div key={r.id} className="grid grid-cols-[220px_1fr] items-center gap-0 border-t border-border py-1.5">
              <div className="pr-3">
                <p className="truncate text-sm font-medium text-ink">{r.name}</p>
              </div>
              <div className="relative h-7">
                <div className="absolute inset-y-2 left-0 right-0 rounded bg-graphite/5" />
                <div
                  className={`absolute inset-y-2 rounded ${PHASE_BAR_COLOR[r.status]}`}
                  style={{ left: `${left(r.start_date)}%`, width: `${width(r.start_date, r.end_date)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
