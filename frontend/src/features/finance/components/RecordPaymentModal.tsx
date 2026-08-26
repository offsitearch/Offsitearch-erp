import { useState } from 'react';
import { Loader2, X } from 'lucide-react';
import { Modal } from '../../../components/Modal';
import DatePicker from '../../../components/ui/DatePicker';
import CurrencyInput from '../../../components/ui/CurrencyInput';
import { formatINR, PAYMENT_METHOD_OPTIONS, paymentMethodLabel } from '../../../lib/constants';
import { parseIndianCurrencyInput, formatIndianCurrencyInput } from '../../../lib/currencyInput';
import { selectClass, primaryBtnClass, secondaryBtnClass, modalLabelClass } from '../../../lib/styles';
import type { PaymentMethod } from '../../../lib/types';

function errDetail(err: unknown): string | null {
  return (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? null;
}

export default function RecordPaymentModal({
  outstanding,
  pending,
  error,
  onSubmit,
  onClose,
}: {
  outstanding: number;
  pending: boolean;
  error: unknown;
  onSubmit: (amount: number, date: string, method: PaymentMethod) => void;
  onClose: () => void;
}) {
  const [amount, setAmount] = useState(() => formatIndianCurrencyInput(String(outstanding)));
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [method, setMethod] = useState<PaymentMethod>('bank_transfer');

  function submit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit(parseIndianCurrencyInput(amount) ?? 0, date, method);
  }

  return (
    <Modal onClose={onClose} maxWidth="max-w-sm">
      <div className="p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-ink">Record payment</h3>
          <button onClick={onClose} aria-label="Close" className="rounded-lg p-1 text-muted hover:bg-surfaceWarm">
            <X className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={submit} className="mt-4 space-y-3">
          <label className={modalLabelClass}>
            Amount (outstanding: {formatINR(outstanding)})
            <CurrencyInput value={amount} onChange={setAmount} className="mt-1" />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className={modalLabelClass}>
              Date
              <DatePicker value={date} onChange={setDate} className="mt-1" />
            </label>
            <label className={modalLabelClass}>
              Method
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value as PaymentMethod)}
                className={`${selectClass} mt-1`}
              >
                {PAYMENT_METHOD_OPTIONS.map((m) => (
                  <option key={m} value={m}>
                    {paymentMethodLabel(m)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {errDetail(error) && (
            <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">
              {errDetail(error)}
            </div>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className={secondaryBtnClass}>
              Cancel
            </button>
            <button type="submit" disabled={pending} className={primaryBtnClass}>
              {pending && <Loader2 className="h-4 w-4 animate-spin" />}
              Save payment
            </button>
          </div>
        </form>
      </div>
    </Modal>
  );
}
