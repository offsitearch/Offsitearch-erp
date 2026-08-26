import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Building2, Clock, Landmark, Mail, MapPin, MessageSquarePlus, Pencil, Phone, Trash2, UserRound, X } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { addCommunication, deleteClient, getClientProfile, updateClient } from '../../api/clients';
import { LogoLoader } from '../../components/LogoLoader';
import { EmptyState } from '../../components/ui/EmptyState';
import {
  CLIENT_TYPE_OPTIONS,
  clientTypeLabel,
  COMMUNICATION_TYPE_LABELS,
  COMMUNICATION_TYPE_OPTIONS,
  DEAL_STAGE_META,
  DEAL_STAGE_OPTIONS,
  formatINR,
  projectTypeLabel,
  canAccess,
} from '../../lib/constants';
import { formatDate, toISODate } from '../../lib/date';
import type { ClientCreateInput, CommunicationInput, CommunicationType, ClientType } from '../../lib/types';
import { useAuthStore } from '../../store/authStore';
import { encodeId } from '../../lib/obfuscate';
import { useDecodedIdRequired as useDecodedId } from '../../lib/useDecodedId';
import { ProjectStatusBadge } from '../projects/components/ProjectStatusBadge';
import Breadcrumbs from '../../components/ui/Breadcrumbs';
import DatePicker from '../../components/ui/DatePicker';
import { useTranslation } from 'react-i18next';
import { secondaryBtnClass, dangerBtnClass, modalFieldClass, modalLabelClass } from '../../lib/styles';

