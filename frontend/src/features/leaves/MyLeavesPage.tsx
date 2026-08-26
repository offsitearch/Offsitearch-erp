import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  CalendarPlus,
  CheckCircle2,
  ChevronDown,
  RefreshCw,
  RotateCcw,
  XCircle,
} from 'lucide-react';
import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { cancelLeave, getLeaveBalances, getMyLeaves } from '../../api/leave';
import { leaveTypeLabel } from '../../lib/constants';
import { formatDate, formatDateRange, formatDayCount, toISODate } from '../../lib/date';
import type { LeaveBalance, LeaveRecord, LeaveType } from '../../lib/types';
import { LogoLoader } from '../../components/LogoLoader';
import { Skeleton } from '../../components/ui/Skeleton';
import { LeaveTabs } from './components/LeaveTabs';
import { LeaveStatusBadge } from './components/LeaveStatusBadge';
import { useTranslation } from 'react-i18next';

const PRIMARY_TYPES: LeaveType[] = ['casual', 'sick', 'earned', 'compensatory'];
const OTHER_TYPES: LeaveType[] = ['maternity', 'paternity', 'work_from_home', 'unpaid'];

function BalanceCard({ row, type }: { row: LeaveBalance | undefined; type: LeaveType }) {
  const { t } = useTranslation();
  const label = leaveTypeLabel(type);
  const available = Number(row?.remaining ?? 0);
  const used = Number(row?.used ?? 0);
  const allocated = Number(row?.allocated ?? 0);
  const pct = allocated > 0 ? Math.round((used / allocated) * 100) : 0;

  return (
    <div className="relative overflow-hidden rounded-xl border border-border bg-surface p-5 shadow-card transition hover:shadow-md">
      {allocated > 0 && available === 0 && (
        <div className="absolute inset-0 bg-graphite/[0.02]" />
      )}
      <div className="relative">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">{label}</p>
        {row ? (
          <>
            <div className="mt-3 flex items-baseline gap-1.5">
              <span className="text-3xl font-bold tracking-tight text-ink">{available}</span>
              <span className="text-xs font-medium text-muted">{available === 1 ? t('leaves.day') : t('leaves.days')}</span>
            </div>
            <p className="mt-0.5 text-xs text-muted">{t('leaves.available')}</p>
            <div className="mt-3 flex items-center gap-3 text-xs text-muted">
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-success" />
                {used} {t('leaves.used')}
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-border" />
                {allocated} {t('leaves.allotted')}
              </span>
            </div>
            {allocated > 0 && (
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-border/60">
                <div
                  className={`h-full rounded-full transition-all ${available > 0 ? 'bg-orange' : 'bg-graphite/30'}`}
                  style={{ width: `${Math.min(pct, 100)}%` }}
                />
              </div>
            )}
          </>
        ) : (
          <>
            <p className="mt-3 text-2xl font-bold tracking-tight text-graphite/40">—</p>
            <p className="mt-1 text-xs text-muted">{t('leaves.notConfigured')}</p>
          </>
        )}
      </div>
    </div>
  );
}

