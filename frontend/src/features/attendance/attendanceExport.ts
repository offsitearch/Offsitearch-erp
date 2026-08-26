import { ATTENDANCE_METHOD_LABELS, ATTENDANCE_STATUS_META } from '../../lib/constants';
import {
  formatDateRange,
  formatMinutesDuration,
  formatTime,
  weekStartFor,
} from '../../lib/date';
import type { AttendanceStatus, AttendanceUserRow, ReportRow } from '../../lib/types';

const STATUS_ORDER: AttendanceStatus[] = [
  'present',
  'late',
  'half_day',
  'work_from_home',
  'on_leave',
  'absent',
];
const WORKING_STATUSES: AttendanceStatus[] = ['present', 'late', 'half_day', 'work_from_home'];

function csvCell(value: unknown): string {
  const s = value === null || value === undefined ? '' : String(value);
  return `"${s.replace(/"/g, '""')}"`;
}

function downloadCsvFile(header: string[], rows: unknown[][], filename: string): void {
  const lines = [header, ...rows].map((row) => row.map(csvCell).join(','));
  const blob = new Blob([`\uFEFF${lines.join('\n')}`], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function statusCounts(rows: ReportRow[]): Record<AttendanceStatus, number> {
  const counts = Object.fromEntries(STATUS_ORDER.map((s) => [s, 0])) as Record<AttendanceStatus, number>;
  for (const row of rows) counts[row.status] = (counts[row.status] ?? 0) + 1;
  return counts;
}

function sumHours(rows: ReportRow[]): number {
  return rows.reduce((sum, r) => sum + (r.total_hours !== null ? Number(r.total_hours) : 0), 0);
}

function roundHours(value: number): number | '' {
  if (!value) return '';
  return Math.round(value * 100) / 100;
}

function statusLabel(s: AttendanceStatus): string {
  return ATTENDANCE_STATUS_META[s]?.label ?? s;
}

/** Exports one day of attendance (respects the filters applied on screen). */
export function exportDayAttendanceCsv(rows: AttendanceUserRow[], dateISO: string): void {
  const counts = Object.fromEntries(STATUS_ORDER.map((s) => [s, 0])) as Record<AttendanceStatus, number>;
  for (const r of rows) counts[r.status] = (counts[r.status] ?? 0) + 1;
  const totalHours = rows.reduce((sum, r) => sum + (r.total_hours !== null ? Number(r.total_hours) : 0), 0);
  const totalOvertime = rows.reduce((sum, r) => sum + (r.overtime_hours !== null ? Number(r.overtime_hours) : 0), 0);
  const totalLate = rows.reduce((sum, r) => sum + (r.late_minutes || 0), 0);

  const summaryRows: unknown[][] = [
    ['Attendance Report — Day View'],
    [`Date: ${dateISO}`],
    [],
    ['Total Records', rows.length],
    ['Total Hours', `${Math.round(totalHours * 100) / 100}`],
    ['Total Overtime (hrs)', `${Math.round(totalOvertime * 100) / 100}`],
    ['Total Late (mins)', totalLate],
    [],
    ['Status Breakdown'],
    ...STATUS_ORDER.map((s) => [statusLabel(s), counts[s]]),
    [],
    [],
  ];

  const header = [
    'Date',
    'Employee ID',
    'Name',
    'Designation',
    'Department',
    'Status',
    'Check In',
    'Check Out',
    'Late (mins)',
    'Total Hours',
    'Overtime Hours',
    'Check-in Method',
    'Check-in Location',
    'Notes',
  ];
  const body = [...rows]
    .sort((a, b) => a.user_name.localeCompare(b.user_name))
    .map((r) => [
      r.date,
      r.employee_id ?? '',
      r.user_name,
      r.designation ?? '',
      r.department ?? '',
      ATTENDANCE_STATUS_META[r.status]?.label ?? r.status,
      r.check_in_time ? formatTime(r.check_in_time) : '',
      r.check_out_time ? formatTime(r.check_out_time) : '',
      r.late_minutes || '',
      r.total_hours ?? '',
      r.overtime_hours ?? '',
      ATTENDANCE_METHOD_LABELS[r.check_in_method] ?? r.check_in_method,
      r.check_in_location ?? '',
      r.notes ?? '',
    ]);
  downloadCsvFile(
    [],
    [...summaryRows, header, ...body],
    `attendance_${dateISO}.csv`,
  );
  // Overwrite: use header-less approach since downloadCsvFile expects header row
  // Re-implement inline for this special case
  const allLines = [
    ...summaryRows.map((row) => row.map(csvCell).join(',')),
    header.map(csvCell).join(','),
    ...body.map((row) => row.map(csvCell).join(',')),
  ];
  const blob = new Blob([`\uFEFF${allLines.join('\n')}`], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `attendance_${dateISO}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

export type MonthlyExportMode = 'weekly' | 'employee' | 'daily';

/**
 * Exports a summarized month report with title and summary section:
 * - weekly: one row per calendar week (Mon-Sun)
 * - employee: one row per employee with status totals
 * - daily: one row per date
 */
export function exportMonthlyAttendanceCsv(
  rows: ReportRow[],
  opts: { mode: MonthlyExportMode; fromDate: string; toDate: string },
): void {
  const { mode, fromDate, toDate } = opts;

  if (mode === 'employee') {
    const byUser = new Map<number, { name: string; id: string | null; dept: string | null; desig: string | null; rows: ReportRow[] }>();
    for (const r of rows) {
      let entry = byUser.get(r.user_id);
      if (!entry) {
        entry = { name: r.user_name, id: r.employee_id, dept: r.department, desig: r.designation, rows: [] };
        byUser.set(r.user_id, entry);
      }
      entry.rows.push(r);
    }

    const allCounts = statusCounts(rows);
    const totalWorked = WORKING_STATUSES.reduce((sum, s) => sum + allCounts[s], 0);
    const totalHours = sumHours(rows);

    const summaryRows: unknown[][] = [
      ['Attendance Report — Employee Summary'],
      [`Period: ${fromDate} to ${toDate}`],
      [],
      ['Total Employees', byUser.size],
      ['Total Records', rows.length],
      ['Total Worked Days', totalWorked],
      ['Total Hours', roundHours(totalHours)],
      [],
      ['Status Totals'],
      ...STATUS_ORDER.map((s) => [statusLabel(s), allCounts[s]]),
      [],
      [],
    ];

    const header = [
      'Employee ID',
      'Name',
      'Department',
      'Designation',
      ...STATUS_ORDER.map((s) => ATTENDANCE_STATUS_META[s].label),
      'Worked Days',
      'Total Hours',
      'Avg Hours/Worked Day',
      'Total Late',
    ];
    const body = [...byUser.entries()]
      .sort((a, b) => a[1].name.localeCompare(b[1].name))
      .map(([, e]) => {
        const counts = statusCounts(e.rows);
        const worked = WORKING_STATUSES.reduce((sum, s) => sum + counts[s], 0);
        const totalH = sumHours(e.rows);
        const totalLate = e.rows.reduce((sum, r) => sum + (r.late_minutes || 0), 0);
        return [
          e.id ?? '',
          e.name,
          e.dept ?? '',
          e.desig ?? '',
          ...STATUS_ORDER.map((s) => counts[s]),
          worked,
          roundHours(totalH),
          roundHours(worked ? totalH / worked : 0),
          formatMinutesDuration(totalLate),
        ];
      });

    const allLines = [
      ...summaryRows.map((row) => row.map(csvCell).join(',')),
      header.map(csvCell).join(','),
      ...body.map((row) => row.map(csvCell).join(',')),
    ];
    const blob = new Blob([`\uFEFF${allLines.join('\n')}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `attendance_by_employee_${fromDate}_${toDate}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    return;
  }

  if (mode === 'daily') {
    const byDate = new Map<string, ReportRow[]>();
    for (const r of rows) {
      const list = byDate.get(r.date) ?? [];
      list.push(r);
      byDate.set(r.date, list);
    }

    const allCounts = statusCounts(rows);
    const totalHours = sumHours(rows);

    const summaryRows: unknown[][] = [
      ['Attendance Report — Daily Summary'],
      [`Period: ${fromDate} to ${toDate}`],
      [],
      ['Total Days', byDate.size],
      ['Total Records', rows.length],
      ['Total Hours', roundHours(totalHours)],
      [],
      ['Status Totals'],
      ...STATUS_ORDER.map((s) => [statusLabel(s), allCounts[s]]),
      [],
      [],
    ];

    const header = [
      'Date',
      'Day',
      'Records',
      ...STATUS_ORDER.map((s) => ATTENDANCE_STATUS_META[s].label),
      'Worked',
      'Total Hours',
      'Avg Hours/Worked Day',
    ];
    const body = [...byDate.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([iso, dayRows]) => {
        const counts = statusCounts(dayRows);
        const worked = WORKING_STATUSES.reduce((sum, s) => sum + counts[s], 0);
        const totalH = sumHours(dayRows);
        return [
          iso,
          new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN', { weekday: 'short' }),
          dayRows.length,
          ...STATUS_ORDER.map((s) => counts[s]),
          worked,
          roundHours(totalH),
          roundHours(worked ? totalH / worked : 0),
        ];
      });

    const allLines = [
      ...summaryRows.map((row) => row.map(csvCell).join(',')),
      header.map(csvCell).join(','),
      ...body.map((row) => row.map(csvCell).join(',')),
    ];
    const blob = new Blob([`\uFEFF${allLines.join('\n')}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `attendance_daily_summary_${fromDate}_${toDate}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    return;
  }

  // Weekly mode
  const byWeek = new Map<string, { dates: Set<string>; rows: ReportRow[] }>();
  for (const r of rows) {
    const key = weekStartFor(new Date(`${r.date}T00:00:00`));
    let bucket = byWeek.get(key);
    if (!bucket) {
      bucket = { dates: new Set(), rows: [] };
      byWeek.set(key, bucket);
    }
    bucket.dates.add(r.date);
    bucket.rows.push(r);
  }

  const allCounts = statusCounts(rows);
  const totalHours = sumHours(rows);

  const summaryRows: unknown[][] = [
    ['Attendance Report — Weekly Summary'],
    [`Period: ${fromDate} to ${toDate}`],
    [],
    ['Total Weeks', byWeek.size],
    ['Total Records', rows.length],
    ['Total Hours', roundHours(totalHours)],
    [],
    ['Status Totals'],
    ...STATUS_ORDER.map((s) => [statusLabel(s), allCounts[s]]),
    [],
    [],
  ];

  const header = [
    'Week',
    'Date Range',
    'Days Recorded',
    'Records',
    ...STATUS_ORDER.map((s) => ATTENDANCE_STATUS_META[s].label),
    'Worked',
    'Total Hours',
    'Avg Hours/Worked Day',
  ];
  const body = [...byWeek.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([weekStart, bucket], i) => {
      const counts = statusCounts(bucket.rows);
      const worked = WORKING_STATUSES.reduce((sum, s) => sum + counts[s], 0);
      const totalH = sumHours(bucket.rows);
      const dates = [...bucket.dates].sort();
      return [
        `Week ${i + 1} (${new Date(`${weekStart}T00:00:00`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })})`,
        formatDateRange(dates[0], dates[dates.length - 1]),
        bucket.dates.size,
        bucket.rows.length,
        ...STATUS_ORDER.map((s) => counts[s]),
        worked,
        roundHours(totalH),
        roundHours(worked ? totalH / worked : 0),
      ];
    });

  const allLines = [
    ...summaryRows.map((row) => row.map(csvCell).join(',')),
    header.map(csvCell).join(','),
    ...body.map((row) => row.map(csvCell).join(',')),
  ];
  const blob = new Blob([`\uFEFF${allLines.join('\n')}`], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `attendance_weekly_summary_${fromDate}_${toDate}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}
