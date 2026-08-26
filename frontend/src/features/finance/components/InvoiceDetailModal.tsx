import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, Loader2, Send, Wallet, X } from 'lucide-react';
import { useState } from 'react';
import { downloadInvoicePdf, getInvoice, recordInvoicePayment, sendInvoice } from '../../../api/finance';
import { Modal } from '../../../components/Modal';
import { Skeleton } from '../../../components/ui/Skeleton';
import { formatINR, invoiceStatusMeta, paymentMethodLabel } from '../../../lib/constants';
import type { PaymentMethod } from '../../../lib/types';
import RecordPaymentModal from './RecordPaymentModal';

function errDetail(err: unknown): string | null {
  return (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? null;
}

function ActionButton({
  onClick,
  pending,
  icon,
  label,
  outline,
}: {
  onClick: () => void;
  pending: boolean;
  icon: React.ReactNode;
  label: string;
  outline?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={pending}
      className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition disabled:opacity-50 ${
        outline
          ? 'border border-border bg-surface text-muted hover:bg-surfaceWarm'
          : 'bg-orange text-white hover:bg-orangeDark'
      }`}
    >
      {pending ? <Loader2 className="h-4 w-4 animate-spin" /> : icon}
      {label}
    </button>
  );
}

export default function InvoiceDetailModal({ id, onClose }: { id: number; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [payment, setPayment] = useState(false);

  const invoice = useQuery({ queryKey: ['invoice', id], queryFn: () => getInvoice(id) });

  const send = useMutation({
    mutationFn: () => sendInvoice(id),
    onSuccess: invalidate,
  });
  const pay = useMutation({
    mutationFn: (payload: { amount: number; payment_date: string; method: PaymentMethod }) =>
      recordInvoicePayment(id, payload),
    onSuccess: () => {
      invalidate();
      setPayment(false);
    },
  });
  const pdf = useMutation({ mutationFn: () => downloadInvoicePdf(id) });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['invoice', id] });
    queryClient.invalidateQueries({ queryKey: ['invoices'] });
    queryClient.invalidateQueries({ queryKey: ['finance-overview'] });
  }

  if (invoice.isPending) {
    return (
      <Modal onClose={onClose} maxWidth="max-w-2xl">
        <Skeleton className="h-80 rounded-xl" />
      </Modal>
    );
  }

  const inv = invoice.data!;
  const meta = invoiceStatusMeta(inv.status);
  const outstanding = Number(inv.total) - Number(inv.paid_amount);

  return (
    <Modal onClose={onClose} maxWidth="max-w-2xl">
      <div className="p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-bold text-ink">{inv.invoice_number}</h2>
              <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${meta.badge}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
                {meta.label}
              </span>
            </div>
            <p className="mt-0.5 text-sm text-muted">
              {inv.client_name ?? 'Client'} {inv.project_code ? `· ${inv.project_code}` : ''}
            </p>
          </div>
          <button onClick={onClose} aria-label="Close" className="rounded-lg p-1 text-muted hover:bg-surfaceWarm">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-3 rounded-lg bg-surfaceWarm p-4 text-sm">
          <div>
            <p className="text-xs text-muted">Issued</p>
            <p className="font-semibold text-ink">{inv.invoice_date}</p>
          </div>
          <div>
            <p className="text-xs text-muted">Due</p>
            <p className="font-semibold text-ink">{inv.due_date}</p>
          </div>
          <div>
            <p className="text-xs text-muted">Last payment</p>
            <p className="font-semibold text-ink">{inv.payment_date ? `${inv.payment_date} (${paymentMethodLabel(inv.payment_method)})` : '—'}</p>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto rounded-lg border border-border">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-border bg-surfaceWarm text-xs uppercase tracking-wide text-muted">
                <th className="px-4 py-2 font-semibold">Description</th>
                <th className="px-3 py-2 font-semibold">HSN/SAC</th>
                <th className="px-3 py-2 text-right font-semibold">Qty</th>
                <th className="px-3 py-2 text-right font-semibold">Rate</th>
                <th className="px-4 py-2 text-right font-semibold">Amount</th>
              </tr>
            </thead>
            <tbody>
              {inv.items.map((item) => (
                <tr key={item.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-2 text-ink">{item.description}</td>
                  <td className="px-3 py-2 text-muted">{item.hsn_sac || '—'}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-ink">
                    {Number(item.quantity)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-ink">{formatINR(item.rate)}</td>
                  <td className="px-4 py-2 text-right font-medium tabular-nums text-ink">
                    {formatINR(item.amount)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="space-y-1 px-4 py-3 text-right text-sm">
            <p className="text-muted">Subtotal: <b className="text-ink">{formatINR(inv.subtotal)}</b></p>
            <p className="text-muted">
              Tax ({inv.tax_percent}%): <b className="text-ink">{formatINR(inv.tax_amount)}</b>
            </p>
            <p className="text-base font-bold text-ink">Total: {formatINR(inv.total)}</p>
            <p className="text-muted">Paid: <b className="text-success">{formatINR(inv.paid_amount)}</b></p>
            <p className="text-muted">
              Outstanding: <b className={outstanding > 0 ? 'text-warning' : 'text-success'}>{formatINR(outstanding)}</b>
            </p>
          </div>
        </div>

        {inv.notes && (
          <p className="mt-3 rounded-lg bg-surfaceWarm px-4 py-2 text-sm text-muted">{inv.notes}</p>
        )}
        {inv.terms && (
          <p className="mt-2 rounded-lg bg-surfaceWarm px-4 py-2 text-sm text-muted">
            <span className="font-semibold uppercase tracking-wide">Terms:</span> {inv.terms}
          </p>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-2">
          {inv.status === 'draft' && (
            <ActionButton
              onClick={() => send.mutate()}
              pending={send.isPending}
              icon={<Send className="h-4 w-4" />}
              label="Mark as sent"
            />
          )}
          {outstanding > 0 && inv.status !== 'cancelled' && (
            <ActionButton
              onClick={() => setPayment(true)}
              pending={pay.isPending}
              icon={<Wallet className="h-4 w-4" />}
              label="Record payment"
            />
          )}
          <ActionButton
            onClick={() => pdf.mutate()}
            pending={pdf.isPending}
            icon={<Download className="h-4 w-4" />}
            label="Download PDF"
            outline
          />
        </div>

        {errDetail(send.error) && (
          <div className="mt-3 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">
            {errDetail(send.error)}
          </div>
        )}

        {payment && (
          <RecordPaymentModal
            outstanding={outstanding}
            pending={pay.isPending}
            error={pay.error}
            onSubmit={(amount, date, method) => pay.mutate({ amount, payment_date: date, method })}
            onClose={() => setPayment(false)}
          />
        )}
      </div>
    </Modal>
  );
}
