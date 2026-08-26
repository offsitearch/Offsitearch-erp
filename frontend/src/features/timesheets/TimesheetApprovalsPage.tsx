import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Check, Eye, X } from 'lucide-react';
import { useState } from 'react';
import {
  approveTimesheet,
  getAllTimesheets,
  getPendingTimesheets,
  rejectTimesheet,
} from '../../api/timesheets';
import { Skeleton } from '../../components/ui/Skeleton';
import { formatDate, formatDateRange, formatDuration } from '../../lib/date';
import type { TimesheetStatus } from '../../lib/types';
import { useAuthStore } from '../../store/authStore';
import { selectClass } from '../../lib/styles';
import { TimesheetDetailModal } from './components/TimesheetDetailModal';
import { TimesheetStatusBadge } from './components/TimesheetStatusBadge';
import { TimesheetTabs } from './components/TimesheetTabs';

const STATUS_FILTERS: Array<{ value: string; label: string }> = [
  { value: '', label: 'All statuses' },
  { value: 'draft', label: 'Draft' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
];

export default function TimesheetApprovalsPage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">Timesheets</h1>
          <p className="mt-1 text-sm text-muted">Review your team's submitted weekly hours.</p>
        </div>
        <TimesheetTabs level={user?.org_level_code} />
      </header>

      <PendingQueue />

      <AllTimesheetsTable />
    </div>
  );
}

