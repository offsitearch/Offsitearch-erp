import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Download, Pencil, RefreshCw, X } from 'lucide-react';
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { getDateAttendance, listUsers, updateAttendance } from '../../api/attendance';
import { downloadReportXlsx } from '../../api/attendance';
import { ATTENDANCE_METHOD_LABELS, ATTENDANCE_STATUS_META, ATTENDANCE_STATUS_OPTIONS, canAccess } from '../../lib/constants';
import { formatDate, formatDuration, formatTime, toISODate } from '../../lib/date';
import type { AttendanceUserRow } from '../../lib/types';
import { StatusBadge } from './components/StatusBadge';
import { Skeleton } from '../../components/ui/Skeleton';
import DatePicker from '../../components/ui/DatePicker';
import TimeInput from '../../components/ui/TimeInput';
import { useTranslation } from 'react-i18next';
import { inputClass, secondaryBtnClass } from '../../lib/styles';

function toDateTimeLocal(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hh = String(d.getHours()).padStart(2, '0');
  const mi = String(d.getMinutes()).padStart(2, '0');
  return `${y}-${m}-${day}T${hh}:${mi}`;
}

function toISOFromLocal(dtLocal: string): string | null {
  if (!dtLocal) return null;
  const d = new Date(dtLocal);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

function methodDetail(row: AttendanceUserRow): string | null {
  const method = ATTENDANCE_METHOD_LABELS[row.check_in_method] ?? row.check_in_method;
  if (!row.check_in_location) return method === 'Web' ? null : method;
  return `${method} · ${row.check_in_location}`;
}

function EditAttendanceModal({
  record,
  onClose,
  onSaved,
}: {
  record: AttendanceUserRow;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const [status, setStatus] = useState(record.status);
  const [checkIn, setCheckIn] = useState(toDateTimeLocal(record.check_in_time));
  const [checkOut, setCheckOut] = useState(toDateTimeLocal(record.check_out_time));
  const [notes, setNotes] = useState(record.notes ?? '');
  const [error, setError] = useState<string | null>(null);

  const saveMutation = useMutation({
    mutationFn: () =>
      updateAttendance(record.id, {
        status,
        check_in_time: toISOFromLocal(checkIn),
        check_out_time: toISOFromLocal(checkOut),
        notes: notes.trim() || null,
      }),
    onSuccess: () => {
      onSaved();
      onClose();
    },
    onError: () => setError("Couldn't update this record. Please try again."),
  });

  const labelClass = 'mb-1 block text-xs font-medium text-muted';
  const fieldClass = `${inputClass} h-auto py-2`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
      <div
        className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-lg border border-border bg-surface p-6 shadow-overlay"
        onKeyDown={(e) => {
          if (e.key === 'Escape' && saveMutation.isPending) {
            e.preventDefault();
            e.stopPropagation();
          }
        }}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-ink">{t('attendance.editAttendance')}</h2>
            <p className="mt-0.5 text-sm text-muted">
              {record.user_name} · {formatDate(record.date)}
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={saveMutation.isPending}
            aria-label="Close"
            className="rounded-md p-1 text-muted transition hover:bg-surfaceWarm hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <form
          className="mt-4 space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            saveMutation.mutate();
          }}
        >
          <label className="block">
            <span className={labelClass}>{t('attendance.status')}</span>
            <select value={status} onChange={(e) => setStatus(e.target.value as AttendanceUserRow['status'])} className={fieldClass}>
              {ATTENDANCE_STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {ATTENDANCE_STATUS_META[s].label}
                </option>
              ))}
            </select>
          </label>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={labelClass}>Check-in time</span>
              <div className="flex gap-2">
                <DatePicker
                  value={checkIn.slice(0, 10)}
                  onChange={(d) => setCheckIn(`${d}T${checkIn.slice(11, 16) || '09:00'}`)}
                />
                <TimeInput
                  value={checkIn.slice(11, 16)}
                  onChange={(t) => setCheckIn(`${checkIn.slice(0, 10) || record.date}T${t}`)}
                  className="w-28 shrink-0"
                />
              </div>
            </label>
            <label className="block">
              <span className={labelClass}>Check-out time</span>
              <div className="flex gap-2">
                <DatePicker
                  value={checkOut.slice(0, 10)}
                  onChange={(d) => setCheckOut(`${d}T${checkOut.slice(11, 16) || '18:00'}`)}
                />
                <TimeInput
                  value={checkOut.slice(11, 16)}
                  onChange={(t) => setCheckOut(`${checkOut.slice(0, 10) || record.date}T${t}`)}
                  className="w-28 shrink-0"
                />
              </div>
            </label>
          </div>
          <label className="block">
            <span className={labelClass}>Notes</span>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Reason, correction note, etc."
              className={fieldClass}
            />
          </label>
          {error && (
            <div className="rounded-md border border-danger/30 bg-dangerSoft px-3 py-2.5 text-sm text-danger">
              {error}
            </div>
          )}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} disabled={saveMutation.isPending} className={secondaryBtnClass}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={saveMutation.isPending}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-orange px-4 text-sm font-medium text-white transition hover:bg-orangeDark focus:outline-none focus:ring-2 focus:ring-orange/50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saveMutation.isPending ? 'Saving…' : 'Save changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function TodayAttendancePage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const isAdmin = canAccess(user?.org_level_code, 'L2');
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const [date, setDate] = useState(() => searchParams.get('date') || toISODate(new Date()));
  const [departmentId, setDepartmentId] = useState<number | ''>('');
  const [status, setStatus] = useState<string>('');
  const [editing, setEditing] = useState<AttendanceUserRow | null>(null);

  const users = useQuery({ queryKey: ['users', 'all'], queryFn: () => listUsers() });

  const departments = users.data
    ? Array.from(
        new Map(
          users.data
            .filter((u) => u.department_id != null)
            .map((u) => [u.department_id as number, u.department ?? '']),
        ).entries(),
      )
    : [];

  const rows = useQuery({
    queryKey: ['attendance', 'date', date, departmentId, status],
    queryFn: () => getDateAttendance(date, departmentId === '' ? null : departmentId, status || null),
  });

  const onSaved = () => {
    queryClient.invalidateQueries({ queryKey: ['attendance', 'date'] });
    queryClient.invalidateQueries({ queryKey: ['attendance', 'today'] });
    queryClient.invalidateQueries({ queryKey: ['attendance', 'report'] });
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
  };

  const counts = rows.data
    ? ATTENDANCE_STATUS_OPTIONS.map((s) => ({
        status: s,
        meta: ATTENDANCE_STATUS_META[s],
        count: rows.data.filter((r) => r.status === s).length,
      }))
    : [];

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">{t('attendance.title')}</h1>
           <p className="mt-1 text-sm text-muted">{t('attendance.seeWhoCheckedIn')}</p>
        </div>
      </header>

      <div className="flex flex-wrap items-end gap-3">
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-muted">{t('attendance.date')}</span>
          <DatePicker value={date} onChange={setDate} className="w-44" />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-muted">{t('attendance.department')}</span>
          <select
            value={departmentId}
            onChange={(e) => setDepartmentId(e.target.value === '' ? '' : Number(e.target.value))}
            className={inputClass}
          >
            <option value="">{t('attendance.allDepartments')}</option>
            {departments.map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-muted">{t('attendance.status')}</span>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className={inputClass}
          >
            <option value="">{t('attendance.allStatuses')}</option>
            {ATTENDANCE_STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {ATTENDANCE_STATUS_META[s].label}
              </option>
            ))}
          </select>
        </label>
        {isAdmin && (
          <button
            onClick={() => downloadReportXlsx(date, date)}
            disabled={rows.isPending || !rows.data?.length}
            className={secondaryBtnClass}
          >
            <Download className="h-4 w-4" />
            Open in Sheets
          </button>
        )}
      </div>

      {rows.data && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 py-1 text-xs font-medium text-ink">
            {rows.data.length} {rows.data.length === 1 ? 'Employee' : 'Employees'}
          </span>
          {counts.map(({ status: s, meta, count }) => (
            <span
              key={s}
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${meta.badge}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
              {meta.label}
              <span className="font-semibold tabular-nums">{count}</span>
            </span>
          ))}
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-border bg-surface shadow-card">
        <table className="w-full min-w-[700px] text-left text-sm">
          <thead className="border-b border-border bg-paper/60 text-[11px] font-semibold uppercase tracking-wider text-muted">
            <tr>
              <th className="px-4 py-3">{t('attendance.employee')}</th>
              <th className="px-4 py-3">Department</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">{t('attendance.checkInTime')}</th>
              <th className="px-4 py-3">{t('attendance.checkOutTime')}</th>
              <th className="px-4 py-3 text-right">{t('attendance.late')}</th>
              <th className="px-4 py-3 text-right">{t('attendance.hours')}</th>
              <th className="px-4 py-3 text-right">OT</th>
              <th className="px-4 py-3" aria-label="Edit" />
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.isPending ? (
              <tr>
                <td colSpan={8} className="px-4 py-8">
                  <div className="space-y-3">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Skeleton key={i} className="h-5 w-full" />
                    ))}
                  </div>
                </td>
              </tr>
            ) : rows.isError ? (
              <tr>
                <td colSpan={8} className="px-4 py-12">
                  <div className="flex flex-col items-center gap-3 text-center">
                    <AlertCircle className="h-6 w-6 text-danger" />
                    <p className="text-sm font-medium text-ink">{t('attendance.couldntLoadDay')}</p>
                    <button onClick={() => rows.refetch()} className={secondaryBtnClass}>
                      <RefreshCw className="h-3.5 w-3.5" />
                      Retry
                    </button>
                  </div>
                </td>
              </tr>
            ) : rows.data?.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center">
                   <p className="text-sm font-medium text-ink">{t('attendance.noAttendanceForDay')}</p>
                   <p className="mt-0.5 text-xs text-muted">{t('attendance.tryDifferentDate')}</p>
                </td>
              </tr>
            ) : (
              rows.data?.map((row) => (
                <tr key={row.id} className="transition hover:bg-surfaceWarm">
                  <td className="px-4 py-3">
                    <p className="font-medium text-ink">{row.user_name}</p>
                    <p className="text-xs text-muted">{row.employee_id ?? '—'}</p>
                  </td>
                  <td className="px-4 py-3 text-muted">{row.department ?? '—'}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={row.status} />
                  </td>
                  <td className="px-4 py-3">
                    <span className="block tabular-nums text-muted">{formatTime(row.check_in_time)}</span>
                    {methodDetail(row) && (
                      <span className="block text-[11px] text-muted">{methodDetail(row)}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 tabular-nums text-muted">{formatTime(row.check_out_time)}</td>
                  <td className="px-4 py-3 text-right tabular-nums text-muted">
                    {row.late_minutes ? `${row.late_minutes}m` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-ink">
                    {formatDuration(row.total_hours) || '—'}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-warning">
                    {Number(row.overtime_hours ?? 0) > 0 ? formatDuration(row.overtime_hours) : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {isAdmin && (
                      <button
                        onClick={() => setEditing(row)}
                        aria-label={`Edit attendance for ${row.user_name}`}
                        title="Edit record"
                        className="rounded-md p-1.5 text-muted transition hover:bg-surfaceWarm hover:text-orange focus:outline-none focus-visible:ring-2 focus-visible:ring-navy/40"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {editing && (
        <EditAttendanceModal record={editing} onClose={() => setEditing(null)} onSaved={onSaved} />
      )}
    </div>
  );
}
