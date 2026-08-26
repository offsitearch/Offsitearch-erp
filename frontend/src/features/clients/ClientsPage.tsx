import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Building2, ChevronLeft, ChevronRight, Clock, Mail, Phone, Plus, RefreshCw, Search, UserRound, X } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { createClient, getClients } from '../../api/clients';
import { Modal } from '../../components/Modal';
import { Skeleton } from '../../components/ui/Skeleton';
import DatePicker from '../../components/ui/DatePicker';
import { clientTypeLabel, clientTypeMeta, CLIENT_TYPE_OPTIONS, DEAL_STAGE_META, DEAL_STAGE_OPTIONS } from '../../lib/constants';
import { formatDate } from '../../lib/date';
import type { ClientCreateInput, ClientType } from '../../lib/types';
import { useAuthStore } from '../../store/authStore';
import { canAccess } from '../../lib/constants';
import { useTranslation } from 'react-i18next';
import { encodeId } from '../../lib/obfuscate';
import { inputClass, primaryBtnClass, secondaryBtnClass, pageBtnClass, labelClass } from '../../lib/styles';

const fieldClass = `${inputClass} w-full`;

function ClientCard({ client }: { client: import('../../lib/types').ClientListItem }) {
  const me = useAuthStore((s) => s.user);
  const canSeeMoney = canAccess(me?.org_level_code, 'L1');
  const meta = clientTypeMeta(client.client_type);
  return (
    <Link
      to={`/clients/${encodeId(client.id)}`}
      className="group flex flex-col rounded-lg border border-border bg-surface p-5 shadow-card transition hover:border-navy/40 hover:shadow-overlay focus:outline-none focus-visible:ring-2 focus-visible:ring-navy/40"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-navy/5 text-navy">
          {client.client_type === 'individual' ? (
            <UserRound className="h-5 w-5" />
          ) : (
            <Building2 className="h-5 w-5" />
          )}
        </span>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${meta.badge}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
          {meta.label}
        </span>
      </div>

      <h3 className="mt-4 text-base font-semibold tracking-tight text-ink">{client.name}</h3>
      {client.company_name && <p className="mt-0.5 text-xs text-muted">{client.company_name}</p>}

      {(client.source || (canSeeMoney && client.budget_range) || client.deal_stage) && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {client.source && (
            <span className="inline-flex items-center rounded-full bg-navy/5 px-2.5 py-0.5 text-xs font-medium text-navy">
              {client.source}
            </span>
          )}
          {canSeeMoney && client.budget_range && (
            <span className="inline-flex items-center rounded-full bg-orange/10 px-2.5 py-0.5 text-xs font-medium text-orangeDark">
              {client.budget_range}
            </span>
          )}
          {client.deal_stage && (
            <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${DEAL_STAGE_META[client.deal_stage]?.badge || 'bg-surfaceWarm text-muted'}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${DEAL_STAGE_META[client.deal_stage]?.dot || 'bg-muted'}`} />
              {DEAL_STAGE_META[client.deal_stage]?.label || client.deal_stage}
            </span>
          )}
        </div>
      )}

      <div className="flex-1" />

      {client.next_follow_up_date && (
        <div className="mt-3 flex items-center gap-1 text-xs text-muted">
          <Clock className="h-3 w-3" />
          Follow up: {formatDate(client.next_follow_up_date)}
        </div>
      )}

      <div className="mt-4 space-y-1 text-sm">
        {client.contact_person && (
          <p className="flex items-center gap-1.5 text-ink">
            <UserRound className="h-3.5 w-3.5 shrink-0 text-muted" />
            {client.contact_person}
          </p>
        )}
        {client.phone && (
          <p className="flex items-center gap-1.5 text-muted">
            <Phone className="h-3.5 w-3.5 shrink-0" />
            {client.phone}
          </p>
        )}
        {client.email && (
          <p className="flex items-center gap-1.5 text-muted">
            <Mail className="h-3.5 w-3.5 shrink-0" />
            {client.email}
          </p>
        )}
      </div>

      <div className="mt-4 border-t border-border pt-3 text-xs text-muted">
        <span className="font-semibold text-ink">{client.project_count}</span> active project
        {client.project_count === 1 ? '' : 's'}
      </div>
    </Link>
  );
}

export default function ClientsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const me = useAuthStore((s) => s.user);
  const [search, setSearch] = useState('');
  const [type, setType] = useState('');
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);

  const filtersActive = Boolean(search || type);

  const clients = useQuery({
    queryKey: ['clients', search, type, page],
    queryFn: () =>
      getClients({
        search: search || undefined,
        client_type: type || undefined,
        page,
        page_size: 12,
      }),
  });

  const createMutation = useMutation({
    mutationFn: createClient,
    onSuccess: () => {
      setShowCreate(false);
      queryClient.invalidateQueries({ queryKey: ['clients'] });
    },
  });

  const total = clients.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / 12));

  function clearFilters() {
    setSearch('');
    setType('');
    setPage(1);
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">{t('clients.title')}</h1>
          <p className="mt-1 text-sm text-muted">
            {t('clients.everyClient')}
          </p>
        </div>
        <button onClick={() => setShowCreate(true)} className={primaryBtnClass}>
          <Plus className="h-4 w-4" />
          Add Client
        </button>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <label className="relative block">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search name, company, email…"
            className={`${inputClass} w-full sm:w-72 pl-9`}
          />
        </label>
        <select
          value={type}
          onChange={(e) => {
            setType(e.target.value);
            setPage(1);
          }}
          className={inputClass}
        >
          <option value="">All types</option>
          {CLIENT_TYPE_OPTIONS.map((t) => (
            <option key={t} value={t}>
              {clientTypeLabel(t)}
            </option>
          ))}
        </select>
        {filtersActive && (
          <button onClick={clearFilters} className={secondaryBtnClass}>
            <X className="h-4 w-4" />
            Clear filters
          </button>
        )}
        {!clients.isPending && clients.data && (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 py-1 text-xs font-medium text-ink">
            {total} {total === 1 ? 'client' : 'clients'}
          </span>
        )}
      </div>

      {clients.isPending ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-52 w-full" />
          ))}
        </div>
      ) : clients.isError ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border px-4 py-16 text-center">
          <AlertCircle className="h-6 w-6 text-danger" />
          <p className="text-sm font-medium text-ink">{t('clients.couldntBeLoaded')}</p>
          <button onClick={() => clients.refetch()} className={secondaryBtnClass}>
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </button>
        </div>
      ) : clients.data?.items.length === 0 ? (
        filtersActive ? (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border px-4 py-16 text-center">
            <Search className="h-8 w-8 text-border" />
            <p className="text-sm font-medium text-ink">{t('clients.noClientsMatch')}</p>
            <p className="text-xs text-muted">{t('clients.tryAdjusting')}</p>
            <button onClick={clearFilters} className={`${secondaryBtnClass} mt-3`}>
              <X className="h-4 w-4" />
              Clear filters
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border px-4 py-16 text-center">
            <Building2 className="h-8 w-8 text-border" />
            <p className="text-sm font-medium text-ink">{t('clients.noClientsYet')}</p>
            <p className="text-xs text-muted">{t('clients.addFirstClient')}</p>
            <button onClick={() => setShowCreate(true)} className={`${primaryBtnClass} mt-3`}>
              <Plus className="h-4 w-4" />
              Add Client
            </button>
          </div>
        )
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {clients.data?.items.map((c) => (
              <ClientCard key={c.id} client={c} />
            ))}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
            <span>
              Showing {total === 0 ? 0 : (page - 1) * 12 + 1}–{Math.min(page * 12, total)} of {total}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className={pageBtnClass}
              >
                <ChevronLeft className="h-4 w-4" />
                Prev
              </button>
              <button
                onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
                disabled={page >= pageCount}
                className={pageBtnClass}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </>
      )}

      {showCreate && (
        <Modal onClose={() => setShowCreate(false)} maxWidth="max-w-md">
          <CreateClientModal
            canEditMoney={canAccess(me?.org_level_code, 'L1')}
            onClose={() => setShowCreate(false)}
            onSubmit={(payload) => createMutation.mutate(payload)}
            pending={createMutation.isPending}
            error={createMutation.error as { response?: { data?: { detail?: string } } } | null}
          />
        </Modal>
      )}
    </div>
  );
}

function CreateClientModal({
  canEditMoney,
  onClose,
  onSubmit,
  pending,
  error,
}: {
  // budget_range is a deal value: executive-only (L0/L1) per the financial policy.
  canEditMoney?: boolean;
  onClose: () => void;
  onSubmit: (payload: ClientCreateInput) => void;
  pending: boolean;
  error: { response?: { data?: { detail?: string } } } | null;
}) {
  const showBudget = canEditMoney ?? true;
  const [name, setName] = useState('');
  const [clientType, setClientType] = useState<ClientType>('individual');
  const [companyName, setCompanyName] = useState('');
  const [contactPerson, setContactPerson] = useState('');
  const [phone, setPhone] = useState('');
  const [phoneSecondary, setPhoneSecondary] = useState('');
  const [email, setEmail] = useState('');
  const [address, setAddress] = useState('');
  const [gstNumber, setGstNumber] = useState('');
  const [source, setSource] = useState('');
  const [panNumber, setPanNumber] = useState('');
  const [budgetRange, setBudgetRange] = useState('');
  const [interest, setInterest] = useState('');
  const [dealStage, setDealStage] = useState('');
  const [nextFollowUpDate, setNextFollowUpDate] = useState('');
  const [nextFollowUpAction, setNextFollowUpAction] = useState('');

  function submit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      name,
      client_type: clientType,
      company_name: companyName || undefined,
      contact_person: contactPerson || undefined,
      phone: phone || undefined,
      phone_secondary: phoneSecondary || undefined,
      email: email || undefined,
      address: address || undefined,
      gst_number: gstNumber || undefined,
      source: source || undefined,
      pan_number: panNumber || undefined,
      ...(showBudget ? { budget_range: budgetRange || undefined } : {}),
      interest: interest || undefined,
      deal_stage: dealStage || undefined,
      next_follow_up_date: nextFollowUpDate || null,
      next_follow_up_action: nextFollowUpAction || undefined,
    });
  }

  return (
    <div className="w-full max-w-md rounded-lg border border-border bg-surface p-6 shadow-overlay">
      <h2 className="text-lg font-semibold tracking-tight text-ink">Add Client</h2>
      <form onSubmit={submit} className="mt-4 space-y-4">
        <label className="block">
          <span className={labelClass}>Client name</span>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Client name"
            className={fieldClass}
          />
        </label>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="block">
            <span className={labelClass}>Type</span>
            <select
              value={clientType}
              onChange={(e) => setClientType(e.target.value as ClientType)}
              className={fieldClass}
            >
              {CLIENT_TYPE_OPTIONS.map((t) => (
                <option key={t} value={t}>
                  {clientTypeLabel(t)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className={labelClass}>Company (if any)</span>
            <input
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Company"
              className={fieldClass}
            />
          </label>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="block">
            <span className={labelClass}>Contact person</span>
            <input
              value={contactPerson}
              onChange={(e) => setContactPerson(e.target.value)}
              placeholder="Contact person"
              className={fieldClass}
            />
          </label>
          <label className="block">
            <span className={labelClass}>Phone</span>
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="Phone"
              className={fieldClass}
            />
          </label>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="block">
            <span className={labelClass}>Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              className={fieldClass}
            />
          </label>
          <label className="block">
            <span className={labelClass}>Source</span>
            <input
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="Referral, walk-in…"
              className={fieldClass}
            />
          </label>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="block">
            <span className={labelClass}>Alt phone</span>
            <input
              value={phoneSecondary}
              onChange={(e) => setPhoneSecondary(e.target.value)}
              placeholder="Alternate phone"
              className={fieldClass}
            />
          </label>
          <label className="block">
            <span className={labelClass}>PAN number</span>
            <input
              value={panNumber}
              onChange={(e) => setPanNumber(e.target.value)}
              placeholder="PAN"
              className={fieldClass}
            />
          </label>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {showBudget && (
            <label className="block">
              <span className={labelClass}>Budget range</span>
              <input
                value={budgetRange}
                onChange={(e) => setBudgetRange(e.target.value)}
                placeholder="e.g. 15–25L"
                className={fieldClass}
              />
            </label>
          )}
          <label className="block">
            <span className={labelClass}>Interest</span>
            <input
              value={interest}
              onChange={(e) => setInterest(e.target.value)}
              placeholder="Interests / preferences"
              className={fieldClass}
            />
          </label>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <label className="block">
            <span className={labelClass}>Deal stage</span>
            <select
              value={dealStage}
              onChange={(e) => setDealStage(e.target.value)}
              className={fieldClass}
            >
              <option value="">None</option>
              {DEAL_STAGE_OPTIONS.map((s) => (
                <option key={s} value={s}>{DEAL_STAGE_META[s]?.label || s}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className={labelClass}>Follow-up date</span>
            <DatePicker value={nextFollowUpDate} onChange={setNextFollowUpDate} className="mt-1" />
          </label>
          <label className="block">
            <span className={labelClass}>Follow-up action</span>
            <input
              value={nextFollowUpAction}
              onChange={(e) => setNextFollowUpAction(e.target.value)}
              placeholder="e.g. Send proposal"
              className={fieldClass}
            />
          </label>
        </div>
        <label className="block">
          <span className={labelClass}>Address</span>
          <textarea
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Billing address — street, city, state, PIN"
            rows={2}
            className={`${fieldClass} h-auto py-2`}
          />
        </label>
        <label className="block">
          <span className={labelClass}>GSTIN (optional)</span>
          <input
            value={gstNumber}
            onChange={(e) => setGstNumber(e.target.value)}
            placeholder="e.g. 29AABCS1429B1Z1"
            className={fieldClass}
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
            {pending ? 'Creating…' : 'Create Client'}
          </button>
        </div>
      </form>
    </div>
  );
}