function PendingQueue() {
  const queryClient = useQueryClient();
  const [detailId, setDetailId] = useState<number | null>(null);
  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectError, setRejectError] = useState<string | null>(null);

  const pendingQuery = useQuery({
    queryKey: ['timesheets', 'pending'],
    queryFn: () => getPendingTimesheets(),
  });

  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['timesheets'] }),
      queryClient.invalidateQueries({ queryKey: ['projects'] }),
      queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
    ]);

  const approveMutation = useMutation({
    mutationFn: approveTimesheet,
    onSuccess: invalidate,
  });
  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) => rejectTimesheet(id, reason),
    onSuccess: () => {
      invalidate();
      setRejectReason('');
    },
  });

  function confirmReject(id: number) {
    if (rejectReason.trim().length < 3) {
      setRejectError('A short reason is required to reject a timesheet.');
      return;
    }
    setRejectError(null);
    rejectMutation.mutate(
      { id, reason: rejectReason.trim() },
      { onSettled: () => setRejectingId(null) },
    );
  }

  const pendingCount = pendingQuery.data?.total ?? 0;

  return (
    <section className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold text-ink">Pending approvals</h2>
          <p className="mt-0.5 text-xs text-muted">Submitted weeks waiting for review.</p>
        </div>
        {pendingCount > 0 && (
          <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-warning/15 px-2 text-xs font-bold tabular-nums text-warning">
            {pendingCount}
          </span>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[880px] text-left text-sm">
          <thead className="border-b border-border bg-paper/60 text-[11px] font-semibold uppercase tracking-wider text-muted">
            <tr>
              <th className="px-4 py-3">Employee</th>
              <th className="px-4 py-3">Department</th>
              <th className="px-4 py-3">Week</th>
              <th className="px-4 py-3">Hours</th>
              <th className="px-4 py-3">Entries</th>
              <th className="px-4 py-3">Submitted</th>
              <th className="px-4 py-3">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {pendingQuery.isPending ? (
              <tr>
                <td colSpan={7} className="px-4 py-8">
                  <Skeleton className="h-5 w-full" />
                </td>
              </tr>
            ) : pendingQuery.isError ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-sm text-danger">
                  Couldn't load pending approvals.
                </td>
              </tr>
            ) : (pendingQuery.data?.items.length ?? 0) === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center">
                  <Check className="mx-auto h-8 w-8 text-success/50" />
                  <p className="mt-2 text-sm font-medium text-ink">No timesheets to review</p>
                  <p className="mt-0.5 text-xs text-muted">You're all caught up.</p>
                </td>
              </tr>
            ) : (
              pendingQuery.data!.items.map((row) => (
                <tr key={row.id} className="transition hover:bg-surfaceWarm">
                  <td className="px-4 py-3">
                    <p className="font-medium text-ink">{row.user_name}</p>
                    <p className="text-xs text-muted">{row.employee_id ?? '—'}</p>
                  </td>
                  <td className="px-4 py-3 text-muted">{row.department ?? '—'}</td>
                  <td className="px-4 py-3 tabular-nums text-muted">
                    {formatDateRange(row.week_start, row.week_end)}
                  </td>
                  <td className="px-4 py-3 font-medium tabular-nums text-ink">
                    {formatDuration(row.total_hours)}
                  </td>
                  <td className="px-4 py-3 tabular-nums text-muted">{row.entry_count}</td>
                  <td className="px-4 py-3 text-muted">{formatDate(row.submitted_at)}</td>
                  <td className="px-4 py-3">
                    {rejectingId === row.id ? (
                      <div className="flex flex-wrap items-center gap-2">
                        <input
                          autoFocus
                          value={rejectReason}
                          onChange={(e) => setRejectReason(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && confirmReject(row.id)}
                          placeholder="Reason"
                          className="h-8 w-44 rounded-md border border-border bg-surface px-2 text-xs text-ink transition focus:border-danger focus:outline-none focus:ring-2 focus:ring-danger/30"
                        />
                        <button
                          onClick={() => confirmReject(row.id)}
                          disabled={rejectMutation.isPending}
                          className="inline-flex items-center gap-1 rounded-md bg-danger px-2.5 py-1.5 text-xs font-semibold text-white transition hover:bg-danger/90 disabled:opacity-60"
                        >
                          <X className="h-3.5 w-3.5" />
                          Reject
                        </button>
                        <button
                          onClick={() => {
                            setRejectingId(null);
                            setRejectReason('');
                            setRejectError(null);
                          }}
                          className="text-xs font-medium text-muted transition hover:text-ink"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setDetailId(row.id)}
                          title="View details"
                          className="inline-flex items-center gap-1 rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs font-medium text-muted transition hover:bg-surfaceWarm hover:text-ink"
                        >
                          <Eye className="h-3.5 w-3.5" />
                          Details
                        </button>
                        <button
                          onClick={() => approveMutation.mutate(row.id)}
                          disabled={approveMutation.isPending}
                          className="inline-flex items-center gap-1 rounded-md bg-success px-2.5 py-1.5 text-xs font-semibold text-white transition hover:bg-success/90 disabled:opacity-60"
                        >
                          <Check className="h-3.5 w-3.5" />
                          Approve
                        </button>
                        <button
                          onClick={() => setRejectingId(row.id)}
                          className="inline-flex items-center gap-1 rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs font-medium text-muted transition hover:bg-dangerSoft hover:text-danger"
                        >
                          <X className="h-3.5 w-3.5" />
                          Reject
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {rejectError && (
        <div className="mx-5 mb-4 flex items-start gap-2 rounded-lg border border-danger/30 bg-dangerSoft px-4 py-3 text-sm text-danger">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{rejectError}</span>
        </div>
      )}

      {(approveMutation.isError || rejectMutation.isError) && (
        <div className="mx-5 mb-4 flex items-start gap-2 rounded-lg border border-danger/30 bg-dangerSoft px-4 py-3 text-sm text-danger">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            {(approveMutation.error as Error | null)?.message ??
              (rejectMutation.error as Error | null)?.message ??
              'Something went wrong.'}
          </span>
        </div>
      )}

      {detailId !== null && <TimesheetDetailModal timesheetId={detailId} onClose={() => setDetailId(null)} />}
    </section>
  );
}

function AllTimesheetsTable() {
  const [statusFilter, setStatusFilter] = useState('');

  const allQuery = useQuery({
    queryKey: ['timesheets', 'all', statusFilter],
    queryFn: () => getAllTimesheets({ status: statusFilter || undefined, page_size: 50 }),
  });

  return (
    <section className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold text-ink">All timesheets</h2>
          <p className="mt-0.5 text-xs text-muted">Every week sheet across the studio (latest 50).</p>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label="Filter by status"
          className={`${selectClass} h-9 w-44 text-xs`}
        >
          {STATUS_FILTERS.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </select>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[880px] text-left text-sm">
          <thead className="border-b border-border bg-paper/60 text-[11px] font-semibold uppercase tracking-wider text-muted">
            <tr>
              <th className="px-4 py-3">Employee</th>
              <th className="px-4 py-3">Week</th>
              <th className="px-4 py-3">Hours</th>
              <th className="px-4 py-3">Submitted</th>
              <th className="px-4 py-3">Reviewed by</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {allQuery.isPending ? (
              <tr>
                <td colSpan={6} className="px-4 py-8">
                  <Skeleton className="h-5 w-full" />
                </td>
              </tr>
            ) : allQuery.isError ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-sm text-danger">
                  Couldn't load timesheets.
                </td>
              </tr>
            ) : (allQuery.data?.items.length ?? 0) === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-sm text-muted">
                  Nothing matches this filter yet.
                </td>
              </tr>
            ) : (
              allQuery.data!.items.map((row) => (
                <tr key={row.id} className="transition hover:bg-surfaceWarm">
                  <td className="px-4 py-3">
                    <p className="font-medium text-ink">{row.user_name}</p>
                    <p className="text-xs text-muted">{row.employee_id ?? '—'}</p>
                  </td>
                  <td className="px-4 py-3 tabular-nums text-muted">
                    {formatDateRange(row.week_start, row.week_end)}
                  </td>
                  <td className="px-4 py-3 font-medium tabular-nums text-ink">
                    {formatDuration(row.total_hours)}
                  </td>
                  <td className="px-4 py-3 text-muted">{formatDate(row.submitted_at)}</td>
                  <td className="px-4 py-3 text-muted">{row.approved_by_name ?? '—'}</td>
                  <td className="px-4 py-3">
                    <TimesheetStatusBadge status={row.status as TimesheetStatus} />
                    {row.status === 'rejected' && row.rejection_reason && (
                      <p className="mt-1 max-w-[240px] text-xs text-muted">
                        <span className="font-medium">Reason:</span> {row.rejection_reason}
                      </p>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
