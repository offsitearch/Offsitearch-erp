import { useQuery } from '@tanstack/react-query';
import {
  AlertCircle,
  CalendarDays,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Download,
  MinusCircle,
  RefreshCw,
  Users,
  XCircle,
} from 'lucide-react';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDepartments } from '../../api/employees';
import { getHolidays, getReportRows, downloadReportXlsx } from '../../api/attendance';
import { ATTENDANCE_STATUS_META, ATTENDANCE_STATUS_OPTIONS } from '../../lib/constants';
import { buildMonthGrid, monthLabel, toISODate, WEEKDAYS } from '../../lib/date';
import type { AttendanceStatus } from '../../lib/types';
import { LogoLoader } from '../../components/LogoLoader';
import { useTranslation } from 'react-i18next';
import { inputClass } from '../../lib/styles';

const MAX_STATUS_ROWS = 3;

export default function AttendanceCalendarPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const now = new Date();
  const [viewMonth, setViewMonth] = useState(() => new Date(now.getFullYear(), now.getMonth(), 1));
  const [departmentId, setDepartmentId] = useState<number | ''>('');

  const year = viewMonth.getFullYear();
  const month = viewMonth.getMonth();
  const from = toISODate(new Date(year, month, 1));
  const to = toISODate(new Date(year, month + 1, 0));

  const departments = useQuery({ queryKey: ['departments'], queryFn: getDepartments });

  const report = useQuery({
    queryKey: ['attendance', 'report', from, to, departmentId],
    queryFn: () => getReportRows(from, to, departmentId === '' ? null : departmentId),
  });

  const holidays = useQuery({
    queryKey: ['attendance', 'holidays', year],
    queryFn: () => getHolidays(year),
  });
  const holidaysByDate = new Map((holidays.data ?? []).map((h) => [h.date, h]));

  const countsByDate = new Map<string, Map<string, number>>();
  for (const row of report.data ?? []) {
    if (!countsByDate.has(row.date)) countsByDate.set(row.date, new Map());
    const day = countsByDate.get(row.date)!;
    day.set(row.status, (day.get(row.status) ?? 0) + 1);
  }

  const cells = buildMonthGrid(year, month);
  const todayISO = toISODate(new Date());

  const monthTotals = useMemo(() => {
    const totals: Partial<Record<AttendanceStatus, number>> = {};
    let total = 0;
    for (const row of report.data ?? []) {
      totals[row.status] = (totals[row.status] ?? 0) + 1;
      total++;
    }
    return { totals, total };
  }, [report.data]);

  function shiftMonth(delta: number) {
    setViewMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + delta, 1));
  }

  function goToToday() {
    const today = new Date();
    setViewMonth(new Date(today.getFullYear(), today.getMonth(), 1));
  }

  const summaryStats = [
    { label: 'Total', value: monthTotals.total, icon: Users, color: 'text-navy', bg: 'bg-navy/10' },
    { label: 'Present', value: (monthTotals.totals['present'] ?? 0) + (monthTotals.totals['late'] ?? 0), icon: CheckCircle2, color: 'text-success', bg: 'bg-successSoft' },
    { label: 'Absent', value: monthTotals.totals['absent'] ?? 0, icon: XCircle, color: 'text-danger', bg: 'bg-dangerSoft' },
    { label: 'On Leave', value: monthTotals.totals['on_leave'] ?? 0, icon: CalendarDays, color: 'text-navy', bg: 'bg-navy/10' },
    { label: 'WFH', value: monthTotals.totals['work_from_home'] ?? 0, icon: MinusCircle, color: 'text-info', bg: 'bg-infoSoft' },
  ];

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">{t('attendance.title')}</h1>
           <p className="mt-1 text-sm text-muted">{t('attendance.dayWiseHeadcount')}</p>
        </div>
      </header>

      {/* ── Controls row ── */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap items-end gap-3">
          <button
            onClick={() => shiftMonth(-1)}
            className="inline-flex h-10 items-center justify-center gap-1 rounded-md border border-border bg-surface px-2.5 text-sm font-medium text-ink transition hover:bg-surfaceWarm focus:outline-none focus-visible:ring-2 focus-visible:ring-navy/40"
            aria-label="Previous month"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button
            onClick={goToToday}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 text-sm font-medium text-ink transition hover:bg-surfaceWarm focus:outline-none focus-visible:ring-2 focus-visible:ring-navy/40"
          >
            Today
          </button>
          <button
            onClick={() => shiftMonth(1)}
            className="inline-flex h-10 items-center justify-center gap-1 rounded-md border border-border bg-surface px-2.5 text-sm font-medium text-ink transition hover:bg-surfaceWarm focus:outline-none focus-visible:ring-2 focus-visible:ring-navy/40"
            aria-label="Next month"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
          <p className="self-center pl-1 text-lg font-semibold tracking-tight text-ink">
            {monthLabel(year, month)}
          </p>
        </div>
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-muted">{t('attendance.department')}</span>
          <select
            value={departmentId}
            onChange={(e) => setDepartmentId(e.target.value === '' ? '' : Number(e.target.value))}
            className={inputClass}
          >
            <option value="">{t('attendance.allDepartments')}</option>
            {(departments.data ?? []).map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-muted">Report type</span>
          <span className="inline-flex h-10 items-center rounded-md border border-border bg-surface px-3 text-sm text-muted">Full attendance</span>
        </label>
        <button
          onClick={() => downloadReportXlsx(from, to)}
          disabled={report.isPending || (report.data ?? []).length === 0}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-border bg-surface px-4 text-sm font-medium text-ink transition hover:bg-surfaceWarm focus:outline-none focus-visible:ring-2 focus-visible:ring-navy/40 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Download className="h-4 w-4" />
          Open in Sheets
        </button>
      </div>

      {/* ── Month summary stats ── */}
      {!report.isPending && !report.isError && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {summaryStats.map((stat) => {
            const Icon = stat.icon;
            return (
              <div
                key={stat.label}
                className="flex items-center gap-3 rounded-xl border border-border bg-surface px-4 py-3 shadow-sm"
              >
                <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${stat.bg}`}>
                  <Icon className={`h-4.5 w-4.5 ${stat.color}`} />
                </span>
                <div>
                  <p className="text-[11px] font-medium uppercase tracking-wider text-muted">{stat.label}</p>
                  <p className="text-lg font-bold tabular-nums text-ink">{stat.value}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Legend ── */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
        {ATTENDANCE_STATUS_OPTIONS.map((s) => (
          <span key={s} className="flex items-center gap-1.5 text-xs text-muted">
            <span className={`h-2 w-2 rounded-full ${ATTENDANCE_STATUS_META[s].dot}`} />
            {ATTENDANCE_STATUS_META[s].label}
          </span>
        ))}
      </div>

      {/* ── Calendar grid ── */}
      <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
        {report.isPending ? (
          <LogoLoader />
        ) : report.isError ? (
          <div className="flex flex-col items-center gap-3 px-4 py-12 text-center">
            <AlertCircle className="h-6 w-6 text-danger" />
             <p className="text-sm font-medium text-ink">{t('attendance.couldntLoadMonth')}</p>
            <button
              onClick={() => report.refetch()}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-border bg-surface px-4 text-sm font-medium text-ink transition hover:bg-surfaceWarm"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <div className="min-w-[560px]">
              <div className="grid grid-cols-7 border-b border-border">
                {WEEKDAYS.map((day) => (
                  <div
                    key={day}
                    className="px-1 py-2.5 text-center text-[11px] font-semibold uppercase tracking-wider text-muted"
                  >
                    {day}
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-7">
                {cells.map(({ date, inMonth }, index) => {
                  const iso = toISODate(date);
                  const dayCounts = countsByDate.get(iso);
                  const holiday = holidaysByDate.get(iso);
                  const isToday = iso === todayISO;
                  const isWeekend = date.getDay() === 0 || date.getDay() === 6;

                  const statusRows = dayCounts
                    ? Array.from(dayCounts.entries())
                        .sort(
                          (a, b) =>
                            ATTENDANCE_STATUS_OPTIONS.indexOf(a[0] as (typeof ATTENDANCE_STATUS_OPTIONS)[number]) -
                            ATTENDANCE_STATUS_OPTIONS.indexOf(b[0] as (typeof ATTENDANCE_STATUS_OPTIONS)[number]),
                        )
                        .map(([status, count]) => ({
                          meta: ATTENDANCE_STATUS_META[status as keyof typeof ATTENDANCE_STATUS_META],
                          count,
                        }))
                    : [];
                  const visibleRows = statusRows.slice(0, MAX_STATUS_ROWS);
                  const more = statusRows.length - visibleRows.length;
                  const dayTotal = statusRows.reduce((sum, r) => sum + r.count, 0);

                  const cellClass = [
                    'relative min-h-[5.75rem] border-r border-b border-border p-1.5 text-left',
                    index % 7 === 6 ? 'border-r-0' : '',
                    index >= 35 ? 'border-b-0' : '',
                    !inMonth
                      ? 'bg-paper/30'
                      : isWeekend
                        ? 'bg-surfaceWarm/30'
                        : 'bg-surface',
                    isToday ? 'ring-1 ring-inset ring-orange/30 bg-orange/[0.03]' : '',
                    inMonth
                      ? 'cursor-pointer transition hover:bg-surfaceWarm/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-navy'
                      : '',
                  ]
                    .filter(Boolean)
                    .join(' ');

                  const cellContent = (
                    <>
                      {isToday && (
                        <span aria-hidden="true" className="absolute inset-x-0 top-0 h-0.5 rounded-t bg-orange" />
                      )}
                      <div className="flex items-start justify-between gap-1">
                        <span
                          className={`inline-flex h-6 items-center justify-center text-xs font-medium ${
                            isToday ? 'font-bold text-ink' : !inMonth ? 'text-muted/30' : isWeekend ? 'text-muted/60' : 'text-ink'
                          }`}
                        >
                          {date.getDate()}
                        </span>
                        <div className="flex items-center gap-1">
                          {dayTotal > 0 && (
                            <span className="rounded-full bg-navy/10 px-1.5 py-px text-[9px] font-bold tabular-nums text-navy">
                              {dayTotal}
                            </span>
                          )}
                          {isToday && (
                            <span className="rounded-sm bg-orange/15 px-1.5 py-px text-[9px] font-bold uppercase tracking-wider text-orange">
                              Today
                            </span>
                          )}
                        </div>
                      </div>
                      {holiday && inMonth && (
                        <p
                          className="mt-1 truncate rounded-sm bg-infoSoft px-1 py-px text-[10px] font-medium text-info"
                          title={holiday.name}
                        >
                          {holiday.name}
                        </p>
                      )}
                      {inMonth &&
                        visibleRows.map(({ meta, count }) => (
                          <div
                            key={meta.label}
                            className="mt-1 flex items-center justify-between gap-1 rounded bg-surfaceWarm/60 px-1.5 py-0.5 text-[10px]"
                            title={`${meta.label}: ${count}`}
                          >
                            <span className="flex min-w-0 items-center gap-1 font-medium text-muted">
                              <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${meta.dot}`} />
                              <span className="truncate">{meta.short}</span>
                            </span>
                            <span className="shrink-0 font-semibold tabular-nums text-ink">{count}</span>
                          </div>
                        ))}
                      {more > 0 && (
                        <p className="mt-1 text-[10px] font-semibold text-muted">+{more} more</p>
                      )}
                    </>
                  );

                  if (inMonth) {
                    return (
                      <button
                        key={index}
                        type="button"
                        onClick={() => navigate(`/attendance?tab=today&date=${iso}`)}
                        className={cellClass}
                        aria-label={`${date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}${isToday ? ', today' : ''}${dayTotal > 0 ? `, ${dayTotal} records` : ''}`}
                      >
                        {cellContent}
                      </button>
                    );
                  }

                  return (
                    <div key={index} className={cellClass}>
                      {cellContent}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