export default function MyLeavesPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const location = useLocation();
  const navigate = useNavigate();
  const year = new Date().getFullYear();
  const today = toISODate(new Date());
  const [cancellingId, setCancellingId] = useState<number | null>(null);

  const notice = (location.state as { leaveNotice?: string } | null)?.leaveNotice ?? null;

  const balances = useQuery({
    queryKey: ['leaves', 'balance', year],
    queryFn: () => getLeaveBalances(year),
  });

  const history = useQuery({
    queryKey: ['leaves', 'mine'],
    queryFn: getMyLeaves,
  });

  const cancelMutation = useMutation({
    mutationFn: cancelLeave,
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ['leaves', 'mine'] }),
        queryClient.invalidateQueries({ queryKey: ['leaves', 'balance'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
      ]),
  });

  function handleCancel(id: number) {
    setCancellingId(id);
    cancelMutation.mutate(id, {
      onSettled: () => setCancellingId(null),
    });
  }

  const balanceMap = new Map((balances.data ?? []).map((b) => [b.leave_type, b]));

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">Leave</h1>
           <p className="mt-1 text-sm text-muted">{t('leaves.trackBalance')}</p>
        </div>
        <LeaveTabs level={user?.org_level_code} />
      </header>

      {notice && (
        <div
          className="flex items-start gap-2 rounded-lg border border-success/25 bg-successSoft px-4 py-3 text-sm text-success"
          role="status"
        >
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{notice}</span>
          <button
            onClick={() => navigate(location.pathname, { replace: true, state: null })}
            className="ml-auto text-xs font-medium underline-offset-2 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ── Primary balance cards ── */}
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-ink">Your balance</h2>
            <p className="mt-0.5 text-xs text-muted">Days available for the {year} calendar year.</p>
          </div>
          <Link
            to="/leaves/apply"
            className="inline-flex h-9 items-center justify-center gap-2 rounded-md bg-orange px-3.5 text-sm font-medium text-white transition hover:bg-orangeDark focus:outline-none focus:ring-2 focus:ring-orange/50"
          >
            <CalendarPlus className="h-4 w-4" />
            Apply
          </Link>
        </div>

        {balances.isPending ? (
          <LogoLoader />
        ) : balances.isError ? (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border px-4 py-10 text-center">
            <AlertCircle className="h-6 w-6 text-danger" />
            <p className="text-sm font-medium text-ink">Couldn't load leave balances.</p>
            <button
              onClick={() => balances.refetch()}
              className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 text-sm font-medium text-ink transition hover:bg-surfaceWarm"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {PRIMARY_TYPES.map((type) => (
              <BalanceCard key={type} type={type} row={balanceMap.get(type)} />
            ))}
          </div>
        )}
      </section>

      {/* ── Other leave types ── */}
      <details className="group rounded-xl border border-border bg-surface shadow-card">
        <summary className="flex cursor-pointer items-center justify-between gap-3 px-5 py-4 text-sm font-semibold text-ink select-none">
          <span>Other leave types</span>
          <ChevronDown className="h-4 w-4 text-muted transition group-open:rotate-180" />
        </summary>
        <div className="grid grid-cols-1 gap-4 border-t border-border px-5 py-5 sm:grid-cols-2 lg:grid-cols-4">
          {OTHER_TYPES.map((type) => (
            <BalanceCard key={type} type={type} row={balanceMap.get(type)} />
          ))}
        </div>
      </details>

      {/* ── Leave history ── */}
      <section className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
        <div className="border-b border-border px-5 py-4">
          <h2 className="text-sm font-semibold text-ink">{t('leaves.leaveHistory')}</h2>
          <p className="mt-0.5 text-xs text-muted">{t('leaves.everyRequest')}</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left text-sm">
            <thead className="border-b border-border bg-paper/60 text-[11px] font-semibold uppercase tracking-wider text-muted">
              <tr>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Dates</th>
                <th className="px-4 py-3">Days</th>
                <th className="px-4 py-3">Reason</th>
                <th className="px-4 py-3">Submitted</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {history.isPending ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8">
                    <div className="space-y-3">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <Skeleton key={i} className="h-5 w-full" />
                      ))}
                    </div>
                  </td>
                </tr>
              ) : history.isError ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12">
                    <div className="flex flex-col items-center gap-3 text-center">
                      <AlertCircle className="h-6 w-6 text-danger" />
                      <p className="text-sm font-medium text-ink">Couldn't load leave history.</p>
                      <button
                        onClick={() => history.refetch()}
                        className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 text-sm font-medium text-ink transition hover:bg-surfaceWarm"
                      >
                        <RefreshCw className="h-3.5 w-3.5" />
                        Retry
                      </button>
                    </div>
                  </td>
                </tr>
              ) : history.data?.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center">
                    <CalendarPlus className="mx-auto h-8 w-8 text-border" />
                    <p className="mt-2 text-sm font-medium text-ink">{t('leaves.noLeaveRequests')}</p>
                    <p className="mt-0.5 text-xs text-muted">{t('leaves.submittedWillAppear')}</p>
                    <Link
                      to="/leaves/apply"
                      className="inline-flex h-9 items-center justify-center gap-2 rounded-md bg-orange px-3.5 mt-4 text-sm font-medium text-white transition hover:bg-orangeDark"
                    >
                      <CalendarPlus className="h-4 w-4" />
                      {t('leaves.applyForLeave')}
                    </Link>
                  </td>
                </tr>
              ) : (
                history.data?.map((leave: LeaveRecord) => (
                  <tr key={leave.id} className="transition hover:bg-surfaceWarm">
                    <td className="px-4 py-3 font-medium text-ink">{leaveTypeLabel(leave.leave_type)}</td>
                    <td className="px-4 py-3 text-muted">{formatDateRange(leave.from_date, leave.to_date)}</td>
                    <td className="px-4 py-3 tabular-nums text-muted">{formatDayCount(leave.total_days)}</td>
                    <td className="max-w-xs truncate px-4 py-3 text-muted">{leave.reason ?? '—'}</td>
                    <td className="px-4 py-3 text-muted">{formatDate(leave.created_at)}</td>
                    <td className="px-4 py-3">
                      <LeaveStatusBadge status={leave.status} />
                      {(leave.status === 'approved' || leave.status === 'rejected') && leave.approved_at && (
                        <p className="mt-1 text-xs text-muted">Reviewed {formatDate(leave.approved_at)}</p>
                      )}
                      {leave.status === 'rejected' && leave.rejection_reason && (
                        <p className="mt-1 max-w-[220px] text-xs text-muted">
                          <span className="font-medium">Reason:</span> {leave.rejection_reason}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {leave.status === 'pending' && leave.from_date >= today ? (
                        <button
                          onClick={() => handleCancel(leave.id)}
                          disabled={cancellingId === leave.id}
                          title="Cancel request"
                          className="inline-flex h-8 items-center justify-center gap-1 rounded-md border border-border bg-surface px-2.5 text-xs font-medium text-muted transition hover:bg-dangerSoft hover:text-danger disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          <XCircle className="h-3.5 w-3.5" />
                          {cancellingId === leave.id ? 'Cancelling…' : 'Cancel'}
                        </button>
                      ) : leave.status === 'rejected' ? (
                        <button
                          onClick={() =>
                            navigate('/leaves/apply', {
                              state: {
                                prefill: {
                                  leave_type: leave.leave_type,
                                  from_date: leave.from_date,
                                  to_date: leave.to_date,
                                  duration: leave.half_day_first
                                    ? 'first'
                                    : leave.half_day_second
                                      ? 'second'
                                      : 'full',
                                  reason: leave.reason ?? '',
                                },
                              },
                            })
                          }
                          title="Re-apply with the same details"
                          className="inline-flex h-8 items-center justify-center gap-1 rounded-md border border-border bg-surface px-2.5 text-xs font-medium text-muted transition hover:bg-surfaceWarm"
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                          Apply again
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
