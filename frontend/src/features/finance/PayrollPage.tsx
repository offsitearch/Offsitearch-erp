import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, Download, Loader2, Play, X } from 'lucide-react';
import { useMemo, useState } from 'react';
import { downloadPayslip, getPayroll, processPayroll } from '../../api/finance';
import { LogoLoader } from '../../components/LogoLoader';
import { useToast } from '../../components/Toast';
import { formatINR, payrollStatusMeta } from '../../lib/constants';
import { useAuthStore } from '../../store/authStore';
import { FinanceTabs } from './components/FinanceTabs';
import { useTranslation } from 'react-i18next';
import { primaryBtnClass, secondaryBtnClass } from '../../lib/styles';

function errDetail(err: unknown): string | null {
  return (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? null;
}

export default function PayrollPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [key, setKey] = useState(() => {
    const now = new Date();
    return { month: now.getMonth() + 1, year: now.getFullYear() };
  });
  const [confirmProcess, setConfirmProcess] = useState(false);

  const payroll = useQuery({
    queryKey: ['payroll', key.year, key.month],
    queryFn: () => getPayroll(key.month, key.year),
  });

  const process = useMutation({
    mutationFn: () => processPayroll(key.month, key.year),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payroll', key.year, key.month] });
      queryClient.invalidateQueries({ queryKey: ['finance-overview'] });
      toast(t('finance.payrollProcessed'), 'success');
      setConfirmProcess(false);
    },
    onError: (err) => {
      toast(errDetail(err) ?? 'Failed to process payroll', 'error');
    },
  });

  function shift(delta: number) {
    setKey((prev) => {
      const total = prev.year * 12 + (prev.month - 1) + delta;
      return { year: Math.floor(total / 12), month: (total % 12) + 1 };
    });
  }

  const run = payroll.data;
  const meta = payrollStatusMeta(run?.status ?? 'draft');
  const totalPay = useMemo(
    () => (run?.entries ?? []).reduce((sum, e) => sum + Number(e.net_pay), 0),
    [run],
  );
  const totalDays = useMemo(
    () => (run?.entries ?? []).reduce((sum, e) => sum + e.working_days, 0),
    [run],
  );

  const monthName = new Date(key.year, key.month - 1, 1).toLocaleDateString('en-IN', {
    month: 'long',
    year: 'numeric',
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">{t('finance.payroll')}</h1>
          <p className="mt-1 text-sm text-muted">
            {t('finance.payrollSubtitle')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => shift(-1)}
            className="rounded-lg border border-border bg-surface p-2 text-muted transition hover:bg-surfaceWarm"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="rounded-lg border border-border bg-surface px-4 py-2 text-sm font-semibold text-ink">
            {monthName}
          </span>
          <button
            onClick={() => shift(1)}
            className="rounded-lg border border-border bg-surface p-2 text-muted transition hover:bg-surfaceWarm"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
      <FinanceTabs level={user?.org_level_code} />

      {payroll.isPending ? (
        <LogoLoader />
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4">
            <SummaryCard label={t('finance.statusLabel')} value={meta.label} badge={meta.badge} />
            <SummaryCard label={t('finance.netPayout')} value={formatINR(totalPay)} />
            <SummaryCard label={t('finance.totalWorkingDays')} value={String(totalDays)} />
          </div>

          <div className="overflow-x-auto rounded-xl border border-border bg-surface shadow-card">
            <div className="flex items-center justify-between border-b border-border px-5 py-3">
              <p className="text-sm font-semibold text-ink">
                {run?.is_preview ? t('finance.preview') : t('finance.processedRun')}
              </p>
              {run && !run.is_preview && run.processed_at && (
                <p className="text-xs text-muted">
                  Processed on {new Date(run.processed_at).toLocaleString()}
                </p>
              )}
            </div>
            <table className="w-full min-w-[700px] text-left text-sm">
              <thead>
                <tr className="border-b border-border bg-surfaceWarm text-xs uppercase tracking-wide text-muted">
                  <th className="px-4 py-3 font-semibold">{t('employees.title')}</th>
                  <th className="px-4 py-3 font-semibold">{t('employees.designation')}</th>
                  <th className="px-4 py-3 font-semibold text-center">{t('finance.days')}</th>
                  <th className="px-4 py-3 font-semibold text-right">{t('finance.gross')}</th>
                  <th className="px-4 py-3 font-semibold text-right">{t('finance.deductions')}</th>
                  <th className="px-4 py-3 font-semibold text-right">{t('finance.netPay')}</th>
                  <th className="px-4 py-3 font-semibold text-right">{t('finance.payslip')}</th>
                </tr>
              </thead>
              <tbody>
                {(run?.entries ?? []).map((entry) => (
                  <tr key={entry.user_id} className="border-b border-border last:border-0 hover:bg-surfaceWarm">
                    <td className="px-4 py-3">
                      <p className="font-semibold text-ink">{entry.user_name ?? 'Employee'}</p>
                      <p className="text-xs text-muted">{entry.employee_id ?? ''}</p>
                    </td>
                    <td className="px-4 py-3 text-muted">{entry.designation ?? '—'}</td>
                    <td className="px-4 py-3 text-center font-medium text-ink">{entry.working_days}</td>
                    <td className="px-4 py-3 text-right text-ink">{formatINR(entry.gross_salary)}</td>
                    <td className="px-4 py-3 text-right text-danger">{formatINR(entry.deductions)}</td>
                    <td className="px-4 py-3 text-right font-bold text-ink">{formatINR(entry.net_pay)}</td>
                    <td className="px-4 py-3 text-right">
                      {run?.is_preview ? (
                        <span className="text-xs text-muted">—</span>
                      ) : (
                        <PayslipButton userId={entry.user_id} month={key.month} year={key.year} />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {run && (run.entries ?? []).length === 0 && (
              <div className="px-5 py-10 text-center text-sm text-muted">
                {t('finance.noSalariedEmployees')}
              </div>
            )}
          </div>

          {run && !run.is_preview && run.processed_at && (
            <div className="rounded-lg bg-successSoft px-4 py-3 text-sm text-success">
              Payroll has been processed for {monthName}. Payslips are ready for download.
            </div>
          )}

          {run && run.is_preview && (
            <div className="flex items-center justify-between rounded-lg bg-navy/10 px-4 py-3 text-sm text-navy">
              <span>
                This is a preview for {monthName}. Processing locks in the numbers and generates
                payslips.
              </span>
              <button onClick={() => setConfirmProcess(true)} className={primaryBtnClass}>
                <Play className="h-4 w-4" /> Process payroll
              </button>
            </div>
          )}

          {errDetail(process.error) && (
            <div className="rounded-lg bg-dangerSoft px-4 py-3 text-sm text-danger">
              {errDetail(process.error)}
            </div>
          )}

          {confirmProcess && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
              <div className="max-h-[90vh] w-full max-w-sm overflow-y-auto rounded-xl bg-surface p-6 shadow-overlay">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-ink">Process payroll</h3>
                  <button onClick={() => setConfirmProcess(false)} aria-label="Close" className="rounded-lg p-1 text-muted hover:bg-surfaceWarm">
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <p className="mt-3 text-sm text-muted">
                  Process payroll for {monthName}? Net payout is{' '}
                  <b className="text-ink">{formatINR(totalPay)}</b>. This cannot be undone for the
                  month.
                </p>
                <div className="mt-4 flex justify-end gap-2">
                  <button onClick={() => setConfirmProcess(false)} className={secondaryBtnClass}>
                    Cancel
                  </button>
                  <button
                    onClick={() => process.mutate()}
                    disabled={process.isPending}
                    className={primaryBtnClass}
                  >
                    {process.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                    Confirm
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function SummaryCard({ label, value, badge }: { label: string; value: string; badge?: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
      <p className="text-sm text-muted">{label}</p>
      {badge ? (
        <span className={`mt-2 inline-block rounded-full px-2.5 py-1 text-sm font-semibold ${badge}`}>
          {value}
        </span>
      ) : (
        <p className="mt-1 text-2xl font-bold text-ink">{value}</p>
      )}
    </div>
  );
}

function PayslipButton({ userId, month, year }: { userId: number; month: number; year: number }) {
  const { t } = useTranslation();
  const download = useMutation({
    mutationFn: () => downloadPayslip(userId, month, year),
  });
  return (
    <button
      onClick={() => download.mutate()}
      disabled={download.isPending}
      title={t('finance.downloadPayslip')}
      className="rounded-lg p-1.5 text-muted transition hover:bg-surfaceWarm disabled:opacity-50"
    >
      {download.isPending ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Download className="h-4 w-4" />
      )}
    </button>
  );
}
