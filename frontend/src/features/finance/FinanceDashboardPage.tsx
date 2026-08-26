import { useQuery } from '@tanstack/react-query';
import { Banknote, FileText, IndianRupee, Receipt, TrendingUp } from 'lucide-react';
import { useMemo, useState } from 'react';
import { getFinanceOverview } from '../../api/finance';
import { LogoLoader } from '../../components/LogoLoader';
import { formatINR } from '../../lib/constants';
import type { FinanceOverview } from '../../lib/types';
import { useAuthStore } from '../../store/authStore';
import { FinanceTabs } from './components/FinanceTabs';
import { useTranslation } from 'react-i18next';

type PeriodKey = 'month' | 'quarter' | 'year' | 'all';

const PERIODS: { key: PeriodKey; label: string }[] = [
  { key: 'month', label: 'This Month' },
  { key: 'quarter', label: 'This Quarter' },
  { key: 'year', label: 'This Year' },
  { key: 'all', label: 'All Time' },
];

const PERIOD_LABELS: Record<PeriodKey, string> = {
  month: 'month',
  quarter: 'quarter',
  year: 'year',
  all: 'all',
};

function KpiCard({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string;
  icon: typeof IndianRupee;
  tone: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted">{label}</p>
        <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${tone}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <p className="mt-2 text-2xl font-bold text-ink">{value}</p>
    </div>
  );
}

export default function FinanceDashboardPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const [period, setPeriod] = useState<PeriodKey>('month');

  const overviews = useQuery({
    queryKey: ['finance-overview'],
    queryFn: async () => {
      const [month, quarter, year, all] = await Promise.all(
        PERIODS.map((p) => getFinanceOverview(p.key)),
      );
      return { month, quarter, year, all } as Record<PeriodKey, FinanceOverview>;
    },
  });

  const chartData = useMemo(() => {
    if (!overviews.data) return [];
    return PERIODS.map((p) => ({
      label: p.label,
      received: Number(overviews.data[p.key].received),
      invoiced: Number(overviews.data[p.key].invoiced),
      expenses: Number(overviews.data[p.key].expenses),
      profit: Number(overviews.data[p.key].profit),
    }));
  }, [overviews.data]);

  const maxBar = Math.max(1, ...chartData.map((d) => d.invoiced));

  if (overviews.isPending) {
    return <LogoLoader />;
  }

  const current = overviews.data?.[period];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">{t('finance.dashboard')}</h1>
          <p className="mt-1 text-sm text-muted">
            {t('finance.revenueFor', { period: t('finance.' + PERIOD_LABELS[period]) })}.
          </p>
        </div>
        <div className="flex gap-1.5 rounded-lg border border-border bg-surface p-1">
          {PERIODS.map((p) => (
            <button
              key={p.key}
              onClick={() => setPeriod(p.key)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
                period === p.key ? 'bg-orange text-white' : 'text-muted hover:text-ink'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
      <FinanceTabs level={user?.org_level_code} />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Invoiced" value={formatINR(current?.invoiced)} icon={FileText} tone="bg-infoSoft text-info" />
        <KpiCard label="Received" value={formatINR(current?.received)} icon={Banknote} tone="bg-successSoft text-success" />
        <KpiCard label="Outstanding" value={formatINR(current?.outstanding)} icon={TrendingUp} tone="bg-warningSoft text-warning" />
        <KpiCard label="Expenses" value={formatINR(current?.expenses)} icon={Receipt} tone="bg-dangerSoft text-danger" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-border bg-surface p-5 shadow-card lg:col-span-2">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-ink">{t('finance.collectionsVsExpenses')}</h2>
              <p className="text-xs text-muted">{t('finance.acrossPeriods')}</p>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="inline-flex items-center gap-1.5 text-muted">
                <span className="h-2.5 w-2.5 rounded-full bg-orange" /> Received
              </span>
              <span className="inline-flex items-center gap-1.5 text-muted">
                <span className="h-2.5 w-2.5 rounded-full bg-danger/50" /> Expenses
              </span>
            </div>
          </div>
          <div className="mt-6 flex h-52 items-end justify-around gap-6">
            {chartData.map((d) => (
              <div key={d.label} className="flex flex-1 flex-col items-center gap-2">
                <div className="flex h-40 w-full items-end justify-center gap-1.5">
                  <div
                    className="w-1/2 max-w-10 rounded-t-md bg-orange transition-all"
                    style={{ height: `${Math.max(4, (d.received / maxBar) * 100)}%` }}
                    title={`Received: ${formatINR(d.received)}`}
                  />
                  <div
                    className="w-1/2 max-w-10 rounded-t-md bg-danger/40 transition-all"
                    style={{ height: `${Math.max(4, (d.expenses / maxBar) * 100)}%` }}
                    title={`Expenses: ${formatINR(d.expenses)}`}
                  />
                </div>
                <span className="text-xs font-medium text-muted">{d.label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-ink">{t('finance.profit')}</h2>
              <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${Number(current?.profit) >= 0 ? 'bg-successSoft text-success' : 'bg-dangerSoft text-danger'}`}>
                <IndianRupee className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold text-ink">{formatINR(current?.profit)}</p>
            <p className="mt-1 text-xs text-muted">
              {Number(current?.profit) >= 0 ? 'After approved expenses' : 'Expenses exceed collections'}
            </p>
          </div>

          <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
            <h2 className="text-base font-bold text-ink">{t('finance.invoiceHealth')}</h2>
            <div className="mt-4 space-y-3">
              <Row label="Invoices" value={current?.invoice_count ?? 0} tone="text-info" />
              <Row label="Paid in full" value={current?.paid_count ?? 0} tone="text-success" />
              <Row label="Overdue" value={current?.overdue_count ?? 0} tone="text-danger" />
              <Row label="Approved expenses" value={current?.expense_count ?? 0} tone="text-warning" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted">{label}</span>
      <span className={`font-bold ${tone}`}>{value}</span>
    </div>
  );
}
