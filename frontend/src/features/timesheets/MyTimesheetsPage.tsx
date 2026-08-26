import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  CalendarClock,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Copy,
  Download,
  Eye,
  FileSpreadsheet,
  Plus,
  RefreshCw,
  Send,
  Trash2,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { getProjectOptions } from '../../api/projects';
import {
  downloadTimesheetMonthExport,
  downloadTimesheetPdf,
  getMyTimesheets,
  getMyWeek,
  saveMyWeek,
  submitTimesheet,
} from '../../api/timesheets';
import { EmptyState } from '../../components/ui/EmptyState';
import { Skeleton } from '../../components/ui/Skeleton';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { buildMonthGrid, formatDate, formatDateRange, formatDuration, monthLabel, toISODate, WEEKDAYS } from '../../lib/date';
import { STANDARD_WORKDAY_HOURS } from '../../lib/constants';
import { primaryBtnClass, secondaryBtnClass } from '../../lib/styles';
import { useAuthStore } from '../../store/authStore';
import type { TimesheetDayStatus, TimesheetStatus, TimesheetWeekSaveInput } from '../../lib/types';
import { TimesheetStatusBadge } from './components/TimesheetStatusBadge';
import { TimesheetDetailModal } from './components/TimesheetDetailModal';
import { TimesheetTabs } from './components/TimesheetTabs';

interface EntryRow {
  key: string;
  date: string;
  project_id: number | null;
  hours: string;
  location: string;
  description: string;
}

/** A day can be edited while it is still a draft or has been rejected. */
const EDITABLE_DAY_STATUSES: ReadonlySet<TimesheetDayStatus> = new Set(['draft', 'rejected']);

function num(raw: string): number {
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? Math.round(n * 100) / 100 : 0;
}

/** Monday of the ISO week containing ``iso``. */
function mondayOf(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  return toISODate(d);
}

