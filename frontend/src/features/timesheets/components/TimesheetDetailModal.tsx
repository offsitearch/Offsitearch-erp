import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { AlertCircle, Check, Clock, X } from 'lucide-react';
import {
  approveTimesheetDay,
  getTimesheet,
  rejectTimesheetDay,
  submitTimesheetDay,
} from '../../../api/timesheets';
import { Modal } from '../../../components/Modal';
import { Skeleton } from '../../../components/ui/Skeleton';
import { formatDate, formatDateRange, formatDuration } from '../../../lib/date';
import { STANDARD_WORKDAY_HOURS, timesheetStatusMeta } from '../../../lib/constants';
import { useAuthStore } from '../../../store/authStore';
import type { TimesheetDetail, TimesheetDay } from '../../../lib/types';
import { TimesheetStatusBadge } from './TimesheetStatusBadge';

function dayHours(detail: TimesheetDetail, dateIso: string): number {
  return detail.entries
    .filter((e) => e.date.slice(0, 10) === dateIso)
    .reduce((sum, e) => sum + Number(e.hours), 0);
}

/** Week breakdown for a reviewer (or the owner), with per-day review actions. */
export function TimesheetDetailModal({
  timesheetId,
  onClose,
}: {
  timesheetId: number;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [busyDay, setBusyDay] = useState<string | null>(null);
  const [rejectingDay, setRejectingDay] = useState<string | null>(null);
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);

  const detailQuery = useQuery({
    queryKey: ['timesheets', 'detail', timesheetId],
    queryFn: () => getTimesheet(timesheetId),
  });

  const detail = detailQuery.data;
  const total = detail
    ? detail.entries.reduce((sum, e) => sum + Number(e.hours), 0)
    : 0;
  const isReviewer =
    !!user && !!detail && detail.user_id !== user.id;
  // The approvals page only opens the modal for leads; per-day actions are
  // shown for any submitted day when the viewer isn't the owner.
  const canReview = isReviewer;

  function invalidate() {
    return queryClient.invalidateQueries({ queryKey: ['timesheets'] });
  }

  async function runDayAction(dayIso: string, action: 'submit' | 'approve' | 'reject') {
    if (!detail) return;
    setBusyDay(dayIso);
    setError(null);
    try {
      if (action === 'approve') await approveTimesheetDay(timesheetId, dayIso);
      else if (action === 'reject') await rejectTimesheetDay(timesheetId, dayIso, reason.trim());
      else await submitTimesheetDay(timesheetId, dayIso);
      setRejectingDay(null);
      setReason('');
      await invalidate();
      await detailQuery.refetch();
    } catch (e) {
      setError((e as Error).message || 'Action failed.');
    } finally {
      setBusyDay(null);
    }
  }

  return (
    <Modal onClose={onClose} maxWidth="max-w-2xl">
      <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
        <div>
          <h2 className="text-base font-semibold text-ink">
            {detail ? detail.user_name : 'Timesheet'}
          </h2>
          {detail && (
            <p className="mt-0.5 text-xs tabular-nums text-muted">
              Week {formatDateRange(detail.week_start, detail.week_end)}
              {detail.employee_id ? ` · ${detail.employee_id}` : ''}
            </p>
          )}
        </div>
        <button
          onClick={onClose}
          className="rounded-md p-1.5 text-muted transition hover:bg-surfaceWarm hover:text-ink"
          aria-label="Close"
        >
          ✕
        </button>
      </div>

      {detailQuery.isPending ? (
        <div className="space-y-3 px-5 py-6">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-6 w-full" />
          ))}
        </div>
      ) : detailQuery.isError || !detail ? (
        <div className="flex items-center gap-2 px-5 py-8 text-sm text-danger">
          <AlertCircle className="h-4 w-4" />
          Couldn't load this timesheet.
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-3 border-b border-border px-5 py-3 text-sm">
            <TimesheetStatusBadge status={detail.status} />
            {detail.status === 'submitted' && (
              <span className="flex items-center gap-1.5 text-xs text-warning">
                <Clock className="h-3.5 w-3.5" />
                Submitted {formatDate(detail.submitted_at)}
              </span>
            )}
            {detail.status === 'rejected' && detail.rejection_reason && (
              <span className="text-xs text-danger">Reason: {detail.rejection_reason}</span>
            )}
            {detail.status === 'approved' && detail.approved_by_name && (
              <span className="text-xs text-muted">Approved by {detail.approved_by_name}</span>
            )}
            <span className="ml-auto font-semibold tabular-nums text-ink">
              Total {formatDuration(total)}
            </span>
          </div>

          {/* ── Per-day status strip ── */}
          {detail.days && detail.days.length > 0 && (
            <div className="border-b border-border bg-paper/50 px-5 py-3">
              <p className="pb-2 text-[11px] font-semibold uppercase tracking-wider text-muted">
                Day status
              </p>
              <ul className="flex flex-wrap gap-x-4 gap-y-1.5">
                {detail.days.map((day) => (
                  <DayStatusItem
                    key={day.date}
                    day={day}
                    hours={dayHours(detail, day.date)}
                    canReview={canReview}
                    busy={busyDay === day.date}
                    rejecting={rejectingDay === day.date}
                    reason={reason}
                    error={error}
                    onReasonChange={setReason}
                    onStartReject={() => {
                      setRejectingDay(day.date);
                      setReason('');
                      setError(null);
                    }}
                    onCancelReject={() => setRejectingDay(null)}
                    onApprove={() => void runDayAction(day.date, 'approve')}
                    onConfirmReject={() => void runDayAction(day.date, 'reject')}
                  />
                ))}
              </ul>
            </div>
          )}

          <div className="max-h-[50vh] overflow-y-auto px-5 py-4">
            {error && rejectingDay === null && (
              <div className="mb-3 flex items-center gap-2 rounded-lg border border-danger/30 bg-dangerSoft px-3 py-2 text-xs text-danger">
                <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                {error}
              </div>
            )}
            {detail.entries.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted">No entries this week.</p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="text-[11px] font-semibold uppercase tracking-wider text-muted">
                  <tr>
                    <th className="pb-2 pr-3">Date</th>
                    <th className="pb-2 pr-3">Project / Task</th>
                    <th className="pb-2 pr-3">Notes</th>
                    <th className="pb-2 text-right">Hours</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {detail.entries.map((e) => (
                    <tr key={e.id}>
                      <td className="py-2 pr-3 tabular-nums text-muted">{formatDate(e.date)}</td>
                      <td className="py-2 pr-3">
                        <p className="font-medium text-ink">{e.project_name ?? '—'}</p>
                        {e.task_title && <p className="text-xs text-muted">{e.task_title}</p>}
                      </td>
                      <td className="max-w-[220px] py-2 pr-3 text-xs text-muted">
                        {e.description ?? '—'}
                      </td>
                      <td className="py-2 text-right tabular-nums text-ink">
                        {formatDuration(e.hours)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </Modal>
  );
}

function DayStatusItem({
  day,
  hours,
  canReview,
  busy,
  rejecting,
  reason,
  error,
  onReasonChange,
  onStartReject,
  onCancelReject,
  onApprove,
  onConfirmReject,
}: {
  day: TimesheetDay;
  hours: number;
  canReview: boolean;
  busy: boolean;
  rejecting: boolean;
  reason: string;
  error: string | null;
  onReasonChange: (value: string) => void;
  onStartReject: () => void;
  onCancelReject: () => void;
  onApprove: () => void;
  onConfirmReject: () => void;
}) {
  const meta = timesheetStatusMeta(day.status);
  if (rejecting) {
    return (
      <li className="w-full rounded-lg border border-danger/30 bg-dangerSoft/60 p-2.5">
        <p className="pb-1.5 text-xs font-semibold text-ink">
          Reject {formatDate(day.date)} — reason required
        </p>
        <textarea
          value={reason}
          onChange={(e) => onReasonChange(e.target.value)}
          rows={2}
          maxLength={500}
          placeholder="What should be fixed?"
          className="w-full rounded-md border border-border bg-surface px-2 py-1.5 text-sm text-ink placeholder:text-muted/70 focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30"
        />
        {error && <p className="pt-1 text-xs text-danger">{error}</p>}
        <div className="flex justify-end gap-1.5 pt-1.5">
          <button
            onClick={onCancelReject}
            disabled={busy}
            className="rounded-md px-2 py-1 text-xs font-medium text-muted transition hover:bg-surfaceWarm hover:text-ink"
          >
            Cancel
          </button>
          <button
            onClick={onConfirmReject}
            disabled={busy || reason.trim().length < 3}
            className="inline-flex items-center gap-1 rounded-md bg-danger px-2 py-1 text-xs font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
          >
            <X className="h-3 w-3" />
            Reject day
          </button>
        </div>
      </li>
    );
  }
  return (
    <li className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface py-1 pl-2 pr-1.5 text-xs">
      <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
      <span className="tabular-nums text-ink">{formatDate(day.date)}</span>
      <span className={`rounded-full px-1.5 py-0.5 font-medium ${meta.badge}`}>{meta.label}</span>
      <span className="tabular-nums text-muted">
        {formatDuration(hours)}
        {hours > STANDARD_WORKDAY_HOURS && (
          <span
            title={`Over the standard ${STANDARD_WORKDAY_HOURS}h workday`}
            className="ml-1 font-semibold uppercase text-warning"
          >
            OT
          </span>
        )}
      </span>
      {canReview && day.status === 'submitted' && (
        <>
          <button
            onClick={onApprove}
            disabled={busy}
            title="Approve this day"
            className="rounded-full p-1 text-success transition hover:bg-successSoft disabled:opacity-50"
          >
            <Check className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={onStartReject}
            disabled={busy}
            title="Reject this day"
            className="rounded-full p-1 text-danger transition hover:bg-dangerSoft disabled:opacity-50"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </>
      )}
      {day.status === 'rejected' && day.rejection_reason && (
        <span className="max-w-[160px] truncate text-danger" title={day.rejection_reason}>
          {day.rejection_reason}
        </span>
      )}
    </li>
  );
}
