import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, Loader2, Plus, Receipt, X } from 'lucide-react';
import { useMemo, useState } from 'react';
import { getProjects } from '../../api/projects';
import { createMyExpense, downloadExpenseReceipt, getMyExpenses } from '../../api/finance';
import { EmptyState } from '../../components/ui/EmptyState';
import { Skeleton } from '../../components/ui/Skeleton';
import DatePicker from '../../components/ui/DatePicker';
import CurrencyInput from '../../components/ui/CurrencyInput';
import { useToast } from '../../components/Toast';
import {
  expenseCategoryLabel,
  expenseStatusMeta,
  EXPENSE_CATEGORY_OPTIONS,
  formatINR,
} from '../../lib/constants';
import type { ExpenseCategory, ProjectListItem } from '../../lib/types';
import { toISODate } from '../../lib/date';
import { parseIndianCurrencyInput } from '../../lib/currencyInput';
import { useAuthStore } from '../../store/authStore';
import { FinanceTabs } from './components/FinanceTabs';
import { useTranslation } from 'react-i18next';
import { inputClass, selectClass, primaryBtnClass, secondaryBtnClass, modalLabelClass } from '../../lib/styles';

function errDetail(err: unknown): string | null {
  return (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? null;
}

const STATUS_TABS: { key: string; label: string }[] = [
  { key: '', label: 'All' },
  { key: 'pending', label: 'Pending' },
  { key: 'approved', label: 'Approved' },
  { key: 'rejected', label: 'Rejected' },
];

export default function MyExpensesPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const [status, setStatus] = useState('');
  const [creating, setCreating] = useState(false);

  const expenses = useQuery({
    queryKey: ['my-expenses', status],
    queryFn: () => getMyExpenses(status ? { status } : undefined),
  });

  const totals = useMemo(() => {
    let total = 0;
    let pendingCount = 0;
    let approvedCount = 0;
    for (const e of expenses.data ?? []) {
      total += Number(e.amount);
      if (e.status === 'pending') pendingCount++;
      if (e.status === 'approved') approvedCount++;
    }
    return { total, pendingCount, approvedCount };
  }, [expenses.data]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">{t('finance.myExpenses')}</h1>
          <p className="mt-1 text-sm text-muted">
            {t('finance.submitAndTrack')}
          </p>
        </div>
        <button onClick={() => setCreating(true)} className={primaryBtnClass}>
          <Plus className="h-4 w-4" /> Submit Expense
        </button>
      </div>
      <FinanceTabs level={user?.org_level_code} />

      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
          <p className="text-sm text-muted">Total submitted</p>
          <p className="mt-1 text-2xl font-bold text-ink">{formatINR(totals.total)}</p>
        </div>
        <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
          <p className="text-sm text-muted">Pending</p>
          <p className="mt-1 text-2xl font-bold text-warning">{totals.pendingCount}</p>
        </div>
        <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
          <p className="text-sm text-muted">Approved</p>
          <p className="mt-1 text-2xl font-bold text-success">{totals.approvedCount}</p>
        </div>
      </div>

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
          </button>
        ))}
      </div>

      {expenses.isPending ? (
        <div className="space-y-2">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12 w-full rounded-xl" />
          ))}
        </div>
      ) : (expenses.data ?? []).length === 0 ? (
        <EmptyState
          title="No expenses found"
          text={t('finance.submitFirstExpense')}
          icon={Receipt}
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border bg-surface shadow-card">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead>
              <tr className="border-b border-border bg-surfaceWarm text-xs uppercase tracking-wide text-muted">
                <th className="px-4 py-3 font-semibold">Date</th>
                <th className="px-4 py-3 font-semibold">Category</th>
                <th className="px-4 py-3 font-semibold">Description</th>
                <th className="px-4 py-3 font-semibold">Project</th>
                <th className="px-4 py-3 font-semibold text-right">Amount</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold text-right">Receipt</th>
              </tr>
            </thead>
            <tbody>
              {(expenses.data ?? []).map((exp) => {
                const meta = expenseStatusMeta(exp.status);
                return (
                  <tr key={exp.id} className="border-b border-border last:border-0 hover:bg-surfaceWarm">
                    <td className="px-4 py-3 text-muted">{exp.expense_date ?? '—'}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-surfaceWarm px-2.5 py-1 text-xs font-medium text-graphite">
                        {expenseCategoryLabel(exp.category as ExpenseCategory)}
                      </span>
                    </td>
                    <td className="max-w-56 truncate px-4 py-3 text-ink">{exp.description ?? '—'}</td>
                    <td className="px-4 py-3 text-muted">{exp.project_code ?? '—'}</td>
                    <td className="px-4 py-3 text-right font-semibold text-ink">{formatINR(exp.amount)}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${meta.badge}`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
                        {meta.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end">
                        {exp.receipt_path && <ReceiptDownloadButton expenseId={exp.id} />}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {creating && <SubmitExpenseModal onClose={() => setCreating(false)} />}
    </div>
  );
}

function ReceiptDownloadButton({ expenseId }: { expenseId: number }) {
  const download = useMutation({ mutationFn: () => downloadExpenseReceipt(expenseId) });

  return (
    <button
      onClick={() => download.mutate()}
      title="Download receipt"
      className="rounded-lg p-1.5 text-muted transition hover:bg-surfaceWarm"
    >
      <Download className="h-4 w-4" />
    </button>
  );
}

function SubmitExpenseModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [category, setCategory] = useState<ExpenseCategory>('travel');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [date, setDate] = useState(toISODate(new Date()));
  const [projectId, setProjectId] = useState<number | ''>('');

  const projects = useQuery({ queryKey: ['projects-options'], queryFn: () => getProjects({ page_size: 100 }) });

  const create = useMutation({
    mutationFn: () =>
      createMyExpense({
        category,
        amount: parseIndianCurrencyInput(amount) ?? 0,
        description: description || undefined,
        expense_date: date,
        project_id: projectId === '' ? undefined : Number(projectId),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-expenses'] });
      toast('Expense submitted', 'success');
      onClose();
    },
    onError: (err) => {
      toast(errDetail(err) ?? 'Failed to submit expense', 'error');
    },
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    create.mutate();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
      <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-xl bg-surface p-6 shadow-overlay">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-ink">Submit Expense</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-lg p-1 text-muted hover:bg-surfaceWarm">
            <X className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={submit} className="mt-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <label className={modalLabelClass}>
              Category
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as ExpenseCategory)}
                className={`${selectClass} mt-1`}
              >
                {EXPENSE_CATEGORY_OPTIONS.map((c) => (
                  <option key={c} value={c}>
                    {expenseCategoryLabel(c)}
                  </option>
                ))}
              </select>
            </label>
            <label className={modalLabelClass}>
              Amount (INR)
              <CurrencyInput value={amount} onChange={setAmount} className="mt-1" />
            </label>
            <label className={modalLabelClass}>
              Date
              <DatePicker value={date} onChange={setDate} className="mt-1" />
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
                    {p.project_code}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className={modalLabelClass}>
            Description
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className={`${inputClass} mt-1`}
            />
          </label>

          {errDetail(create.error) && (
            <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">
              {errDetail(create.error)}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className={secondaryBtnClass}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={create.isPending || !amount}
              className={primaryBtnClass}
            >
              {create.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Submit
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
