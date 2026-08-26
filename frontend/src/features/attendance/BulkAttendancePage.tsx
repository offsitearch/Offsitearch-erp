import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';
import { bulkMark, listUsers } from '../../api/attendance';
import { ATTENDANCE_STATUS_META, ATTENDANCE_STATUS_OPTIONS } from '../../lib/constants';
import { toISODate } from '../../lib/date';
import type { AttendanceStatus } from '../../lib/types';
import { Skeleton } from '../../components/ui/Skeleton';
import DatePicker from '../../components/ui/DatePicker';
import TimeInput from '../../components/ui/TimeInput';
import { useTranslation } from 'react-i18next';
import { selectClass, primaryBtnClass, secondaryBtnClass } from '../../lib/styles';

interface TimeEntry {
  check_in: string;
  check_out: string;
}

function toISOFromLocal(dtLocal: string): string | null {
  if (!dtLocal) return null;
  const d = new Date(dtLocal);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

export default function BulkAttendancePage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [date, setDate] = useState(() => toISODate(new Date()));
  const [departmentId, setDepartmentId] = useState<number | ''>('');
  const [statuses, setStatuses] = useState<Record<number, string>>({});
  const [times, setTimes] = useState<Record<number, TimeEntry>>({});
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [message, setMessage] = useState<{ kind: 'success' | 'error'; text: string } | null>(null);

  const users = useQuery({
    queryKey: ['users', 'all'],
    queryFn: () => listUsers(),
  });

  useEffect(() => {
    if (!message || message.kind !== 'success') return;
    const id = window.setTimeout(() => setMessage(null), 6000);
    return () => window.clearTimeout(id);
  }, [message]);

  const departments = users.data
    ? Array.from(
        new Map(
          users.data
            .filter((u) => u.department_id != null)
            .map((u) => [u.department_id as number, u.department ?? '']),
        ).entries(),
      )
    : [];

  const departmentUsers = (users.data ?? []).filter(
    (u) => departmentId === '' || u.department_id === departmentId,
  );

  const dirty = departmentUsers.some(
    (u) =>
      (statuses[u.id] ?? 'present') !== 'present' ||
      times[u.id]?.check_in ||
      times[u.id]?.check_out,
  );

  const mutation = useMutation({
    mutationFn: () =>
      bulkMark(
        date,
        departmentUsers.map((u) => {
          const t = times[u.id];
          return {
            user_id: u.id,
            status: statuses[u.id] ?? 'present',
            check_in_time: t?.check_in ? toISOFromLocal(t.check_in) : undefined,
            check_out_time: t?.check_out ? toISOFromLocal(t.check_out) : undefined,
          };
        }),
      ),
    onSuccess: () => {
      setConfirmOpen(false);
      setMessage({
        kind: 'success',
        text: `Attendance saved for ${departmentUsers.length} ${
          departmentUsers.length === 1 ? 'employee' : 'employees'
        } on ${date}.`,
      });
      queryClient.invalidateQueries({ queryKey: ['attendance'] });
    },
    onError: () => setMessage({ kind: 'error', text: "Couldn't save attendance. Please try again." }),
  });

  function setAllPresent() {
    setStatuses(Object.fromEntries(departmentUsers.map((u) => [u.id, 'present'])));
  }

  function handleDateChange(value: string) {
    setDate(value);
    setStatuses({});
    setTimes({});
    setConfirmOpen(false);
  }

  function handleDepartmentChange(value: string) {
    setDepartmentId(value === '' ? '' : Number(value));
    setStatuses({});
    setTimes({});
    setConfirmOpen(false);
  }

  function setTimeField(userId: number, field: 'check_in' | 'check_out', value: string) {
    setTimes((prev) => ({
      ...prev,
      [userId]: { ...prev[userId], [field]: value },
    }));
  }

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">Attendance</h1>
           <p className="mt-1 text-sm text-muted">{t('attendance.markAttendance')}</p>
        </div>
      </header>

      <div className="flex flex-wrap items-end gap-3">
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-muted">Date</span>
          <DatePicker value={date} onChange={handleDateChange} className="w-44" />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-muted">Department</span>
          <select
            value={departmentId}
            onChange={(e) => handleDepartmentChange(e.target.value)}
            className={selectClass}
          >
            <option value="">{t('attendance.allDepartments')}</option>
            {departments.map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <button onClick={setAllPresent} disabled={departmentUsers.length === 0} className={secondaryBtnClass}>
          Set all present
        </button>
        <button
          onClick={() => (dirty ? setConfirmOpen(true) : mutation.mutate())}
          disabled={mutation.isPending || departmentUsers.length === 0}
          className={primaryBtnClass}
        >
          {mutation.isPending ? t('attendance.saving') : `${t('attendance.saveCount', { count: departmentUsers.length })}`}
        </button>
        {dirty && !confirmOpen && !mutation.isPending && (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-warning/40 bg-warningSoft px-2.5 py-1 text-xs font-medium text-warning">
            <AlertCircle className="h-3.5 w-3.5" />
            Unsaved changes
          </span>
        )}
      </div>

      {confirmOpen && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-warning/40 bg-warningSoft px-4 py-3">
          <p className="text-sm text-warning">
            {t('attendance.confirmSave')}{' '}
            <span className="font-semibold">{departmentUsers.length}</span> {t('attendance.employeeCount')}{' '}
            <span className="font-semibold">{date}</span>.
          </p>
          <div className="flex gap-2">
            <button onClick={() => setConfirmOpen(false)} disabled={mutation.isPending} className={secondaryBtnClass}>
              Cancel
            </button>
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className={primaryBtnClass}
            >
              {mutation.isPending ? t('attendance.saving') : t('attendance.confirmAndSave')}
            </button>
          </div>
        </div>
      )}

      {message && (
        <div
          className={`flex items-start gap-2 rounded-md px-3 py-2.5 text-sm ${
            message.kind === 'success' ? 'bg-successSoft text-success' : 'bg-dangerSoft text-danger'
          }`}
          role="status"
        >
          {message.kind === 'success' ? (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          ) : (
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          )}
          <span>{message.text}</span>
          {message.kind === 'error' && (
            <button
              onClick={() => setMessage(null)}
              className="ml-auto shrink-0 text-xs font-medium underline-offset-2 hover:underline"
            >
              Dismiss
            </button>
          )}
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-border bg-surface shadow-card">
        <table className="w-full min-w-[600px] text-left text-sm">
          <thead className="border-b border-border bg-paper/60 text-[11px] font-semibold uppercase tracking-wider text-muted">
            <tr>
              <th className="px-4 py-3">Employee</th>
              <th className="px-4 py-3">Department</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Check-in</th>
              <th className="px-4 py-3">Check-out</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {users.isPending ? (
              <tr>
                <td colSpan={5} className="px-4 py-8">
                  <div className="space-y-3">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Skeleton key={i} className="h-5 w-full" />
                    ))}
                  </div>
                </td>
              </tr>
            ) : users.isError ? (
              <tr>
                <td colSpan={5} className="px-4 py-12">
                  <div className="flex flex-col items-center gap-3 text-center">
                    <AlertCircle className="h-6 w-6 text-danger" />
                    <div>
                      <p className="text-sm font-medium text-ink">{t('attendance.couldntLoadEmployees')}</p>
                      <p className="mt-0.5 text-xs text-muted">
                        {t('attendance.couldntRetrieveList')}
                      </p>
                    </div>
                    <button onClick={() => users.refetch()} className={secondaryBtnClass}>
                      <RefreshCw className="h-3.5 w-3.5" />
                      Retry
                    </button>
                  </div>
                </td>
              </tr>
            ) : departmentUsers.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center">
                   <p className="text-sm font-medium text-ink">{t('attendance.noEmployeesFound')}</p>
                   <p className="mt-0.5 text-xs text-muted">{t('attendance.selectDepartment')}</p>
                </td>
              </tr>
            ) : departmentUsers.map((u) => {
                const status = (statuses[u.id] ?? 'present') as AttendanceStatus;
                const tint = status !== 'present' ? ATTENDANCE_STATUS_META[status].cell : '';
                const t = times[u.id];
                return (
                  <tr key={u.id} className={`transition hover:bg-surfaceWarm ${tint}`}>
                    <td className="px-4 py-3">
                      <p className="font-medium text-ink">{u.name}</p>
                      <p className="text-xs text-muted">{u.employee_id ?? '—'}</p>
                    </td>
                    <td className="px-4 py-3 text-muted">{u.department ?? '—'}</td>
                    <td className="px-4 py-3">
                      <select
                        value={status}
                        onChange={(e) => setStatuses((prev) => ({ ...prev, [u.id]: e.target.value }))}
                        className={selectClass}
                      >
                        {ATTENDANCE_STATUS_OPTIONS.map((s) => (
                          <option key={s} value={s}>
                            {ATTENDANCE_STATUS_META[s].label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <TimeInput
                        value={t?.check_in?.slice(11, 16) ?? ''}
                        onChange={(time) => setTimeField(u.id, 'check_in', time ? `${date}T${time}` : '')}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <TimeInput
                        value={t?.check_out?.slice(11, 16) ?? ''}
                        onChange={(time) => setTimeField(u.id, 'check_out', time ? `${date}T${time}` : '')}
                      />
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
