import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Download, Loader2, Plus, Receipt, X } from 'lucide-react';
import { useMemo, useState } from 'react';
import { getProjects } from '../../api/projects';
import {
  approveExpense,
  createExpense,
  downloadExpenseReceipt,
  getExpenses,
  uploadExpenseReceipt,
} from '../../api/finance';
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
import type { Expense, ExpenseCategory, ProjectListItem } from '../../lib/types';
import { useAuthStore } from '../../store/authStore';
import { parseIndianCurrencyInput } from '../../lib/currencyInput';
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

export default function ExpensesPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const [status, setStatus] = useState('');
  const [creating, setCreating] = useState(false);

  const expenses = useQuery({
    queryKey: ['expenses', status],
    queryFn: () => getExpenses(status ? { status } : {}),
  });

  const totals = useMemo(() => {
    let total = 0;
    let approved = 0;
    for (const e of expenses.data ?? []) {
      total += Number(e.amount);
      if (e.status === 'approved') approved += Number(e.amount);
    }
    return { total, approved };
  }, [expenses.data]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">{t('finance.expenses')}</h1>
          <p className="mt-1 text-sm text-muted">
            {t('finance.recordProjectCosts')} and route them through approval.
          </p>
        </div>
        <button onClick={() => setCreating(true)} className={primaryBtnClass}>
          <Plus className="h-4 w-4" /> Add Expense
        </button>
      </div>
      <FinanceTabs level={user?.org_level_code} />

      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
          <p className="text-sm text-muted">Total recorded</p>
          <p className="mt-1 text-2xl font-bold text-ink">{formatINR(totals.total)}</p>
        </div>
        <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
          <p className="text-sm text-muted">Approved</p>
          <p className="mt-1 text-2xl font-bold text-success">{formatINR(totals.approved)}</p>
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
          title={t('finance.noExpensesFound')}
          text={t('finance.addFirstExpense')}
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
                <th className="px-4 py-3 font-semibold text-right">Actions</th>
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
                      <ExpenseRowActions expense={exp} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {creating && <CreateExpenseModal onClose={() => setCreating(false)} />}
    </div>
  );
}

function ExpenseRowActions({ expense }: { expense: Expense }) {
  const queryClient = useQueryClient();
  const decide = useMutation({
    mutationFn: (approve: boolean) => approveExpense(expense.id, approve),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['expenses'] }),
  });
  const download = useMutation({ mutationFn: () => downloadExpenseReceipt(expense.id) });

  if (expense.status === 'pending') {
    return (
      <div className="flex items-center justify-end gap-1">
        <button
          onClick={() => decide.mutate(true)}
          disabled={decide.isPending}
          title="Approve"
          className="rounded-lg p-1.5 text-success transition hover:bg-successSoft"
        >
          <Check className="h-4 w-4" />
        </button>
        <button
          onClick={() => decide.mutate(false)}
          disabled={decide.isPending}
          title="Reject"
          className="rounded-lg p-1.5 text-danger transition hover:bg-dangerSoft"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-end">
      <button
        onClick={() => download.mutate()}
        title="Receipt"
        className="rounded-lg p-1.5 text-muted transition hover:bg-surfaceWarm"
      >
        <Download className="h-4 w-4" />
      </button>
    </div>
  );
}

function CreateExpenseModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [category, setCategory] = useState<ExpenseCategory>('travel');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [projectId, setProjectId] = useState<number | ''>('');
  const [paidBy, setPaidBy] = useState('');
  const [file, setFile] = useState<File | null>(null);

  const projects = useQuery({ queryKey: ['projects-options'], queryFn: () => getProjects({ page_size: 100 }) });

  const create = useMutation({
    mutationFn: () =>
      createExpense({
        category,
        amount: parseIndianCurrencyInput(amount) ?? 0,
        description: description || undefined,
        expense_date: date,
        project_id: projectId === '' ? null : Number(projectId),
        paid_by: paidBy || undefined,
      }),
    onSuccess: async (expense) => {
      if (file) {
        try {
          await uploadExpenseReceipt(expense.id, file);
        } catch {
          /* receipt is optional */
        }
      }
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
      queryClient.invalidateQueries({ queryKey: ['finance-overview'] });
      toast('Expense saved', 'success');
      onClose();
    },
    onError: (err) => {
      toast(errDetail(err) ?? 'Failed to save expense', 'error');
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
          <h2 className="text-lg font-bold text-ink">Add Expense</h2>
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
          <label className={modalLabelClass}>
            Paid by
            <input
              value={paidBy}
              onChange={(e) => setPaidBy(e.target.value)}
              placeholder="Person / company"
              className={`${inputClass} mt-1`}
            />
          </label>
          <label className={modalLabelClass}>
            Receipt (optional)
            <input
              type="file"
              accept="image/*,.pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className={`${inputClass} mt-1 file:mr-3 file:rounded-md file:border-0 file:bg-surfaceWarm file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-ink hover:file:bg-border`}
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
              Save Expense
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
