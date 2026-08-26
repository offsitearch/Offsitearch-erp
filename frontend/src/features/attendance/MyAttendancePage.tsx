import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock,
  LogIn,
  LogOut,
  MapPin,
  RefreshCw,
  StickyNote,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { checkIn, checkOut, getHolidays, getMyAttendance } from '../../api/attendance';
import { ATTENDANCE_METHOD_LABELS, ATTENDANCE_STATUS_META, ATTENDANCE_STATUS_OPTIONS } from '../../lib/constants';
import { formatDuration, formatMinutesDuration, formatTime, monthLabel, toISODate } from '../../lib/date';
import type { AttendanceRecord, AttendanceStatus } from '../../lib/types';
import { LogoLoader } from '../../components/LogoLoader';
import { MonthCalendar } from './components/MonthCalendar';
import { useTranslation } from 'react-i18next';

const SUMMARY_ORDER: AttendanceStatus[] = ['present', 'late', 'half_day', 'work_from_home', 'absent', 'on_leave'];

function liveMinutes(checkInISO: string | null | undefined, now: Date): number {
  if (!checkInISO) return 0;
  const started = new Date(checkInISO).getTime();
  if (Number.isNaN(started)) return 0;
  return Math.max(0, Math.floor((now.getTime() - started) / 60_000));
}

function recordDetail(record: AttendanceRecord | undefined): string | null {
  if (!record) return null;
  const parts: string[] = [];
  if (record.check_in_method !== 'web')
    parts.push(ATTENDANCE_METHOD_LABELS[record.check_in_method] ?? record.check_in_method);
  if (record.check_in_location) parts.push(record.check_in_location);
  const text = parts.join(' · ');
  if (record.notes) return text ? `${text} — ${record.notes}` : record.notes;
  return text || null;
}

function ClockDisplay({ time }: { time: Date }) {
  const hh = String(time.getHours()).padStart(2, '0');
  const mm = String(time.getMinutes()).padStart(2, '0');
  return (
    <span className="font-mono text-[40px] font-light leading-none tracking-tight text-white">
      {hh}
      <span className="animate-pulse text-white/40">:</span>
      {mm}
    </span>
  );
}

