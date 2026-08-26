import { useState } from 'react';
import { X } from 'lucide-react';
import type { ProjectDetail, ProjectCreateInput, ProjectType } from '../../../lib/types';
import { PROJECT_TYPE_OPTIONS, PROJECT_STATUS_OPTIONS, projectTypeLabel } from '../../../lib/constants';
import { toISODate } from '../../../lib/date';
import { formatIndianCurrencyInput, parseIndianCurrencyInput } from '../../../lib/currencyInput';
import CurrencyInput from '../../../components/ui/CurrencyInput';
import DatePicker from '../../../components/ui/DatePicker';

const primaryBtnClass =
  'inline-flex h-10 items-center justify-center gap-2 rounded-md bg-orange px-4 text-sm font-medium text-white transition hover:bg-orangeDark focus:outline-none focus-visible:ring-2 focus-visible:ring-orange/50';
const secondaryBtnClass =
  'inline-flex h-9 items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 text-sm font-medium text-ink transition hover:bg-surfaceWarm focus:outline-none focus-visible:ring-2 focus-visible:ring-navy/40';
const modalFieldClass =
  'h-10 w-full rounded-md border border-border bg-surface px-3 text-sm text-ink transition focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30';
const modalLabelClass = 'mb-1 block text-xs font-medium text-muted';

function projectStatusLabel(status: string): string {
  return status.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}

export default function EditProjectModal({
  project,
  clients,
  employees,
  canAssignLead,
  canEditMoney,
  onClose,
  onSubmit,
  pending,
  error,
}: {
  project: ProjectDetail;
  clients: { id: number; name: string }[];
  employees: { id: number; name: string }[];
  canAssignLead: boolean;
  canEditMoney?: boolean;
  onClose: () => void;
  onSubmit: (payload: Partial<ProjectCreateInput>) => void;
  pending: boolean;
  error: { response?: { data?: { detail?: string } } } | null;
}) {
  // Financial fields are executive-only (L0/L1) per the financial access policy;
  // non-executives simply don't send them.
  const showMoney = canEditMoney ?? true;
  const [form, setForm] = useState({
    name: project.name,
    project_type: project.project_type as ProjectType,
    status: project.status,
    priority: project.priority,
    category: project.category ?? '',
    client_id: project.client_id ?? '',
    project_lead_id: project.project_lead_id ?? '',
    location: project.location ?? '',
    plot_area: project.plot_area ?? '',
    built_up_area: project.built_up_area ?? '',
    no_of_floors: project.no_of_floors ?? '',
    budget: project.budget != null ? formatIndianCurrencyInput(String(project.budget)) : '',
    start_date: project.start_date ?? toISODate(new Date()),
    end_date: project.end_date ?? '',
    description: project.description ?? '',
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      name: form.name,
      project_type: form.project_type,
      status: form.status,
      priority: form.priority,
      category: form.category || undefined,
      client_id: form.client_id === '' ? null : Number(form.client_id),
      project_lead_id: form.project_lead_id === '' ? null : Number(form.project_lead_id),
      location: form.location || undefined,
      plot_area: form.plot_area === '' ? null : Number(form.plot_area),
      built_up_area: form.built_up_area === '' ? null : Number(form.built_up_area),
      no_of_floors: form.no_of_floors || undefined,
      ...(showMoney
        ? {
            budget: parseIndianCurrencyInput(form.budget),
          }
        : {}),
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      description: form.description || undefined,
    });
  }

  const set = (key: keyof typeof form, value: string) => setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-border bg-surface p-6 shadow-overlay">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold tracking-tight text-ink">Edit project</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-md p-1 text-muted transition hover:bg-surfaceWarm hover:text-ink">
            <X className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={submit} className="mt-4 space-y-4">
          <label className="block">
            <span className={modalLabelClass}>Name</span>
            <input
              required
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              className={modalFieldClass}
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={modalLabelClass}>Type</span>
              <select
                value={form.project_type}
                onChange={(e) => set('project_type', e.target.value)}
                className={modalFieldClass}
              >
                {PROJECT_TYPE_OPTIONS.map((t) => (
                  <option key={t} value={t}>
                    {projectTypeLabel(t)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className={modalLabelClass}>Status</span>
              <select value={form.status} onChange={(e) => set('status', e.target.value)} className={modalFieldClass}>
                {PROJECT_STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {projectStatusLabel(s)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={modalLabelClass}>Category</span>
              <input value={form.category} onChange={(e) => set('category', e.target.value)} placeholder="e.g. Villa, Apartment" className={modalFieldClass} />
            </label>
            <label className="block">
              <span className={modalLabelClass}>Priority</span>
              <select value={form.priority} onChange={(e) => set('priority', e.target.value)} className={modalFieldClass}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={modalLabelClass}>Client</span>
              <select value={form.client_id} onChange={(e) => set('client_id', e.target.value)} className={modalFieldClass}>
                <option value="">No client</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className={modalLabelClass}>Project lead</span>
              <select
                value={form.project_lead_id}
                onChange={(e) => set('project_lead_id', e.target.value)}
                disabled={!canAssignLead}
                className={`${modalFieldClass} disabled:cursor-not-allowed disabled:opacity-60`}
              >
                <option value="">No project lead</option>
                {employees.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={modalLabelClass}>Location</span>
              <input value={form.location} onChange={(e) => set('location', e.target.value)} className={modalFieldClass} />
            </label>
            <label className="block">
              <span className={modalLabelClass}>No. of floors</span>
              <input value={form.no_of_floors} onChange={(e) => set('no_of_floors', e.target.value)} placeholder="e.g. G+2" className={modalFieldClass} />
            </label>
          </div>
          {showMoney && (
            <label className="block">
              <span className={modalLabelClass}>Budget (INR)</span>
              <CurrencyInput
                value={form.budget}
                onChange={(budget) => set('budget', budget)}
                placeholder="e.g. 10,00,000"
                className="mt-0"
              />
            </label>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={modalLabelClass}>Plot area</span>
              <input
                type="number"
                value={form.plot_area}
                onChange={(e) => set('plot_area', e.target.value)}
                placeholder="sq.ft"
                className={modalFieldClass}
              />
            </label>
            <label className="block">
              <span className={modalLabelClass}>Built-up area</span>
              <input
                type="number"
                value={form.built_up_area}
                onChange={(e) => set('built_up_area', e.target.value)}
                placeholder="sq.ft"
                className={modalFieldClass}
              />
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={modalLabelClass}>Start date</span>
              <DatePicker value={form.start_date} onChange={(v) => set('start_date', v)} className="mt-1" />
            </label>
            <label className="block">
              <span className={modalLabelClass}>End date</span>
              <DatePicker value={form.end_date} onChange={(v) => set('end_date', v)} className="mt-1" />
            </label>
          </div>
          <label className="block">
            <span className={modalLabelClass}>Description</span>
            <textarea
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
              rows={3}
              className={`${modalFieldClass} h-auto py-2`}
            />
          </label>
          {error?.response?.data?.detail && (
            <div className="rounded-md border border-danger/30 bg-dangerSoft px-3 py-2.5 text-sm text-danger">
              {error.response.data.detail}
            </div>
          )}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className={secondaryBtnClass}>
              Cancel
            </button>
            <button type="submit" disabled={pending} className={primaryBtnClass}>
              {pending ? 'Saving…' : 'Save changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
