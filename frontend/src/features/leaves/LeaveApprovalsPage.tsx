import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Check, RefreshCw, X } from 'lucide-react';
import { useState } from 'react';
import { useAuthStore } from '../../store/authStore';
import { approveLeave, getPendingLeaves, getTeamAvailability, rejectLeave } from '../../api/leave';
import { leaveTypeLabel } from '../../lib/constants';
import { formatDate, formatDateRange, formatDayCount, toISODate } from '../../lib/date';
import { Skeleton } from '../../components/ui/Skeleton';
import { LeaveTabs } from './components/LeaveTabs';
import { LeaveStatusBadge } from './components/LeaveStatusBadge';
import { useTranslation } from 'react-i18next';

export default function LeaveApprovalsPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectError, setRejectError] = useState<string | null>(null);

  const now = new Date();
  const quarterFrom = toISODate(new Date(now.getFullYear(), now.getMonth(), 1));
  const quarterTo = toISODate(new Date(now.getFullYear(), now.getMonth() + 2, 0));

  const pending = useQuery({
    queryKey: ['leaves', 'pending'],
    queryFn: getPendingLeaves,
  });

  const availability = useQuery({
    queryKey: ['leaves', 'team-availability', quarterFrom, quarterTo],
    queryFn: () => getTeamAvailability(quarterFrom, quarterTo),
  });

  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['leaves', 'pending'] }),
      queryClient.invalidateQueries({ queryKey: ['leaves', 'team-availability'] }),
      queryClient.invalidateQueries({ queryKey: ['leaves', 'balance'] }),
      queryClient.invalidateQueries({ queryKey: ['attendance'] }),
      queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
    ]);

  const approveMutation = useMutation({ mutationFn: approveLeave, onSuccess: invalidate });
  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) => rejectLeave(id, reason),
    onSuccess: invalidate,
  });

  function confirmReject(id: number) {
    if (!rejectReason.trim()) {
      setRejectError('A reason is required to reject a leave.');
      return;
    }
    setRejectError(null);
    rejectMutation.mutate({ id, reason: rejectReason.trim() });
    setRejectingId(null);
    setRejectReason('');
  }

  const pendingCount = pending.data?.length ?? 0;

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">Leave</h1>
           <p className="mt-1 text-sm text-muted">{t('leaves.approveRejectPending')}</p>
        </div>
        <LeaveTabs level={user?.org_level_code} />
      </header>

      {/* ── Pending approvals ── */}
      <section className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-ink">Pending approvals</h2>
            <p className="mt-0.5 text-xs text-muted">Requests waiting for your review, newest first.</p>
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
                <th className="px-4 py-3">Leave</th>
                <th className="px-4 py-3">Dates</th>
                <th className="px-4 py-3">Days</th>
                <th className="px-4 py-3">Reason</th>
                <th className="px-4 py-3">Requested</th>
                <th className="px-4 py-3">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {pending.isPending ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8">
                    <div className="space-y-3">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <Skeleton key={i} className="h-5 w-full" />
                      ))}
                    </div>
                  </td>
                </tr>
              ) : pending.isError ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12">
                    <div className="flex flex-col items-center gap-3 text-center">
                      <AlertCircle className="h-6 w-6 text-danger" />
                      <p className="text-sm font-medium text-ink">Couldn't load pending approvals.</p>
                      <button
                        onClick={() => pending.refetch()}
                        className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 text-sm font-medium text-ink transition hover:bg-surfaceWarm"
                      >
                        <RefreshCw className="h-3.5 w-3.5" />
                        Retry
                      </button>
                    </div>
                  </td>
                </tr>
              ) : pending.data?.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center">
                    <Check className="mx-auto h-8 w-8 text-success/50" />
                    <p className="mt-2 text-sm font-medium text-ink">{t('leaves.noPendingApprovals')}</p>
                    <p className="mt-0.5 text-xs text-muted">{t('leaves.allCaughtUp')}</p>
                  </td>
                </tr>
              ) : (
                pending.data?.map((leave) => (
                  <tr key={leave.id} className="transition hover:bg-surfaceWarm">
                    <td className="px-4 py-3">
                      <p className="font-medium text-ink">{leave.user_name}</p>
                      <p className="text-xs text-muted">{leave.employee_id ?? '—'}</p>
                    </td>
                    <td className="px-4 py-3 text-muted">{leave.department ?? '—'}</td>
                    <td className="px-4 py-3 font-medium text-ink">{leaveTypeLabel(leave.leave_type)}</td>
                    <td className="px-4 py-3 text-muted">{formatDateRange(leave.from_date, leave.to_date)}</td>
                    <td className="px-4 py-3 tabular-nums text-muted">{formatDayCount(leave.total_days)}</td>
                    <td className="max-w-xs truncate px-4 py-3 text-muted">{leave.reason ?? '—'}</td>
                    <td className="px-4 py-3 text-muted">{formatDate(leave.created_at)}</td>
                    <td className="px-4 py-3">
                      {rejectingId === leave.id ? (
                        <div className="flex items-center gap-2">
                          <input
                            autoFocus
                            value={rejectReason}
                            onChange={(e) => setRejectReason(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && confirmReject(leave.id)}
                            placeholder="Reason"
                            className="h-8 w-40 rounded-md border border-border bg-surface px-2 text-xs text-ink transition focus:border-danger focus:outline-none focus:ring-2 focus:ring-danger/30"
                          />
                          <button
                            onClick={() => confirmReject(leave.id)}
                            disabled={rejectMutation.isPending}
                            className="inline-flex items-center gap-1 rounded-md bg-danger px-2.5 py-1.5 text-xs font-semibold text-white transition hover:bg-danger/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-danger/40 disabled:opacity-60"
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
                            onClick={() => approveMutation.mutate(leave.id)}
                            disabled={approveMutation.isPending}
                            title="Approve"
                            className="inline-flex items-center gap-1 rounded-md bg-success px-2.5 py-1.5 text-xs font-semibold text-white transition hover:bg-success/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-success/40 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            <Check className="h-3.5 w-3.5" />
                            {t('leaves.approve')}
                          </button>
                          <button
                            onClick={() => setRejectingId(leave.id)}
                            title={t('leaves.reject')}
                            className="inline-flex items-center gap-1 rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs font-medium text-muted transition hover:bg-dangerSoft hover:text-danger focus:outline-none focus-visible:ring-2 focus-visible:ring-navy/40"
                          >
                            <X className="h-3.5 w-3.5" />
                            {t('leaves.reject')}
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
      </section>

      {rejectError && (
        <div className="flex items-start gap-2 rounded-lg border border-danger/30 bg-dangerSoft px-4 py-3 text-sm text-danger">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{rejectError}</span>
        </div>
      )}

      {/* ── Team availability ── */}
      <section className="rounded-xl border border-border bg-surface shadow-card">
        <div className="border-b border-border px-5 py-4">
          <h2 className="text-sm font-semibold text-ink">{t('leaves.teamAvailability')}</h2>
           <p className="mt-0.5 text-xs text-muted">{t('leaves.whoIsOut')}</p>
        </div>
        <div className="p-5">
          {availability.isPending ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full rounded-lg" />
              ))}
            </div>
          ) : availability.isError ? (
            <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border px-4 py-8 text-center">
              <AlertCircle className="h-6 w-6 text-danger" />
              <p className="text-sm font-medium text-ink">Couldn't load team availability.</p>
              <button
                onClick={() => availability.refetch()}
                className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 text-sm font-medium text-ink transition hover:bg-surfaceWarm"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Retry
              </button>
            </div>
          ) : availability.data?.length === 0 ? (
            <div className="rounded-lg bg-paper px-4 py-6 text-center">
              <p className="text-sm text-muted">No leaves in this period.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {availability.data?.map((row, index) => (
                <div
                  key={index}
                  className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 rounded-lg border border-border bg-paper px-4 py-3 transition hover:shadow-sm"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-navy/10 text-xs font-bold text-navy">
                      {row.user_name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-ink">{row.user_name}</p>
                      <p className="text-xs text-muted">{row.department ?? '—'}</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-sm">
                    <span className="text-muted">{leaveTypeLabel(row.leave_type)}</span>
                    <span className="text-xs tabular-nums text-muted">{formatDateRange(row.from_date, row.to_date)}</span>
                    <LeaveStatusBadge status={row.status} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