export default function MyAttendancePage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [viewMonth, setViewMonth] = useState(() => new Date());
  const todayISO = toISODate(new Date());
  const [selectedDate, setSelectedDate] = useState<string | null>(todayISO);
  const [notice, setNotice] = useState<{ kind: 'success' | 'error'; text: string } | null>(null);
  const [now, setNow] = useState(() => new Date());
  const [showDetails, setShowDetails] = useState(false);
  const [checkInLocation, setCheckInLocation] = useState('');
  const [checkInNote, setCheckInNote] = useState('');
  const [confirmCheckout, setConfirmCheckout] = useState(false);

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (!notice || notice.kind !== 'success') return;
    const id = window.setTimeout(() => setNotice(null), 4000);
    return () => window.clearTimeout(id);
  }, [notice]);

  const year = viewMonth.getFullYear();
  const month = viewMonth.getMonth();

  const summary = useQuery({
    queryKey: ['attendance', 'me', year, month],
    queryFn: () => getMyAttendance(month + 1, year),
  });

  const holidays = useQuery({
    queryKey: ['attendance', 'holidays', year],
    queryFn: () => getHolidays(year),
  });

  const todayRecord = summary.data?.records.find((r) => r.date === todayISO);

  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['attendance', 'me'] }),
      queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
    ]);

  const checkInMutation = useMutation({
    mutationFn: () =>
      checkIn({
        method: 'web',
        location: checkInLocation.trim() || undefined,
        notes: checkInNote.trim() || undefined,
      }),
    onSuccess: (data) => {
      invalidate();
      setShowDetails(false);
      setCheckInLocation('');
      setCheckInNote('');
      setNotice({ kind: 'success', text: `Checked in successfully at ${formatTime(data.check_in_time)}.` });
    },
    onError: () => setNotice({ kind: 'error', text: "Couldn't record your check-in. Please try again." }),
  });

  const checkOutMutation = useMutation({
    mutationFn: checkOut,
    onSuccess: (data) => {
      invalidate();
      setConfirmCheckout(false);
      setNotice({ kind: 'success', text: `Checked out successfully at ${formatTime(data.check_out_time)}.` });
    },
    onError: () => setNotice({ kind: 'error', text: "Couldn't record your check-out. Please try again." }),
  });

  const hasActiveSession = Boolean(todayRecord?.check_in_time && !todayRecord?.check_out_time);
  const checkedIn = hasActiveSession;
  const checkedOut = Boolean(todayRecord?.check_out_time);
  const isLate = todayRecord?.status === 'late';

  const pill = !todayRecord
    ? { label: t('dashboard.notCheckedIn'), bg: 'bg-white/10', text: 'text-white/60', dot: 'bg-white/40' }
    : hasActiveSession
      ? isLate
        ? {
            label: `Late · ${todayRecord.late_minutes ?? 0}m`,
            bg: 'bg-warning/15',
            text: 'text-warning',
            dot: 'bg-warning',
          }
        : {
            label: t('attendance.checkedInStatus'),
            bg: 'bg-success/15',
            text: 'text-success',
            dot: 'bg-success',
          }
      : {
          label: checkedOut ? 'Checked out' : t('dashboard.dayComplete'),
          bg: 'bg-success/15',
          text: 'text-success',
          dot: 'bg-success',
        };

  const workedMinutes = useMemo(() => {
    if (!todayRecord) return 0;
    const accumulated = parseFloat(String(todayRecord.total_hours || 0));
    const accumulatedMin = Number.isNaN(accumulated) ? 0 : Math.round(accumulated * 60);
    if (hasActiveSession) {
      return accumulatedMin + liveMinutes(todayRecord.check_in_time, now);
    }
    return accumulatedMin;
  }, [todayRecord, hasActiveSession, now]);

  const worked = workedMinutes > 0 ? formatMinutesDuration(workedMinutes) : '—';

  const totals = summary.data?.totals ?? {};
  const summaryRows = SUMMARY_ORDER.map((status) => {
    const meta = ATTENDANCE_STATUS_META[status];
    return { status, meta, count: totals[status] ?? 0 };
  });

  const totalDaysTracked = summaryRows.reduce((sum, r) => sum + r.count, 0);
  const presentDays = (totals['present'] ?? 0) + (totals['late'] ?? 0);
  const attendanceRate = totalDaysTracked > 0 ? Math.round((presentDays / totalDaysTracked) * 100) : 0;

  const selectedRecord = summary.data?.records.find((r) => r.date === selectedDate);

  function shiftMonth(delta: number) {
    setViewMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + delta, 1));
  }

  function goToToday() {
    const today = new Date();
    setViewMonth(new Date(today.getFullYear(), today.getMonth(), 1));
    setSelectedDate(todayISO);
  }

  const emptyMonth = summary.data && summary.data.records.length === 0;

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">{t('attendance.title')}</h1>
           <p className="mt-1 text-sm text-muted">{t('attendance.trackDaily')}</p>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* ── Left column: Today card + Month summary ── */}
        <div className="space-y-6 lg:col-span-1">
          {/* ── Today Hero Card ── */}
          <section className="relative overflow-hidden rounded-xl border border-navy/20 bg-gradient-to-br from-navy via-navyDark to-navy text-white shadow-card">
            <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-white/5" />
            <div className="absolute -bottom-4 -left-4 h-16 w-16 rounded-full bg-orange/10" />

            <div className="relative flex items-center justify-between border-b border-white/10 px-5 py-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-white/40">Today</p>
                <p className="mt-0.5 text-sm font-medium text-white/90">
                  {now.toLocaleDateString('en-IN', {
                    weekday: 'long',
                    day: 'numeric',
                    month: 'long',
                  })}
                </p>
              </div>
              <span
                className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${pill.bg} ${pill.text}`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${pill.dot} ${checkedIn && !checkedOut ? 'animate-pulse' : ''}`} />
                {pill.label}
              </span>
            </div>

            <div className="relative p-5">
              {!todayRecord ? (
                <>
                  <div className="mb-5 flex justify-center">
                    <ClockDisplay time={now} />
                  </div>
                  <div className="flex items-start gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white/70">
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-sky" />
                    <span>{t('attendance.youHaventCheckedIn')}</span>
                  </div>
                </>
              ) : (
                <>
                  <div className="mb-4 grid grid-cols-4 gap-3">
                    <div className="rounded-lg bg-white/5 px-3 py-2.5 text-center">
                      <p className="text-[10px] font-medium uppercase tracking-wider text-white/40">In</p>
                      <p className="mt-0.5 text-sm font-semibold tabular-nums text-white">
                        {formatTime(todayRecord.check_in_time)}
                      </p>
                    </div>
                    <div className="rounded-lg bg-white/5 px-3 py-2.5 text-center">
                      <p className="text-[10px] font-medium uppercase tracking-wider text-white/40">Out</p>
                      <p className="mt-0.5 text-sm font-semibold tabular-nums text-white">
                        {formatTime(todayRecord.check_out_time)}
                      </p>
                    </div>
                    <div className="rounded-lg bg-white/5 px-3 py-2.5 text-center">
                      <p className="text-[10px] font-medium uppercase tracking-wider text-white/40">Worked</p>
                      <p className="mt-0.5 text-sm font-semibold tabular-nums text-orange">{worked}</p>
                    </div>
                    <div className="rounded-lg bg-white/5 px-3 py-2.5 text-center">
                      <p className="text-[10px] font-medium uppercase tracking-wider text-white/40">OT</p>
                      <p className="mt-0.5 text-sm font-semibold tabular-nums text-warning">
                        {formatDuration(todayRecord.overtime_hours ?? null) || '—'}
                      </p>
                    </div>
                  </div>
                </>
              )}

              {/* ── Action area ── */}
              <div className="space-y-3">
                {!checkedIn && (
                  <button
                    type="button"
                    onClick={() => setShowDetails((v) => !v)}
                    className="inline-flex items-center gap-1.5 rounded-md px-1 py-1 text-xs font-medium text-white/60 transition hover:text-white"
                  >
                    <ChevronDown className={`h-3.5 w-3.5 transition-transform ${showDetails ? 'rotate-180' : ''}`} />
                    {showDetails ? 'Hide details' : 'Add location / note'}
                  </button>
                )}

                {!checkedIn && showDetails && (
                  <div className="space-y-2.5 rounded-lg border border-white/10 bg-white/5 p-3">
                    <label className="block">
                      <span className="mb-1 flex items-center gap-1.5 text-xs font-medium text-white/50">
                        <MapPin className="h-3 w-3" /> {t('attendance.location')}
                      </span>
                      <input
                        value={checkInLocation}
                        onChange={(e) => setCheckInLocation(e.target.value)}
                        placeholder="e.g. Studio, Client site, Home"
                        className="w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-white/30 focus:border-orange/60 focus:outline-none focus:ring-2 focus:ring-orange/30"
                      />
                    </label>
                    <label className="block">
                      <span className="mb-1 flex items-center gap-1.5 text-xs font-medium text-white/50">
                        <StickyNote className="h-3 w-3" /> {t('attendance.note')}
                      </span>
                      <input
                        value={checkInNote}
                        onChange={(e) => setCheckInNote(e.target.value)}
                        placeholder="Optional note"
                        className="w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-white/30 focus:border-orange/60 focus:outline-none focus:ring-2 focus:ring-orange/30"
                      />
                    </label>
                  </div>
                )}

                {!hasActiveSession ? (
                  <button
                    onClick={() => checkInMutation.mutate()}
                    disabled={checkInMutation.isPending}
                    className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-orange px-4 text-sm font-semibold text-white transition hover:bg-orangeDark focus:outline-none focus:ring-2 focus:ring-orange/50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {checkInMutation.isPending ? (
                      <>
                        <Clock className="h-4 w-4 animate-spin" />
                        Checking in…
                      </>
                    ) : (
                      <>
                        <LogIn className="h-4 w-4" />
                        {checkedOut ? 'Check In Again' : 'Check In'}
                      </>
                    )}
                  </button>
                ) : (
                  confirmCheckout ? (
                    <div className="space-y-2 rounded-lg border border-white/10 bg-white/5 p-3">
                      <p className="text-xs font-medium text-white/60">{t('attendance.confirmCheckoutQuestion')}</p>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setConfirmCheckout(false)}
                          disabled={checkOutMutation.isPending}
                          className="inline-flex h-9 flex-1 items-center justify-center gap-2 rounded-md border border-white/20 px-3 text-sm font-medium text-white transition hover:bg-white/10"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => checkOutMutation.mutate(undefined)}
                          disabled={checkOutMutation.isPending}
                          className="inline-flex h-9 flex-1 items-center justify-center gap-2 rounded-md border border-danger/40 bg-danger/20 px-3 text-sm font-semibold text-white transition hover:bg-danger/30 disabled:opacity-60"
                        >
                          {checkOutMutation.isPending ? (
                            <>
                              <Clock className="h-4 w-4 animate-spin" />
                              Checking out…
                            </>
                          ) : (
                            <>
                              <LogOut className="h-4 w-4" />
                              Confirm checkout
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setConfirmCheckout(true)}
                      disabled={checkOutMutation.isPending}
                      className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg border-2 border-white/20 bg-white/5 px-4 text-sm font-semibold text-white transition hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-white/30 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <LogOut className="h-4 w-4" />
                      Check Out
                    </button>
                  )
                )}
              </div>

              {notice && (
                <div
                  className={`mt-3 flex items-start gap-2 rounded-lg border px-3 py-2.5 text-sm ${
                    notice.kind === 'success'
                      ? 'border-success/30 bg-success/15 text-success'
                      : 'border-danger/30 bg-danger/15 text-danger'
                  }`}
                  role="status"
                >
                  {notice.kind === 'success' ? (
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                  ) : (
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  )}
                  <span>{notice.text}</span>
                  {notice.kind === 'error' && (
                    <button
                      onClick={() => setNotice(null)}
                      className="ml-auto shrink-0 text-xs font-medium underline-offset-2 hover:underline"
                    >
                      Dismiss
                    </button>
                  )}
                </div>
              )}
            </div>
          </section>

          {/* ── Month Summary Card ── */}
          <section className="rounded-xl border border-border bg-surface shadow-card">
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <p className="text-sm font-semibold text-ink">Month summary</p>
              <p className="text-xs font-medium text-muted">{monthLabel(year, month)}</p>
            </div>
            <div className="p-5">
              {summary.isPending ? (
                <LogoLoader />
              ) : summary.isError ? (
                <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border px-4 py-6 text-center">
                  <p className="text-sm text-muted">Couldn't load month totals.</p>
                  <button
                    onClick={() => summary.refetch()}
                    className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 text-sm font-medium text-ink transition hover:bg-surfaceWarm"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    Retry
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Attendance rate ring */}
                  <div className="flex items-center gap-4 rounded-lg bg-paper px-4 py-3">
                    <div className="relative h-14 w-14 shrink-0">
                      <svg className="h-14 w-14 -rotate-90" viewBox="0 0 56 56">
                        <circle cx="28" cy="28" r="24" fill="none" className="stroke-border" strokeWidth="4" />
                        <circle
                          cx="28"
                          cy="28"
                          r="24"
                          fill="none"
                          className="stroke-success"
                          strokeWidth="4"
                          strokeDasharray={`${(attendanceRate / 100) * 150.8} 150.8`}
                          strokeLinecap="round"
                        />
                      </svg>
                      <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-ink">
                        {attendanceRate}%
                      </span>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-ink">Attendance rate</p>
                      <p className="text-xs text-muted">
                        {presentDays} of {totalDaysTracked} working days
                      </p>
                    </div>
                  </div>

                  {/* Status rows */}
                  <div className="space-y-1.5">
                    {summaryRows.map((row) => {
                      const Icon = row.meta.icon;
                      return (
                        <div
                          key={row.status}
                          className="flex items-center gap-3 rounded-lg px-3 py-2 transition hover:bg-surfaceWarm"
                        >
                          <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${row.meta.cell}`}>
                            <Icon className={`h-4 w-4 ${row.meta.iconColor}`} />
                          </span>
                          <span className="flex-1 text-sm text-ink">{row.meta.label}</span>
                          <span className="text-lg font-bold tabular-nums text-ink">{row.count}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </section>
        </div>

        {/* ── Right column: Calendar ── */}
        <div className="lg:col-span-2">
          <section className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
              <h2 className="text-lg font-semibold tracking-tight text-ink">{monthLabel(year, month)}</h2>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => shiftMonth(-1)}
                  className="inline-flex h-9 items-center justify-center gap-1 rounded-md border border-border bg-surface px-2.5 text-sm font-medium text-ink transition hover:bg-surfaceWarm focus:outline-none focus-visible:ring-2 focus-visible:ring-navy/40"
                  aria-label="Previous month"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  onClick={goToToday}
                  className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 text-sm font-medium text-ink transition hover:bg-surfaceWarm focus:outline-none focus-visible:ring-2 focus-visible:ring-navy/40"
                >
                  Today
                </button>
                <button
                  onClick={() => shiftMonth(1)}
                  className="inline-flex h-9 items-center justify-center gap-1 rounded-md border border-border bg-surface px-2.5 text-sm font-medium text-ink transition hover:bg-surfaceWarm focus:outline-none focus-visible:ring-2 focus-visible:ring-navy/40"
                  aria-label="Next month"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-b border-border px-5 py-3">
              {ATTENDANCE_STATUS_OPTIONS.map((status) => (
                <span key={status} className="flex items-center gap-1.5 text-xs text-muted">
                  <span className={`h-2 w-2 shrink-0 rounded-full ${ATTENDANCE_STATUS_META[status].dot}`} />
                  {ATTENDANCE_STATUS_META[status].label}
                </span>
              ))}
            </div>

            <div className="p-3">
              {summary.isPending ? (
                <LogoLoader />
              ) : summary.isError ? (
                <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border px-4 py-10 text-center">
                  <AlertCircle className="h-6 w-6 text-danger" />
                  <p className="text-sm font-medium text-ink">Couldn't load attendance history.</p>
                  <button
                    onClick={() => summary.refetch()}
                    className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 text-sm font-medium text-ink transition hover:bg-surfaceWarm"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    Retry
                  </button>
                </div>
              ) : (
                <>
                  {emptyMonth && (
                    <div className="mb-3 rounded-lg border border-dashed border-border px-4 py-4 text-center">
                      <p className="text-sm font-medium text-ink">No attendance records yet.</p>
                      <p className="mt-0.5 text-xs text-muted">
                        {t('attendance.attendanceHistoryWillAppear')}
                      </p>
                    </div>
                  )}
                  <MonthCalendar
                    year={year}
                    month={month}
                    records={summary.data?.records ?? []}
                    holidays={holidays.data ?? []}
                    selectedDate={selectedDate}
                    onSelectDay={setSelectedDate}
                  />
                  {selectedRecord && (
                    <div className="mt-3 overflow-hidden rounded-lg border border-border bg-paper">
                      <div className="flex items-center gap-3 px-4 py-3">
                        <span
                          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${ATTENDANCE_STATUS_META[selectedRecord.status].cell}`}
                        >
                          {(() => {
                            const SelIcon = ATTENDANCE_STATUS_META[selectedRecord.status].icon;
                            return <SelIcon className={`h-5 w-5 ${ATTENDANCE_STATUS_META[selectedRecord.status].iconColor}`} />;
                          })()}
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-semibold text-ink">
                              {new Date(`${selectedRecord.date}T00:00:00`).toLocaleDateString('en-IN', {
                                weekday: 'short',
                                day: 'numeric',
                                month: 'short',
                              })}
                            </p>
                            <span
                              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${ATTENDANCE_STATUS_META[selectedRecord.status].badge}`}
                            >
                              {ATTENDANCE_STATUS_META[selectedRecord.status].label}
                            </span>
                          </div>
                          <p className="mt-0.5 text-xs tabular-nums text-muted">
                            {formatTime(selectedRecord.check_in_time)} – {formatTime(selectedRecord.check_out_time)} ·{' '}
                            {formatDuration(selectedRecord.total_hours) || '0h'}
                          </p>
                          {recordDetail(selectedRecord) && (
                            <p className="mt-0.5 text-xs text-muted">{recordDetail(selectedRecord)}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