function newRowKey(): string {
  return `row-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

function newRow(dateIso: string): EntryRow {
  return {
    key: newRowKey(),
    date: dateIso,
    project_id: null,
    hours: '',
    location: '',
    description: '',
  };
}

/** One visual row per stored entry — no merging; multiple entries per day are expected. */
function rowsFromDetail(detail: {
  entries: Array<{
    id: number;
    project_id: number | null;
    date: string;
    hours: string | number;
    location: string | null;
    description: string | null;
  }>;
}): EntryRow[] {
  return detail.entries.map((entry) => ({
    key: `entry-${entry.id}`,
    date: entry.date.slice(0, 10),
    project_id: entry.project_id,
    hours: String(num(String(entry.hours))) || String(entry.hours),
    location: entry.location ?? '',
    description: entry.description ?? '',
  }));
}

function buildEntries(rows: EntryRow[]): TimesheetWeekSaveInput['entries'] {
  return rows.flatMap((row) => {
    const hours = num(row.hours);
    if (!hours) return [];
    return [
      {
        project_id: row.project_id,
        task_id: null,
        date: row.date,
        hours,
        location: row.location.trim() || null,
        description: row.description.trim() || null,
      },
    ];
  });
}

/** Display-only marker for days logged above the standard workday. */
function OvertimeChip({ hours }: { hours: number }) {
  if (hours <= STANDARD_WORKDAY_HOURS) return null;
  return (
    <span
      title={`Over the standard ${STANDARD_WORKDAY_HOURS}h workday`}
      className="ml-1.5 inline-flex items-center rounded-full bg-warningSoft px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-warning"
    >
      OT
    </span>
  );
}

export default function MyTimesheetsPage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">Timesheets</h1>
          <p className="mt-1 text-sm text-muted">
            Log your hours per project — past draft days in the current week can still be edited.
          </p>
        </div>
        <TimesheetTabs level={user?.org_level_code} />
      </header>
      <DaySheet />
      <History />
    </div>
  );
}

function MiniCalendar({
  selected,
  today,
  onSelect,
  onClose,
}: {
  selected: string;
  today: string;
  onSelect: (iso: string) => void;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const init = new Date(`${selected}T00:00:00`);
  const [month, setMonth] = useState(init.getMonth());
  const [year, setYear] = useState(init.getFullYear());

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener('mousedown', handleClick, { once: true });
    return () => document.removeEventListener('mousedown', handleClick);
  }, [onClose]);

  const cells = buildMonthGrid(year, month);

  return (
    <div
      ref={ref}
      className="absolute left-0 top-full z-50 mt-2 w-64 rounded-xl border border-border bg-surface shadow-lg"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-center justify-between px-3 py-2">
        <button
          onClick={() => {
            if (month === 0) { setMonth(11); setYear((y) => y - 1); }
            else setMonth((m) => m - 1);
          }}
          className="rounded p-0.5 text-muted hover:text-ink"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-sm font-semibold text-ink">{monthLabel(year, month)}</span>
        <button
          onClick={() => {
            if (month === 11) { setMonth(0); setYear((y) => y + 1); }
            else setMonth((m) => m + 1);
          }}
          className="rounded p-0.5 text-muted hover:text-ink"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
      <div className="grid grid-cols-7 gap-px px-2 pb-2">
        {WEEKDAYS.map((d) => (
          <div key={d} className="py-1 text-center text-[10px] font-semibold uppercase text-muted">
            {d}
          </div>
        ))}
        {cells.map((cell, i) => {
          const iso = toISODate(cell.date);
          const isSelected = iso === selected;
          const isTodayCell = iso === today;
          return (
            <button
              key={i}
              onClick={() => onSelect(iso)}
              className={`h-8 w-full rounded text-xs font-medium transition
                ${!cell.inMonth ? 'text-muted/40' : 'text-ink hover:bg-surfaceWarm'}
                ${isSelected ? 'bg-orange text-white hover:bg-orangeDark' : ''}
                ${isTodayCell && !isSelected ? 'ring-1 ring-orange/50' : ''}
              `}
            >
              {cell.date.getDate()}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function DaySheet() {
  const queryClient = useQueryClient();
  const todayIso = toISODate(new Date());
  const [dayOffset, setDayOffset] = useState(0);
  const [showCalendar, setShowCalendar] = useState(false);

  const selectedDate = useMemo(() => {
    const d = new Date(`${todayIso}T00:00:00`);
    d.setDate(d.getDate() + dayOffset);
    return toISODate(d);
  }, [todayIso, dayOffset]);

  const isToday = dayOffset === 0;
  const isFuture = dayOffset > 0;

  const selectedDayLabel = useMemo(() => {
    const d = new Date(`${selectedDate}T00:00:00`);
    const weekday = d.toLocaleDateString('en-IN', { weekday: 'long' });
    return `${weekday}, ${formatDate(selectedDate)}`;
  }, [selectedDate]);

  const [rows, setRows] = useState<EntryRow[]>([]);
  const [dirty, setDirty] = useState(false);
  const [confirmSubmit, setConfirmSubmit] = useState(false);

  const dayQuery = useQuery({
    queryKey: ['timesheets', 'day', selectedDate],
    queryFn: () => getMyWeek(selectedDate),
  });

  useEffect(() => {
    if (dayQuery.data) {
      setRows(rowsFromDetail(dayQuery.data));
      setDirty(false);
    }
  }, [dayQuery.data]);

  const projectsQuery = useQuery({
    queryKey: ['projects', 'timesheet-options'],
    queryFn: () => getProjectOptions(),
    staleTime: 60_000,
  });
  const projects = useMemo(
    () => projectsQuery.data ?? [],
    [projectsQuery.data],
  );

  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['timesheets'] }),
      queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
    ]);

  const saveMutation = useMutation({
    mutationFn: () =>
      saveMyWeek({ week_start: mondayOf(selectedDate), entries: buildEntries(rows) }),
    onSuccess: async () => {
      await invalidate();
      setDirty(false);
    },
  });

  const submitMutation = useMutation({
    mutationFn: (id: number) => submitTimesheet(id),
    onSuccess: async () => {
      await invalidate();
      setDirty(false);
    },
  });

  const pdfMutation = useMutation({
    mutationFn: (id: number) => downloadTimesheetPdf(id),
  });

  const detail = dayQuery.data;

  // Editability: any draft or rejected day in the week can be edited.
  const selectedDay = detail?.days?.find((d) => d.date.slice(0, 10) === selectedDate);
  const selectedDayStatus: TimesheetDayStatus = selectedDay?.status ?? 'draft';
  const hasEditableDay = detail?.days && detail.days.length > 0
    ? detail.days.some((d) => EDITABLE_DAY_STATUSES.has(d.status))
    : true; // No day rows yet — week is fresh, editable
  const dayEditable = hasEditableDay && !submitMutation.isPending;

  // Rows for the selected day only.
  const dayRows = useMemo(
    () => rows.filter((r) => r.date === selectedDate),
    [rows, selectedDate],
  );

  // Rows the owner may edit: draft/rejected day entries.
  const editorRows = useMemo(() => {
    if (!detail) return [];
    return dayRows.filter((r) => {
      const day = detail.days?.find((d) => d.date.slice(0, 10) === r.date);
      return !day || EDITABLE_DAY_STATUSES.has(day.status);
    });
  }, [dayRows, detail]);

  const dayTotal = useMemo(
    () => editorRows.reduce((sum, r) => sum + num(r.hours), 0),
    [editorRows],
  );

  const missingProject = editorRows.some((r) => num(r.hours) > 0 && r.project_id == null);

  function patch(key: string, changes: Partial<EntryRow>) {
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...changes } : r)));
    setDirty(true);
  }

  function discardChanges() {
    if (dayQuery.data) {
      setRows(rowsFromDetail(dayQuery.data));
      setDirty(false);
    }
  }

  /** Copies yesterday's rows into the selected date (fetching last week's sheet if needed). */
  async function copyYesterday() {
    const prev = new Date(`${selectedDate}T00:00:00`);
    prev.setDate(prev.getDate() - 1);
    const prevIso = toISODate(prev);
    let sourceRows: EntryRow[];
    if (
      detail &&
      prevIso >= detail.week_start.slice(0, 10) &&
      prevIso <= detail.week_end.slice(0, 10)
    ) {
      sourceRows = rows;
    } else {
      try {
        sourceRows = rowsFromDetail(await getMyWeek(prevIso));
      } catch {
        return;
      }
    }
    const copies = sourceRows
      .filter((r) => r.date === prevIso && num(r.hours) > 0)
      .map((r) => ({ ...r, key: newRowKey(), date: selectedDate }));
    if (copies.length === 0) return;
    setRows((prevRows) => [...prevRows.filter((r) => r.date !== selectedDate), ...copies]);
    setDirty(true);
  }

  async function handleSubmit() {
    if (!detail) return;
    setConfirmSubmit(true);
  }

  async function doSubmit() {
    if (!detail) return;
    setConfirmSubmit(false);
    if (dirty) {
      try {
        await saveMutation.mutateAsync();
      } catch {
        return; // Save errors surface below; never submit a failed save.
      }
    }
    submitMutation.mutate(detail.id);
  }

  const actionError =
    (saveMutation.error as Error | null)?.message ??
    (submitMutation.error as Error | null)?.message;

  return (
    <section className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
      {/* ── Daily header ── */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setDayOffset((d) => d - 1)}
            title="Previous day"
            className="rounded p-0.5 text-muted transition hover:bg-surfaceWarm hover:text-ink"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <div className="relative flex flex-col items-center">
            <button
              onClick={() => setShowCalendar((v) => !v)}
              className="flex items-center gap-1.5 rounded-md px-2 py-1 text-sm font-semibold text-ink transition hover:bg-surfaceWarm"
              title="Open calendar"
            >
              <CalendarClock className="h-4 w-4 text-muted" />
              {selectedDayLabel}
            </button>
            {!isToday && (
              <button
                onClick={() => setDayOffset(0)}
                className="text-[10px] font-medium text-orange transition hover:text-orangeDark"
              >
                ← Back to today
              </button>
            )}
            {showCalendar && (
              <MiniCalendar
                selected={selectedDate}
                today={todayIso}
                onSelect={(date) => {
                  const diff = Math.round(
                    (new Date(`${date}T00:00:00`).getTime() - new Date(`${todayIso}T00:00:00`).getTime()) / 86400000,
                  );
                  setDayOffset(diff);
                  setShowCalendar(false);
                }}
                onClose={() => setShowCalendar(false)}
              />
            )}
          </div>
          <button
            onClick={() => setDayOffset((d) => d + 1)}
            title="Next day"
            disabled={isFuture}
            className="rounded p-0.5 text-muted transition hover:bg-surfaceWarm hover:text-ink disabled:cursor-not-allowed disabled:opacity-30"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
        <div className="flex items-center gap-3">
          {detail && (
            <TimesheetStatusBadge
              status={
                selectedDayStatus === 'draft'
                  ? detail.status
                  : (selectedDayStatus as TimesheetStatus)
              }
            />
          )}
          {detail && (
            <button
              onClick={() => pdfMutation.mutate(detail.id)}
              disabled={pdfMutation.isPending}
              title="Download PDF receipt"
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-surface px-2.5 text-xs font-medium text-muted transition hover:bg-surfaceWarm hover:text-ink disabled:opacity-60"
            >
              <Download className="h-3.5 w-3.5" />
              PDF
            </button>
          )}
          <span className="text-sm font-semibold tabular-nums text-ink" title="Hours logged for this day">
            {formatDuration(dayTotal)}
            <OvertimeChip hours={dayTotal} />
          </span>
        </div>
      </div>

      {/* ── Status banners (driven by today's day row) ── */}
      {selectedDayStatus === 'rejected' && (
        <div className="flex items-start gap-2 border-b border-danger/25 bg-dangerSoft px-5 py-3 text-sm text-danger">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            Rejected by {detail?.approved_by_name ?? 'a reviewer'}
            {detail?.rejection_reason ? `: ${detail.rejection_reason}` : '.'} Correct today's
            entries and resubmit.
          </span>
        </div>
      )}
      {selectedDayStatus === 'submitted' && (
        <div className="flex items-start gap-2 border-b border-warning/25 bg-warningSoft px-5 py-3 text-sm text-warning">
          <Clock className="mt-0.5 h-4 w-4 shrink-0" />
          <span>Submitted — waiting for a lead to review.</span>
        </div>
      )}
      {selectedDayStatus === 'approved' && (
        <div className="flex items-start gap-2 border-b border-success/25 bg-successSoft px-5 py-3 text-sm text-success">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            Approved{detail?.approved_by_name ? ` by ${detail.approved_by_name}` : ''}.
          </span>
        </div>
      )}

      {dayQuery.isPending ? (
        <div className="space-y-3 px-5 py-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : dayQuery.isError ? (
        <div className="flex flex-col items-center gap-3 px-4 py-12 text-center">
          <AlertCircle className="h-6 w-6 text-danger" />
          <p className="text-sm font-medium text-ink">Couldn't load timesheet.</p>
          <button onClick={() => dayQuery.refetch()} className={secondaryBtnClass}>
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </button>
        </div>
      ) : (
        <>
          {/* ── Entries for selected day ── */}
          <div className="border-b border-border">
            <div className="px-5 pb-1 pt-4">
              <p className="text-xs text-muted">
                {dayEditable
                  ? 'Log hours for this day. You can edit draft or rejected days. Future dates are not allowed.'
                  : 'Read-only.'}
              </p>
            </div>

            {editorRows.length === 0 ? (
              <div className="px-5 py-6">
                <EmptyState
                  icon={CalendarClock}
                  title="No hours logged yet"
                  text={
                    dayEditable
                      ? 'Add a row below to start logging your work.'
                      : 'Nothing was logged.'
                  }
                />
              </div>
            ) : (
              <div className="overflow-x-auto px-2 pb-2">
                <table className="w-full min-w-[800px] text-left text-sm">
                  <thead className="text-[11px] font-semibold uppercase tracking-wider text-muted">
                    <tr>
                      <th className="w-28 px-3 py-2">Date</th>
                      <th className="w-20 px-3 py-2">Hrs</th>
                      <th className="px-3 py-2">Project</th>
                      <th className="px-3 py-2">Location</th>
                      <th className="px-3 py-2">Description</th>
                      {dayEditable && <th className="w-10 px-2" aria-hidden="true" />}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {editorRows.map((row) => (
                      <EntryEditorRow
                        key={row.key}
                        row={row}
                        editable={dayEditable}
                        projects={projects}
                        onChange={(changes) => patch(row.key, changes)}
                        onRemove={() => {
                          setRows((prev) => prev.filter((r) => r.key !== row.key));
                          setDirty(true);
                        }}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {dayEditable && (
              <div className="flex flex-wrap items-center gap-2 px-5 pb-4">
                <button
                  onClick={() => {
                    setRows((prev) => [...prev, newRow(selectedDate)]);
                    setDirty(true);
                  }}
                  className="inline-flex h-9 items-center justify-center gap-1.5 rounded-md border border-dashed border-border px-3 text-sm font-medium text-muted transition hover:border-orange/40 hover:text-orange"
                >
                  <Plus className="h-4 w-4" />
                  Add entry
                </button>
                <button
                  onClick={() => void copyYesterday()}
                  title="Copy yesterday's rows into today"
                  className="inline-flex h-9 items-center justify-center gap-1.5 rounded-md border border-dashed border-border px-3 text-sm font-medium text-muted transition hover:border-orange/40 hover:text-orange"
                >
                  <Copy className="h-3.5 w-3.5" />
                  Copy yesterday
                </button>
              </div>
            )}
          </div>

          {rows.length === 0 && dayQuery.isFetched && !dayEditable && (
            <div className="px-5 py-12">
              <EmptyState
                icon={CalendarClock}
                title="No hours logged"
                text="This day has no entries or is submitted/approved."
              />
            </div>
          )}

          {/* ── Actions ── */}
          <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
            {dayEditable ? (
              <>
                <span className="text-xs text-muted">
                  Total{' '}
                  <span className="font-semibold tabular-nums text-ink">
                    {formatDuration(dayTotal)}
                  </span>
                </span>
                <div className="flex items-center gap-2">
                  {missingProject && (
                    <span className="text-xs font-medium text-warning">
                      Pick a project for every entry with hours.
                    </span>
                  )}
                  <button
                    onClick={discardChanges}
                    disabled={!dirty || saveMutation.isPending}
                    className={secondaryBtnClass}
                  >
                    Discard
                  </button>
                  <button
                    onClick={() => saveMutation.mutate()}
                    disabled={
                      !dirty ||
                      missingProject ||
                      saveMutation.isPending
                    }
                    className={secondaryBtnClass}
                  >
                    {saveMutation.isPending ? 'Saving…' : 'Save'}
                  </button>
                  <button
                    onClick={handleSubmit}
                    disabled={
                      dayTotal === 0 ||
                      missingProject ||
                      saveMutation.isPending ||
                      submitMutation.isPending
                    }
                    className={primaryBtnClass}
                  >
                    <Send className="h-4 w-4" />
                    {submitMutation.isPending
                      ? 'Submitting…'
                      : selectedDayStatus === 'rejected'
                        ? 'Resubmit'
                        : 'Submit for approval'}
                  </button>
                </div>
              </>
            ) : (
              <p className="text-xs text-muted">
                {selectedDayStatus === 'approved'
                  ? 'Approved days are locked.'
                  : selectedDayStatus === 'submitted'
                    ? 'Waiting for review — you can edit again if it is rejected.'
                    : 'Read-only.'}
              </p>
            )}
          </div>

          {(saveMutation.isError || submitMutation.isError || pdfMutation.isError) && (
            <div className="mx-5 mb-4 flex items-start gap-2 rounded-lg border border-danger/30 bg-dangerSoft px-4 py-3 text-sm text-danger">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{actionError ?? 'Something went wrong. Please try again.'}</span>
            </div>
          )}
        </>
      )}

      {confirmSubmit && (
        <ConfirmDialog
          title={selectedDayStatus === 'rejected' ? 'Resubmit for approval?' : 'Submit for approval?'}
          message={`Once submitted, your hours (${formatDuration(dayTotal)}) for editable days are locked while under review — you cannot edit or add entries until a lead responds. Rejected days reopen for fixes; approved days are final.`}
          confirmLabel="Send for approval"
          tone="info"
          pending={submitMutation.isPending}
          onConfirm={() => void doSubmit()}
          onClose={() => setConfirmSubmit(false)}
        />
      )}
    </section>
  );
}

function EntryEditorRow({
  row,
  editable,
  projects,
  onChange,
  onRemove,
}: {
  row: EntryRow;
  editable: boolean;
  projects: { id: number; name: string }[];
  onChange: (changes: Partial<EntryRow>) => void;
  onRemove: () => void;
}) {
  const cellBase =
    'w-full rounded-md border border-border bg-surface px-2 text-sm text-ink shadow-card transition placeholder:text-muted/70 focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30 disabled:bg-paper disabled:text-muted';
  return (
    <tr className="align-middle hover:bg-surfaceWarm/50">
      <td className="px-3 py-2">
        <input
          type="date"
          value={row.date}
          disabled={!editable}
          onChange={(e) => onChange({ date: e.target.value })}
          max={toISODate(new Date())}
          className={`${cellBase} h-9 tabular-nums`}
        />
      </td>
      <td className="px-3 py-2">
        <input
          value={row.hours}
          onChange={(e) =>
            onChange({ hours: e.target.value.replace(/[^0-9.]/g, '').slice(0, 5) })
          }
          disabled={!editable}
          inputMode="decimal"
          placeholder="0"
          className={`${cellBase} h-9 text-center tabular-nums`}
        />
      </td>
      <td className="max-w-[220px] px-3 py-2">
        <select
          value={row.project_id ?? ''}
          disabled={!editable}
          onChange={(e) =>
            onChange({ project_id: e.target.value ? Number(e.target.value) : null })
          }
          className={`${cellBase} h-9`}
        >
          <option value="">Select project…</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </td>
      <td className="px-3 py-2">
        <input
          value={row.location}
          onChange={(e) => onChange({ location: e.target.value })}
          disabled={!editable}
          placeholder="e.g. Studio, Site"
          className={`${cellBase} h-9`}
        />
      </td>
      <td className="px-3 py-2">
        <input
          value={row.description}
          onChange={(e) => onChange({ description: e.target.value })}
          disabled={!editable}
          placeholder="What did you work on?"
          className={`${cellBase} h-9`}
        />
      </td>
      {editable ? (
        <td className="px-2 py-2 text-center">
          <button
            onClick={onRemove}
            title="Remove entry"
            className="rounded-md p-1.5 text-muted transition hover:bg-dangerSoft hover:text-danger"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </td>
      ) : (
        <td />
      )}
    </tr>
  );
}

function History() {
  const historyQuery = useQuery({
    queryKey: ['timesheets', 'mine'],
    queryFn: () => getMyTimesheets(),
  });
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [viewingId, setViewingId] = useState<number | null>(null);
  const now = new Date();
  const [exportMonth, setExportMonth] = useState(
    `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`,
  );
  const [exporting, setExporting] = useState<'xlsx' | 'pdf' | null>(null);

  async function handleDownload(id: number) {
    setDownloadingId(id);
    try {
      await downloadTimesheetPdf(id);
    } finally {
      setDownloadingId(null);
    }
  }

  async function handleExport(format: 'xlsx' | 'pdf') {
    const [year, month] = exportMonth.split('-').map(Number);
    if (!year || !month) return;
    setExporting(format);
    try {
      await downloadTimesheetMonthExport(year, month, format);
    } finally {
      setExporting(null);
    }
  }

  return (
    <section className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold text-ink">Past weeks</h2>
          <p className="mt-0.5 text-xs text-muted">
            Your recent timesheets — download any week as a PDF receipt.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="month"
            value={exportMonth}
            max={`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`}
            onChange={(e) => setExportMonth(e.target.value)}
            className="h-8 rounded-md border border-border bg-surface px-2 text-xs tabular-nums text-ink focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30"
            aria-label="Export month"
          />
          <button
            onClick={() => void handleExport('xlsx')}
            disabled={!exportMonth || exporting !== null}
            title="Download the month's entries as Excel"
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-surface px-2.5 text-xs font-medium text-muted transition hover:bg-surfaceWarm hover:text-ink disabled:opacity-60"
          >
            <FileSpreadsheet className="h-3.5 w-3.5" />
            {exporting === 'xlsx' ? '…' : 'XLSX'}
          </button>
          <button
            onClick={() => void handleExport('pdf')}
            disabled={!exportMonth || exporting !== null}
            title="Download the month's entries as PDF"
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-surface px-2.5 text-xs font-medium text-muted transition hover:bg-surfaceWarm hover:text-ink disabled:opacity-60"
          >
            <Download className="h-3.5 w-3.5" />
            {exporting === 'pdf' ? '…' : 'PDF'}
          </button>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b border-border bg-paper/60 text-[11px] font-semibold uppercase tracking-wider text-muted">
            <tr>
              <th className="px-4 py-3">Week</th>
              <th className="px-4 py-3">Hours</th>
              <th className="px-4 py-3">Entries</th>
              <th className="px-4 py-3">Submitted</th>
              <th className="px-4 py-3">Reviewed by</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {historyQuery.isPending ? (
              <tr>
                <td colSpan={7} className="px-4 py-8">
                  <Skeleton className="h-5 w-full" />
                </td>
              </tr>
            ) : historyQuery.isError ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-sm text-muted">
                  Couldn't load history.
                </td>
              </tr>
            ) : (historyQuery.data?.items.length ?? 0) === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-sm text-muted">
                  No past weeks yet.
                </td>
              </tr>
            ) : (
              historyQuery.data!.items.map((row) => (
                <tr key={row.id} className="transition hover:bg-surfaceWarm">
                  <td className="px-4 py-3 font-medium tabular-nums text-ink">
                    {formatDateRange(row.week_start, row.week_end)}
                  </td>
                  <td className="px-4 py-3 tabular-nums text-muted">
                    {formatDuration(row.total_hours)}
                  </td>
                  <td className="px-4 py-3 tabular-nums text-muted">{row.entry_count}</td>
                  <td className="px-4 py-3 text-muted">{formatDate(row.submitted_at)}</td>
                  <td className="px-4 py-3 text-muted">{row.approved_by_name ?? '—'}</td>
                  <td className="px-4 py-3">
                    <TimesheetStatusBadge status={row.status} />
                    {row.status === 'rejected' && row.rejection_reason && (
                      <p className="mt-1 max-w-[240px] text-xs text-muted">
                        <span className="font-medium">Reason:</span> {row.rejection_reason}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => setViewingId(row.id)}
                        title="View this week's entries"
                        className="inline-flex items-center gap-1 rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs font-medium text-muted transition hover:bg-surfaceWarm hover:text-ink"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        View
                      </button>
                      <button
                        onClick={() => handleDownload(row.id)}
                        disabled={downloadingId === row.id}
                        title="Download PDF receipt"
                        className="inline-flex items-center gap-1 rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs font-medium text-muted transition hover:bg-surfaceWarm hover:text-ink disabled:opacity-60"
                      >
                        <Download className="h-3.5 w-3.5" />
                        {downloadingId === row.id ? '…' : 'PDF'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {viewingId !== null && (
        <TimesheetDetailModal timesheetId={viewingId} onClose={() => setViewingId(null)} />
      )}
    </section>
  );
}