export default function ClientProfilePage() {
  const { t } = useTranslation();
  const clientId = useDecodedId();
  const navigate = useNavigate();
  const currentUser = useAuthStore((s) => s.user);
  const isSuperAdmin = canAccess(currentUser?.org_level_code, 'L1');
  // Financial data is executive-only (L0/L1) per the financial access policy.
  const canSeeMoney = isSuperAdmin;
  const queryClient = useQueryClient();
  const [showCommForm, setShowCommForm] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [showDeactivate, setShowDeactivate] = useState(false);

  const profile = useQuery({ queryKey: ['client-profile', clientId], queryFn: () => getClientProfile(clientId) });

  const commMutation = useMutation({
    mutationFn: (payload: CommunicationInput) => addCommunication(clientId, payload),
    onSuccess: () => {
      setShowCommForm(false);
      queryClient.invalidateQueries({ queryKey: ['client-profile', clientId] });
    },
  });

  const editMutation = useMutation({
    mutationFn: (payload: Partial<ClientCreateInput>) => updateClient(clientId, payload),
    onSuccess: () => {
      setShowEdit(false);
      queryClient.invalidateQueries({ queryKey: ['client-profile', clientId] });
      queryClient.invalidateQueries({ queryKey: ['clients'] });
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: () => deleteClient(clientId),
    onSuccess: () => {
      setShowDeactivate(false);
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      navigate('/clients');
    },
  });

  if (profile.isPending) {
    return <LogoLoader />;
  }

  const data = profile.data;
  if (!data) {
    return <EmptyState icon={Building2} title={t('clients.clientNotFound')} />;
  }

  const { client, projects, communications, financial_summary: fin } = data;

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Clients', to: '/clients' }, { label: client.name }]} />

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-navy/10 text-navy">
            {client.client_type === 'individual' ? (
              <UserRound className="h-6 w-6" />
            ) : (
              <Building2 className="h-6 w-6" />
            )}
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-ink">{client.name}</h1>
            <p className="mt-1 text-sm text-muted">
              {clientTypeLabel(client.client_type)}
              {client.company_name ? ` · ${client.company_name}` : ''}
            </p>
            {client.deal_stage && (
              <span className={`mt-1.5 inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${DEAL_STAGE_META[client.deal_stage]?.badge || 'bg-surfaceWarm text-muted'}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${DEAL_STAGE_META[client.deal_stage]?.dot || 'bg-muted'}`} />
                {DEAL_STAGE_META[client.deal_stage]?.label || client.deal_stage}
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => setShowEdit(true)} className={secondaryBtnClass}>
            <Pencil className="h-4 w-4" />
            Edit
          </button>
          {isSuperAdmin && (
            <button onClick={() => setShowDeactivate(true)} className={dangerBtnClass}>
              <Trash2 className="h-4 w-4" />
              Deactivate
            </button>
          )}
          <button
            onClick={() => setShowCommForm(true)}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-orange px-4 text-sm font-medium text-white transition hover:bg-orangeDark focus:outline-none focus-visible:ring-2 focus-visible:ring-orange/50"
          >
            <MessageSquarePlus className="h-4 w-4" />
            Log Communication
          </button>
        </div>
      </div>

      <div className={`grid gap-3 ${canSeeMoney ? 'sm:grid-cols-3' : 'sm:grid-cols-1'}`}>
        <div className="rounded-lg border border-border bg-surface p-4 shadow-card">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">{t('clients.totalProjects')}</p>
          <p className="mt-1 text-2xl font-bold text-ink">{fin.total_projects}</p>
        </div>
        {canSeeMoney && (
          <>
            <div className="rounded-lg border border-border bg-surface p-4 shadow-card">
              <p className="text-xs font-medium uppercase tracking-wide text-muted">{t('clients.totalBudget')}</p>
              <p className="mt-1 text-2xl font-bold text-ink">{formatINR(fin.total_budget)}</p>
            </div>
            <div className="rounded-lg border border-border bg-surface p-4 shadow-card">
              <p className="text-xs font-medium uppercase tracking-wide text-muted">Studio fee</p>
              <p className="mt-1 text-2xl font-bold text-ink">{formatINR(fin.total_studio_fee)}</p>
            </div>
          </>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">Projects</h2>
            {projects.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border py-10 text-center text-sm text-muted">
                No projects for this client yet.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-border bg-surface shadow-card">
                <table className="w-full min-w-[600px] text-left text-sm">
                  <thead className="border-b border-border bg-graphite/5 text-xs font-medium uppercase tracking-wide text-muted">
                    <tr>
                      <th className="px-4 py-3">Project</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Progress</th>
                      {canSeeMoney && <th className="px-4 py-3">Studio fee</th>}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {projects.map((p) => (
                      <tr key={p.id} className="transition hover:bg-surfaceWarm">
                        <td className="px-4 py-3">
                          <Link to={`/projects/${encodeId(p.id)}`} className="font-medium text-ink hover:underline">
                            {p.name}
                          </Link>
                          <p className="text-xs text-muted">{p.project_code}</p>
                        </td>
                        <td className="px-4 py-3 text-muted">{projectTypeLabel(p.project_type)}</td>
                        <td className="px-4 py-3">
                          <ProjectStatusBadge status={p.status} />
                        </td>
                        <td className="px-4 py-3 text-muted">{p.progress_pct}%</td>
                        {canSeeMoney && (
                          <td className="px-4 py-3 font-medium text-ink">{formatINR(p.studio_fee)}</td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
              Contact log ({communications.length})
            </h2>
            <div className="space-y-3">
              {communications.length === 0 && (
                <div className="rounded-lg border border-dashed border-border py-10 text-center text-sm text-muted">
                  No communications logged yet.
                </div>
              )}
              {communications.map((c) => (
                <div key={c.id} className="rounded-lg border border-border bg-surface p-4 shadow-card">
                  <div className="flex items-center justify-between gap-2">
                    <span className="rounded-full bg-navy/10 px-2.5 py-0.5 text-xs font-medium text-navy">
                      {COMMUNICATION_TYPE_LABELS[c.type]}
                    </span>
                    <span className="text-xs text-muted">
                      {c.user_name} · {new Date(c.occurred_at).toLocaleString('en-IN')}
                    </span>
                  </div>
                  {c.subject && <p className="mt-2 text-sm font-medium text-ink">{c.subject}</p>}
                  {c.notes && <p className="mt-1 text-sm text-muted">{c.notes}</p>}
                </div>
              ))}
            </div>
          </section>
        </div>

        <aside className="space-y-4">
          <div className="rounded-lg border border-border bg-surface p-5 shadow-card">
            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">Details</h3>
            <dl className="space-y-2.5 text-sm">
              <DetailRow icon={<Phone className="h-4 w-4" />} label="Phone" value={client.phone ?? '—'} />
              <DetailRow icon={<Mail className="h-4 w-4" />} label="Email" value={client.email ?? '—'} />
              <DetailRow icon={<MapPin className="h-4 w-4" />} label="Address" value={client.address ?? '—'} />
              <DetailRow icon={<Landmark className="h-4 w-4" />} label="GST" value={client.gst_number ?? '—'} />
              <DetailRow icon={<Landmark className="h-4 w-4" />} label="PAN" value={client.pan_number ?? '—'} />
              <DetailRow icon={<UserRound className="h-4 w-4" />} label="Contact" value={client.contact_person ?? '—'} />
            </dl>
            {client.next_follow_up_date && (
              <div className="mt-3 border-t border-border pt-3">
                <div className="flex items-center gap-2 text-sm">
                  <Clock className="h-4 w-4 text-muted" />
                  <span className="text-muted">Next follow-up:</span>
                  <span className="font-medium text-ink">{formatDate(client.next_follow_up_date)}</span>
                </div>
                {client.next_follow_up_action && (
                  <p className="ml-6 mt-0.5 text-xs text-muted">{client.next_follow_up_action}</p>
                )}
              </div>
            )}
          </div>

          {canSeeMoney && (
            <div className="rounded-lg border border-border bg-surface p-5 shadow-card">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">Finance</h3>
              <dl className="space-y-2.5 text-sm">
                <FinanceRow label="Invoiced" value={formatINR(fin.invoiced)} />
                <FinanceRow label="Received" value={formatINR(fin.received)} />
                <FinanceRow label="Outstanding" value={formatINR(fin.outstanding)} />
              </dl>
            </div>
          )}
        </aside>
      </div>

      {showCommForm && (
        <CommunicationModal
          onClose={() => setShowCommForm(false)}
          onSubmit={(payload) => commMutation.mutate(payload)}
          pending={commMutation.isPending}
          error={commMutation.error as { response?: { data?: { detail?: string } } } | null}
        />
      )}

      {showEdit && (
        <EditClientModal
          client={client}
          canEditMoney={canSeeMoney}
          onClose={() => setShowEdit(false)}
          onSubmit={(payload) => editMutation.mutate(payload)}
          pending={editMutation.isPending}
          error={editMutation.error as { response?: { data?: { detail?: string } } } | null}
        />
      )}

      {showDeactivate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
          <div className="max-h-[90vh] w-full max-w-sm overflow-y-auto rounded-lg border border-border bg-surface p-6 shadow-overlay">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold tracking-tight text-ink">{t('clients.deactivateClient')}</h2>
              <button onClick={() => setShowDeactivate(false)} aria-label="Close" className="rounded-md p-1 text-muted transition hover:bg-surfaceWarm hover:text-ink">
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="mt-2 text-sm text-muted">
              Deactivate <span className="font-medium text-ink">{client.name}</span>? The client is hidden from the
              directory but its records are kept.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setShowDeactivate(false)} className={secondaryBtnClass}>
                Cancel
              </button>
              <button
                onClick={() => deactivateMutation.mutate()}
                disabled={deactivateMutation.isPending}
                className="inline-flex h-9 items-center justify-center gap-2 rounded-md bg-danger px-4 text-sm font-medium text-white transition hover:bg-danger/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-danger/30 disabled:opacity-50"
              >
                {deactivateMutation.isPending ? 'Deactivating…' : 'Deactivate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function EditClientModal({
  client,
  canEditMoney,
  onClose,
  onSubmit,
  pending,
  error,
}: {
  client: {
    name: string;
    client_type: string;
    company_name: string | null;
    contact_person: string | null;
    phone: string | null;
    phone_secondary: string | null;
    email: string | null;
    address: string | null;
    gst_number: string | null;
    pan_number: string | null;
    source: string | null;
    budget_range?: string | null;
    interest: string | null;
    notes: string | null;
    deal_stage: string;
    next_follow_up_date: string | null;
    next_follow_up_action: string | null;
  };
  // budget_range is a deal value: executive-only (L0/L1) per the financial policy.
  canEditMoney?: boolean;
  onClose: () => void;
  onSubmit: (payload: Partial<ClientCreateInput>) => void;
  pending: boolean;
  error: { response?: { data?: { detail?: string } } } | null;
}) {
  const showBudget = canEditMoney ?? true;
  const [form, setForm] = useState({
    name: client.name,
    client_type: client.client_type as ClientType,
    company_name: client.company_name ?? '',
    contact_person: client.contact_person ?? '',
    phone: client.phone ?? '',
    phone_secondary: client.phone_secondary ?? '',
    email: client.email ?? '',
    address: client.address ?? '',
    gst_number: client.gst_number ?? '',
    pan_number: client.pan_number ?? '',
    source: client.source ?? '',
    budget_range: client.budget_range ?? '',
    interest: client.interest ?? '',
    notes: client.notes ?? '',
    deal_stage: client.deal_stage ?? '',
    next_follow_up_date: client.next_follow_up_date ?? '',
    next_follow_up_action: client.next_follow_up_action ?? '',
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      name: form.name,
      client_type: form.client_type,
      company_name: form.company_name || undefined,
      contact_person: form.contact_person || undefined,
      phone: form.phone || undefined,
      phone_secondary: form.phone_secondary || undefined,
      email: form.email || undefined,
      address: form.address || undefined,
      gst_number: form.gst_number || undefined,
      pan_number: form.pan_number || undefined,
      source: form.source || undefined,
      ...(showBudget ? { budget_range: form.budget_range || undefined } : {}),
      interest: form.interest || undefined,
      notes: form.notes || undefined,
      deal_stage: form.deal_stage || undefined,
      next_follow_up_date: form.next_follow_up_date || null,
      next_follow_up_action: form.next_follow_up_action || undefined,
    });
  }

  const set = (key: keyof typeof form, value: string) => setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-border bg-surface p-6 shadow-overlay">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold tracking-tight text-ink">Edit client</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-md p-1 text-muted transition hover:bg-surfaceWarm hover:text-ink">
            <X className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={submit} className="mt-4 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={modalLabelClass}>Name</span>
              <input required value={form.name} onChange={(e) => set('name', e.target.value)} className={modalFieldClass} />
            </label>
            <label className="block">
              <span className={modalLabelClass}>Type</span>
              <select
                value={form.client_type}
                onChange={(e) => setForm({ ...form, client_type: e.target.value as ClientType })}
                className={modalFieldClass}
              >
                {CLIENT_TYPE_OPTIONS.map((t) => (
                  <option key={t} value={t}>{clientTypeLabel(t)}</option>
                ))}
              </select>
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={modalLabelClass}>Company</span>
              <input value={form.company_name} onChange={(e) => set('company_name', e.target.value)} className={modalFieldClass} />
            </label>
            <label className="block">
              <span className={modalLabelClass}>Contact person</span>
              <input value={form.contact_person} onChange={(e) => set('contact_person', e.target.value)} className={modalFieldClass} />
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={modalLabelClass}>Phone</span>
              <input value={form.phone} onChange={(e) => set('phone', e.target.value)} className={modalFieldClass} />
            </label>
            <label className="block">
              <span className={modalLabelClass}>Alt phone</span>
              <input value={form.phone_secondary} onChange={(e) => set('phone_secondary', e.target.value)} className={modalFieldClass} />
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={modalLabelClass}>Email</span>
              <input value={form.email} onChange={(e) => set('email', e.target.value)} className={modalFieldClass} />
            </label>
            <label className="block">
              <span className={modalLabelClass}>GST</span>
              <input value={form.gst_number} onChange={(e) => set('gst_number', e.target.value)} className={modalFieldClass} />
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={modalLabelClass}>PAN</span>
              <input value={form.pan_number} onChange={(e) => set('pan_number', e.target.value)} className={modalFieldClass} />
            </label>
            <label className="block">
              <span className={modalLabelClass}>Source</span>
              <input value={form.source} onChange={(e) => set('source', e.target.value)} className={modalFieldClass} />
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {showBudget && (
              <label className="block">
                <span className={modalLabelClass}>Budget range</span>
                <input value={form.budget_range} onChange={(e) => set('budget_range', e.target.value)} className={modalFieldClass} />
              </label>
            )}
            <label className="block">
              <span className={modalLabelClass}>Interest</span>
              <input value={form.interest} onChange={(e) => set('interest', e.target.value)} className={modalFieldClass} />
            </label>
          </div>
          <label className="block">
            <span className={modalLabelClass}>Address</span>
            <textarea value={form.address} onChange={(e) => set('address', e.target.value)} rows={2} className={`${modalFieldClass} h-auto py-2`} />
          </label>
          <label className="block">
            <span className={modalLabelClass}>Notes</span>
            <textarea value={form.notes} onChange={(e) => set('notes', e.target.value)} rows={2} className={`${modalFieldClass} h-auto py-2`} />
          </label>
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="block">
              <span className={modalLabelClass}>Deal stage</span>
              <select
                value={form.deal_stage}
                onChange={(e) => set('deal_stage', e.target.value)}
                className={modalFieldClass}
              >
                <option value="">None</option>
                {DEAL_STAGE_OPTIONS.map((s) => (
                  <option key={s} value={s}>{DEAL_STAGE_META[s]?.label || s}</option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className={modalLabelClass}>Follow-up date</span>
              <DatePicker
                value={form.next_follow_up_date}
                onChange={(v) => set('next_follow_up_date', v)}
                className="mt-1"
              />
            </label>
            <label className="block">
              <span className={modalLabelClass}>Follow-up action</span>
              <input
                value={form.next_follow_up_action}
                onChange={(e) => set('next_follow_up_action', e.target.value)}
                placeholder="e.g. Send proposal"
                className={modalFieldClass}
              />
            </label>
          </div>
          {error?.response?.data?.detail && (
            <div className="rounded-md border border-danger/30 bg-dangerSoft px-3 py-2.5 text-sm text-danger">
              {error.response.data.detail}
            </div>
          )}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className={secondaryBtnClass}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={pending}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-orange px-4 text-sm font-medium text-white transition hover:bg-orangeDark focus:outline-none focus-visible:ring-2 focus-visible:ring-orange/50 disabled:opacity-50"
            >
              {pending ? 'Saving…' : 'Save changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DetailRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="flex items-center gap-1.5 text-muted">
        {icon}
        {label}
      </dt>
      <dd className="text-right text-ink">{value}</dd>
    </div>
  );
}

function FinanceRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border pb-2 last:border-0 last:pb-0">
      <dt className="text-muted">{label}</dt>
      <dd className="font-medium text-ink">{value}</dd>
    </div>
  );
}

function CommunicationModal({
  onClose,
  onSubmit,
  pending,
  error,
}: {
  onClose: () => void;
  onSubmit: (payload: CommunicationInput) => void;
  pending: boolean;
  error: { response?: { data?: { detail?: string } } } | null;
}) {
  const [type, setType] = useState<CommunicationType>('call');
  const [subject, setSubject] = useState('');
  const [notes, setNotes] = useState('');
  const [occurredAt, setOccurredAt] = useState(toISODate(new Date()));

  function submit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      type,
      subject: subject || undefined,
      notes: notes || undefined,
      occurred_at: occurredAt || undefined,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
      <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-lg border border-border bg-surface p-6 shadow-overlay">
        <h2 className="text-lg font-semibold tracking-tight text-ink">Log Communication</h2>
        <form onSubmit={submit} className="mt-4 space-y-4">
          <select
            value={type}
            onChange={(e) => setType(e.target.value as CommunicationType)}
            className={modalFieldClass}
          >
            {COMMUNICATION_TYPE_OPTIONS.map((t) => (
              <option key={t} value={t}>
                {COMMUNICATION_TYPE_LABELS[t]}
              </option>
            ))}
          </select>
          <input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Subject (optional)"
            className={modalFieldClass}
          />
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Notes"
            rows={3}
            className={`${modalFieldClass} h-auto py-2`}
          />
          <label className="block">
            <span className={modalLabelClass}>Date</span>
            <DatePicker value={occurredAt} onChange={setOccurredAt} className="mt-1" />
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
            <button
              type="submit"
              disabled={pending}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-orange px-4 text-sm font-medium text-white transition hover:bg-orangeDark focus:outline-none focus-visible:ring-2 focus-visible:ring-orange/50 disabled:opacity-50"
            >
              {pending ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
