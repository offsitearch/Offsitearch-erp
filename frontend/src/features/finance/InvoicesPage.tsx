import { useQuery } from '@tanstack/react-query';
import { FilePlus2, Plus } from 'lucide-react';
import { useMemo, useState } from 'react';
import { getInvoices } from '../../api/finance';
import { EmptyState } from '../../components/ui/EmptyState';
import { Skeleton } from '../../components/ui/Skeleton';
import { formatINR, invoiceStatusMeta } from '../../lib/constants';
import { useAuthStore } from '../../store/authStore';
import { FinanceTabs } from './components/FinanceTabs';
import CreateInvoiceModal from './components/CreateInvoiceModal';
import InvoiceDetailModal from './components/InvoiceDetailModal';
import { useTranslation } from 'react-i18next';
import { primaryBtnClass } from '../../lib/styles';

const STATUS_TABS: { key: string; label: string }[] = [
  { key: '', label: 'All' },
  { key: 'draft', label: 'Draft' },
  { key: 'sent', label: 'Sent' },
  { key: 'partial', label: 'Partial' },
  { key: 'paid', label: 'Paid' },
  { key: 'overdue', label: 'Overdue' },
  { key: 'cancelled', label: 'Cancelled' },
];

export default function InvoicesPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const [status, setStatus] = useState('');
  const [creating, setCreating] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const invoices = useQuery({
    queryKey: ['invoices', status],
    queryFn: () => getInvoices(status ? { status } : {}),
  });

  const invoicesByStatus = useMemo(() => {
    const map = new Map<string, number>();
    for (const i of invoices.data ?? []) {
      map.set(i.status, (map.get(i.status) ?? 0) + 1);
    }
    return map;
  }, [invoices.data]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">{t('finance.invoices')}</h1>
           <p className="mt-1 text-sm text-muted">{t('finance.createSendTrack')}</p>
        </div>
        <button onClick={() => setCreating(true)} className={primaryBtnClass}>
          <Plus className="h-4 w-4" /> New Invoice
        </button>
      </div>
      <FinanceTabs level={user?.org_level_code} />

      <div className="flex flex-wrap gap-1.5 rounded-lg border border-border bg-surface p-1">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setStatus(tab.key)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
              status === tab.key ? 'bg-orange text-white' : 'text-muted hover:text-ink'
            }`}
          >
            {tab.label}
            {tab.key !== '' && (
              <span className="ml-1.5 rounded-full bg-white/20 px-1.5 text-xs">
                {invoicesByStatus.get(tab.key) ?? 0}
              </span>
            )}
          </button>
        ))}
      </div>

      {invoices.isPending ? (
        <div className="space-y-2">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-12 w-full rounded-xl" />
          ))}
        </div>
      ) : (invoices.data ?? []).length === 0 ? (
        <EmptyState
          title={t('finance.noInvoicesYet')}
          text={t('finance.createFirst')}
          icon={FilePlus2}
          action={
            <button onClick={() => setCreating(true)} className={primaryBtnClass}>
              <Plus className="h-4 w-4" /> New Invoice
            </button>
          }
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border bg-surface shadow-card">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead>
              <tr className="border-b border-border bg-surfaceWarm text-xs uppercase tracking-wide text-muted">
                <th className="px-4 py-3 font-semibold">Invoice</th>
                <th className="px-4 py-3 font-semibold">Client</th>
                <th className="px-4 py-3 font-semibold">Issued</th>
                <th className="px-4 py-3 font-semibold">Due</th>
                <th className="px-4 py-3 font-semibold text-right">Total</th>
                <th className="px-4 py-3 font-semibold text-right">Paid</th>
                <th className="px-4 py-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {(invoices.data ?? []).map((inv) => {
                const meta = invoiceStatusMeta(inv.status);
                return (
                  <tr
                    key={inv.id}
                    onClick={() => setSelectedId(inv.id)}
                    className="cursor-pointer border-b border-border transition last:border-0 hover:bg-surfaceWarm"
                  >
                    <td className="px-4 py-3 font-semibold text-ink">{inv.invoice_number}</td>
                    <td className="px-4 py-3 text-muted">{inv.client_name ?? '—'}</td>
                    <td className="px-4 py-3 text-muted">{inv.invoice_date}</td>
                    <td className="px-4 py-3 text-muted">{inv.due_date}</td>
                    <td className="px-4 py-3 text-right font-semibold text-ink">{formatINR(inv.total)}</td>
                    <td className="px-4 py-3 text-right text-muted">{formatINR(inv.paid_amount)}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${meta.badge}`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
                        {meta.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {creating && <CreateInvoiceModal onClose={() => setCreating(false)} />}
      {selectedId !== null && (
        <InvoiceDetailModal id={selectedId} onClose={() => setSelectedId(null)} />
      )}
    </div>
  );
}
