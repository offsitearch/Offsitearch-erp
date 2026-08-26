import { useState } from 'react';
import { X } from 'lucide-react';
import type { PhaseStatus } from '../../../lib/types';
import { phaseStatusMeta } from '../../../lib/constants';
import { parseIndianCurrencyInput, formatIndianCurrencyInput } from '../../../lib/currencyInput';
import { primaryBtnClass, secondaryBtnClass, modalFieldClass, modalLabelClass } from '../../../lib/styles';
import DatePicker from '../../../components/ui/DatePicker';
import CurrencyInput from '../../../components/ui/CurrencyInput';

const PHASE_STATUS_OPTIONS: PhaseStatus[] = ['not_started', 'in_progress', 'completed', 'delayed'];

export default function PhaseEditModal({
  phase,
  pending,
  canEditMoney,
  onClose,
  onSubmit,
}: {
  phase: { id: number; name: string; status: PhaseStatus; start_date: string; end_date: string; completion_pct: number; studio_fee: string };
  pending: boolean;
  canEditMoney?: boolean;
  onClose: () => void;
  onSubmit: (payload: { name: string; status: PhaseStatus; start_date: string | null; end_date: string | null; completion_pct: number; studio_fee?: number | null }) => void;
}) {
  // Financial fields are executive-only (L0/L1) per the financial access policy;
  // non-executives simply don't send them.
  const showFee = canEditMoney ?? true;
  const [name, setName] = useState(phase.name);
  const [status, setStatus] = useState<PhaseStatus>(phase.status);
  const [startDate, setStartDate] = useState(phase.start_date);
  const [endDate, setEndDate] = useState(phase.end_date);
  const [completion, setCompletion] = useState(String(phase.completion_pct));
  const [studioFee, setStudioFee] = useState(phase.studio_fee);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const pct = Math.min(100, Math.max(0, Number(completion) || 0));
    onSubmit({
      name: name.trim() || phase.name,
      status,
      start_date: startDate || null,
      end_date: endDate || null,
      completion_pct: status === 'completed' ? 100 : pct,
      ...(showFee ? { studio_fee: parseIndianCurrencyInput(studioFee) } : {}),
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
      <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-lg border border-border bg-surface p-6 shadow-overlay">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold tracking-tight text-ink">Edit phase</h3>
          <button onClick={onClose} aria-label="Close" className="rounded-md p-1 text-muted transition hover:bg-surfaceWarm hover:text-ink">
            <X className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={submit} className="mt-4 space-y-4">
          <label className="block">
            <span className={modalLabelClass}>Phase name</span>
            <input value={name} onChange={(e) => setName(e.target.value)} className={modalFieldClass} />
          </label>
          <label className="block">
            <span className={modalLabelClass}>Status</span>
            <select value={status} onChange={(e) => setStatus(e.target.value as PhaseStatus)} className={modalFieldClass}>
              {PHASE_STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {phaseStatusMeta(s).label}
                </option>
              ))}
            </select>
          </label>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={modalLabelClass}>Start date</span>
              <DatePicker value={startDate} onChange={setStartDate} className="mt-1" />
            </label>
            <label className="block">
              <span className={modalLabelClass}>End date</span>
              <DatePicker value={endDate} onChange={setEndDate} className="mt-1" />
            </label>
          </div>
          <label className="block">
            <span className={modalLabelClass}>Completion (%)</span>
            <input
              type="number"
              min={0}
              max={100}
              value={completion}
              onChange={(e) => setCompletion(e.target.value)}
              className={modalFieldClass}
            />
          </label>
          {showFee && (
            <label className="block">
              <span className={modalLabelClass}>Studio Fee (INR)</span>
              <CurrencyInput value={formatIndianCurrencyInput(studioFee)} onChange={setStudioFee} className="mt-0" />
            </label>
          )}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className={secondaryBtnClass}>
              Cancel
            </button>
            <button type="submit" disabled={pending} className={primaryBtnClass}>
              {pending ? 'Saving…' : 'Save phase'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
