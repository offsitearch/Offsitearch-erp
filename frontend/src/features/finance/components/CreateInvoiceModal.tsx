import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Plus, X } from 'lucide-react';
import { useState } from 'react';
import { getClients } from '../../../api/clients';
import { createInvoice } from '../../../api/finance';
import { Modal } from '../../../components/Modal';
import { getProjects } from '../../../api/projects';
import { useToast } from '../../../components/Toast';
import DatePicker from '../../../components/ui/DatePicker';
import CurrencyInput from '../../../components/ui/CurrencyInput';
import { formatINR } from '../../../lib/constants';
import { parseIndianCurrencyInput } from '../../../lib/currencyInput';
import { inputClass, selectClass, primaryBtnClass, secondaryBtnClass, modalLabelClass } from '../../../lib/styles';
import type { ClientListItem, InvoiceCreateInput, ProjectListItem } from '../../../lib/types';

function errDetail(err: unknown): string | null {
  return (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? null;
}

interface FeeLineInput {
  description: string;
  hsn: string;
  qty: string;
  rate: string;
}

export default function CreateInvoiceModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [clientId, setClientId] = useState<number | ''>('');
  const [projectId, setProjectId] = useState<number | ''>('');
  const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().slice(0, 10));
  const [dueDate, setDueDate] = useState('');
  const [taxPercent, setTaxPercent] = useState('18');
  const [lines, setLines] = useState<FeeLineInput[]>([{ description: '', hsn: '', qty: '1', rate: '' }]);
  const [notes, setNotes] = useState('');

  const clients = useQuery({ queryKey: ['clients-options'], queryFn: () => getClients({ page_size: 100 }) });
  const projects = useQuery({ queryKey: ['projects-options'], queryFn: () => getProjects({ page_size: 100 }) });

  const lineAmount = (l: FeeLineInput) =>
    (Number(l.qty) || 0) * (parseIndianCurrencyInput(l.rate) ?? 0);
  const subtotal = lines.reduce((sum, l) => sum + lineAmount(l), 0);
  const tax = subtotal * ((Number(taxPercent) || 0) / 100);
  const total = subtotal + tax;

  const create = useMutation({
    mutationFn: (payload: InvoiceCreateInput) => createInvoice(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      queryClient.invalidateQueries({ queryKey: ['finance-overview'] });
      toast('Invoice created', 'success');
      onClose();
    },
    onError: (err) => {
      toast(errDetail(err) ?? 'Failed to create invoice', 'error');
    },
  });

  function updateLine(idx: number, patch: Partial<FeeLineInput>) {
    setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, ...patch } : l)));
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const items = lines
      .filter((l) => l.description.trim() !== '' && (parseIndianCurrencyInput(l.rate) ?? 0) > 0)
      .map((l) => ({
        description: l.description.trim(),
        hsn_sac: l.hsn.trim() || null,
        quantity: Number(l.qty) || 1,
        rate: parseIndianCurrencyInput(l.rate)!,
      }));
    if (items.length === 0) return;
    create.mutate({
      client_id: Number(clientId),
      project_id: projectId === '' ? null : Number(projectId),
      invoice_date: invoiceDate,
      due_date: dueDate,
      tax_percent: Number(taxPercent) || 0,
      items,
      notes: notes.trim() || null,
    });
  }

  return (
    <Modal onClose={onClose} maxWidth="max-w-3xl">
      <div className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-ink">New Invoice</h2>
            <p className="mt-0.5 text-sm text-muted">Bill by line item — qty × rate with optional HSN/SAC codes.</p>
          </div>
          <button onClick={onClose} aria-label="Close" className="rounded-lg p-1 text-muted hover:bg-surfaceWarm">
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={submit} className="mt-4 space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className={modalLabelClass}>
              Client *
              <select
                required
                value={clientId}
                onChange={(e) => setClientId(e.target.value === '' ? '' : Number(e.target.value))}
                className={`${selectClass} mt-1`}
              >
                <option value="">Select client</option>
                {(clients.data?.items ?? []).map((c: ClientListItem) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            <label className={modalLabelClass}>
              Project (optional)
              <select
                value={projectId}
                onChange={(e) => setProjectId(e.target.value === '' ? '' : Number(e.target.value))}
                className={`${selectClass} mt-1`}
              >
                <option value="">No project</option>
                {(projects.data?.items ?? []).map((p: ProjectListItem) => (
                  <option key={p.id} value={p.id}>
                    {p.project_code} {p.name ? `· ${p.name}` : ''}
                  </option>
                ))}
              </select>
            </label>
            <label className={modalLabelClass}>
              Invoice date
              <DatePicker value={invoiceDate} onChange={setInvoiceDate} className="mt-1" />
            </label>
            <label className={modalLabelClass}>
              Due date
              <DatePicker value={dueDate} onChange={setDueDate} className="mt-1" />
            </label>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Line items</p>
              <button
                type="button"
                onClick={() => setLines((prev) => [...prev, { description: '', hsn: '', qty: '1', rate: '' }])}
                className="inline-flex items-center gap-1 text-xs font-medium text-navy hover:underline"
              >
                <Plus className="h-3.5 w-3.5" />
                Add line item
              </button>
            </div>
            <div className="mt-2 space-y-2">
              <div className="flex items-center gap-2 px-1 text-[11px] font-medium uppercase tracking-wide text-muted">
                <span className="min-w-0 flex-1">Description</span>
                <span className="w-20 shrink-0">HSN/SAC</span>
                <span className="w-14 shrink-0 text-right">Qty</span>
                <span className="w-32 shrink-0 text-right">Rate</span>
                <span className="w-24 shrink-0 text-right">Amount</span>
                <span className="w-8 shrink-0" />
              </div>
              {lines.map((line, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <input
                    value={line.description}
                    onChange={(e) => updateLine(idx, { description: e.target.value })}
                    placeholder="e.g. Architectural design fee — concept to GFC drawings"
                    className={`${inputClass} min-w-0 flex-1`}
                  />
                  <input
                    value={line.hsn}
                    onChange={(e) => updateLine(idx, { hsn: e.target.value })}
                    placeholder="995411"
                    className={`${inputClass} w-20 shrink-0`}
                  />
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={line.qty}
                    onChange={(e) => updateLine(idx, { qty: e.target.value })}
                    className={`${inputClass} w-14 shrink-0 text-right`}
                  />
                  <CurrencyInput
                    value={line.rate}
                    onChange={(rate) => updateLine(idx, { rate })}
                    placeholder="1,50,000"
                    className="w-32 shrink-0"
                  />
                  <span className="w-24 shrink-0 text-right text-sm font-medium tabular-nums text-ink">
                    {formatINR(lineAmount(line))}
                  </span>
                  <button
                    type="button"
                    onClick={() => setLines((prev) => prev.filter((_, i) => i !== idx))}
                    disabled={lines.length === 1}
                    aria-label="Remove line item"
                    className="w-8 shrink-0 rounded-lg p-2 text-muted transition hover:bg-dangerSoft hover:text-danger disabled:opacity-30"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <label className="block">
            <span className={modalLabelClass}>Notes (optional)</span>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="e.g. Advance received, payment schedule, scope summary…"
              className={`${inputClass} h-auto py-2`}
            />
          </label>

          <div className="flex flex-wrap items-end justify-end gap-x-6 gap-y-2 rounded-lg bg-surfaceWarm px-4 py-3 text-sm">
            <label>
              <span className="block text-xs font-medium text-muted">GST / Tax %</span>
              <input
                type="number"
                min="0"
                max="100"
                value={taxPercent}
                onChange={(e) => setTaxPercent(e.target.value)}
                className={`${inputClass} mt-1 w-24`}
              />
            </label>
            <div className="space-y-0.5 text-right">
              <p className="text-muted">
                Subtotal: <b className="text-ink">{formatINR(subtotal)}</b>
              </p>
              <p className="text-muted">
                Tax: <b className="text-ink">{formatINR(tax)}</b>
              </p>
              <p className="text-base font-bold text-ink">Total: {formatINR(total)}</p>
            </div>
          </div>

          {errDetail(create.error) && (
            <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{errDetail(create.error)}</div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className={secondaryBtnClass}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={create.isPending || clientId === '' || !invoiceDate || !dueDate}
              className={primaryBtnClass}
            >
              {create.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Create Invoice
            </button>
          </div>
        </form>
      </div>
    </Modal>
  );
}
