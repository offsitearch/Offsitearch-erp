import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, CalendarPlus, CheckCircle2, RotateCcw } from 'lucide-react';
import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { applyLeave, getLeaveBalances } from '../../api/leave';
import { leaveTypeLabel, LEAVE_TYPE_OPTIONS } from '../../lib/constants';
import { toISODate } from '../../lib/date';
import type { LeaveType } from '../../lib/types';
import { LeaveTabs } from './components/LeaveTabs';
import DatePicker from '../../components/ui/DatePicker';
import { useTranslation } from 'react-i18next';
import { inputClass, secondaryBtnClass, primaryBtnClass } from '../../lib/styles';

const fullWidthInput = `${inputClass} w-full`;

const DURATIONS = [
  { value: 'full' as const, label: 'Full day' },
  { value: 'first' as const, label: 'First half' },
  { value: 'second' as const, label: 'Second half' },
];

interface ApplyPrefill {
  leave_type: LeaveType;
  from_date: string;
  to_date: string;
  duration: 'full' | 'first' | 'second';
  reason: string;
}

export default function ApplyLeavePage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const today = toISODate(new Date());

  const prefill = (location.state as { prefill?: ApplyPrefill } | null)?.prefill;

  const [leaveType, setLeaveType] = useState<LeaveType>(prefill?.leave_type ?? 'casual');
  const [fromDate, setFromDate] = useState(prefill?.from_date ?? today);
  const [toDate, setToDate] = useState(prefill?.to_date ?? today);
  const [duration, setDuration] = useState<'full' | 'first' | 'second'>(prefill?.duration ?? 'full');
  const [reason, setReason] = useState(prefill?.reason ?? '');
  const [error, setError] = useState<string | null>(null);

  const year = new Date(fromDate).getFullYear();
  const balances = useQuery({
    queryKey: ['leaves', 'balance', year],
    queryFn: () => getLeaveBalances(year),
  });
  const currentBalance = balances.data?.find((b) => b.leave_type === leaveType);
  const remaining = Number(currentBalance?.remaining ?? 0);

  const mutation = useMutation({
    mutationFn: applyLeave,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leaves'] });
      navigate('/leaves/my', { state: { leaveNotice: 'Leave request submitted.' } });
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail ?? t('leaves.failedToApply'));
    },
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (toDate < fromDate) {
      setError(t('leaves.toMustBeAfterFrom'));
      return;
    }
    mutation.mutate({
      leave_type: leaveType,
      from_date: fromDate,
      to_date: toDate,
      half_day_first: duration === 'first',
      half_day_second: duration === 'second',
      reason: reason || undefined,
    });
  }

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">{t('leaves.title')}</h1>
           <p className="mt-1 text-sm text-muted">{t('leaves.applySubtitle')}</p>
        </div>
        <LeaveTabs level={user?.org_level_code} />
      </header>

      <section className="max-w-2xl rounded-xl border border-border bg-surface p-6 shadow-card">
        <div className="mb-5 border-b border-border pb-4">
          <h2 className="text-base font-semibold tracking-tight text-ink">{t('leaves.applyLeaveTitle')}</h2>
          <p className="mt-0.5 text-xs text-muted">
            {t('leaves.workingDaysAuto')}
          </p>
        </div>

        {prefill && (
          <div className="mb-5 flex items-start gap-2 rounded-md border border-navy/15 bg-paper px-4 py-3 text-sm">
            <RotateCcw className="mt-0.5 h-4 w-4 shrink-0 text-navy" />
            <span className="text-ink">
              {t('leaves.reapplying')} — your previous details are pre-filled. Adjust and resubmit.
            </span>
          </div>
        )}

        {currentBalance &&
          (remaining > 0 ? (
            <div className="mb-5 rounded-md border border-navy/15 bg-paper px-4 py-3 text-sm">
              <p className="text-ink">
                {leaveTypeLabel(leaveType)} ·{' '}
                <span className="font-semibold">{t('leaves.daysAvailable', { count: remaining })}</span>
              </p>
              <p className="mt-0.5 text-xs text-muted">
                {t('leaves.usedOfAllotted', { used: currentBalance.used, allocated: currentBalance.allocated })}
              </p>
            </div>
          ) : (
            <div className="mb-5 flex items-start gap-2 rounded-md border border-warning/30 bg-warningSoft px-4 py-3 text-sm text-warning">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                No {leaveTypeLabel(leaveType)} is currently available. Choose another type or adjust your dates.
              </span>
            </div>
          ))}

        <form onSubmit={submit} className="space-y-4">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-muted">{t('leaves.leaveType')}</span>
            <select value={leaveType} onChange={(e) => setLeaveType(e.target.value as LeaveType)} className={fullWidthInput}>
              {LEAVE_TYPE_OPTIONS.map((type) => (
                <option key={type} value={type}>
                  {leaveTypeLabel(type)}
                </option>
              ))}
            </select>
          </label>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-muted">{t('leaves.from')}</span>
              <DatePicker value={fromDate} onChange={setFromDate} min={today} />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-muted">{t('leaves.to')}</span>
              <DatePicker value={toDate} onChange={setToDate} min={fromDate} />
            </label>
          </div>

          <fieldset>
            <legend className="mb-1 block text-xs font-medium text-muted">{t('leaves.duration')}</legend>
            <div className="flex flex-wrap gap-4">
              {DURATIONS.map((d) => (
                <label key={d.value} className="flex items-center gap-2 text-sm text-ink">
                  <input
                    type="radio"
                    name="duration"
                    checked={duration === d.value}
                    onChange={() => setDuration(d.value)}
                    className="h-4 w-4 accent-orange"
                  />
                  {d.label}
                </label>
              ))}
            </div>
          </fieldset>

          <label className="block">
            <span className="mb-1 block text-xs font-medium text-muted">{t('leaves.reason')}</span>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              placeholder={t('leaves.whyNeedLeave')}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink transition focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30"
            />
          </label>

          {error && (
            <div className="flex items-start gap-2 rounded-md border border-danger/30 bg-dangerSoft px-4 py-3 text-sm text-danger">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3 border-t border-border pt-4">
            <Link to="/leaves/my" className={secondaryBtnClass}>
              Cancel
            </Link>
            <button type="submit" disabled={mutation.isPending} className={primaryBtnClass}>
              {mutation.isPending ? (
                <>
                  <CheckCircle2 className="h-4 w-4 animate-pulse" />
                  Submitting…
                </>
              ) : (
                <>
                  <CalendarPlus className="h-4 w-4" />
                  Submit Request
                </>
              )}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
