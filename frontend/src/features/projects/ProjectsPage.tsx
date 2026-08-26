import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  Building2,
  ChevronLeft,
  ChevronRight,
  FolderKanban,
  MapPin,
  Plus,
  RefreshCw,
  Search,
  X,
} from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { getClients } from '../../api/clients';
import { getEmployees } from '../../api/employees';
import { createProject, getPhaseTemplates, getProjects } from '../../api/projects';
import { EmptyState } from '../../components/ui/EmptyState';
import { LogoLoader } from '../../components/LogoLoader';
import {
  canAccess,
  formatINR,
  levelRank,
  projectTypeLabel,
  PROJECT_STATUS_OPTIONS,
  PROJECT_TYPE_OPTIONS,
} from '../../lib/constants';
import { toISODate } from '../../lib/date';
import { parseIndianCurrencyInput } from '../../lib/currencyInput';
import CurrencyInput from '../../components/ui/CurrencyInput';
import type { ProjectCreateInput, ProjectListItem, ProjectType } from '../../lib/types';
import { useAuthStore } from '../../store/authStore';
import { encodeId } from '../../lib/obfuscate';
import { ProjectStatusBadge } from './components/ProjectStatusBadge';
import DatePicker from '../../components/ui/DatePicker';
import { useTranslation } from 'react-i18next';
import { inputClass, primaryBtnClass, secondaryBtnClass, pageBtnClass, labelClass } from '../../lib/styles';

const fieldClass = `${inputClass} w-full`;

function ProjectCard({ project }: { project: ProjectListItem }) {
  const me = useAuthStore((s) => s.user);
  const canSeeMoney = canAccess(me?.org_level_code, 'L1');
  const raw = Number(project.progress_pct) || 0;
  const progress = Math.min(raw, 100);
  const progressLabel = parseFloat(progress.toFixed(2));
  return (
    <Link
      to={`/projects/${encodeId(project.id)}`}
      className="group flex flex-col rounded-lg border border-border bg-surface p-5 shadow-card transition hover:border-orange/40 hover:shadow-overlay focus:outline-none focus-visible:ring-2 focus-visible:ring-navy/40"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-navy/5 text-navy">
          <FolderKanban className="h-5 w-5" />
        </span>
        <ProjectStatusBadge status={project.status} />
      </div>

      <h3 className="mt-4 text-lg font-semibold tracking-tight text-ink group-hover:text-navyDark">
        {project.name}
      </h3>
      <p className="mt-0.5 text-xs text-muted">
        {project.project_code} · {projectTypeLabel(project.project_type)}
      </p>

      {project.client_name && (
        <p className="mt-4 flex items-center gap-1.5 text-sm font-medium text-ink">
          <Building2 className="h-3.5 w-3.5 shrink-0 text-muted" />
          {project.client_name}
        </p>
      )}
      {project.location && (
        <p className="mt-1 flex items-center gap-1.5 text-xs text-muted">
          <MapPin className="h-3 w-3 shrink-0" />
          {project.location}
        </p>
      )}

      <div className="flex-1" />

      <div className="mt-5 border-t border-border pt-4">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted">Progress</span>
          <span className="font-medium tabular-nums text-ink">{progressLabel}%</span>
        </div>
        <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-border/70">
          <div
            className={`h-full rounded-full transition-all ${progress > 0 ? 'bg-success' : ''}`}
            style={{ width: `${progress}%` }}
          />
        </div>
        {canSeeMoney && project.studio_fee && (
          <div className="mt-3 flex items-center justify-between text-xs">
            <span className="text-muted">Studio fee</span>
            <span className="font-medium tabular-nums text-graphite">{formatINR(project.studio_fee)}</span>
          </div>
        )}
        {project.hours_logged !== null && (
          <div className="mt-1.5 flex items-center justify-between text-xs">
            <span className="text-muted">Hours logged</span>
            <span className="font-medium tabular-nums text-graphite">
              {Number(project.hours_logged)}h
              {canSeeMoney && project.studio_fee && Number(project.studio_fee) > 0 && (
                <span className="ml-1 text-muted">
                  · {formatINR(Number(project.studio_fee) / Number(project.hours_logged))}/hr
                </span>
              )}
            </span>
          </div>
        )}
      </div>
    </Link>
  );
}

export default function ProjectsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [type, setType] = useState('');
  const [status, setStatus] = useState('');
  const [clientFilter, setClientFilter] = useState('');
  const [leadFilter, setLeadFilter] = useState('');
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);

  const filtersActive = Boolean(search || type || status || clientFilter || leadFilter);

  const projects = useQuery({
    queryKey: ['projects', search, type, status, clientFilter, leadFilter, page],
    queryFn: () =>
      getProjects({
        search: search || undefined,
        project_type: type || undefined,
        status: status || undefined,
        client_id: clientFilter === '' ? undefined : Number(clientFilter),
        lead_id: leadFilter === '' ? undefined : Number(leadFilter),
        page,
        page_size: 9,
      }),
  });

  const clients = useQuery({ queryKey: ['clients-options'], queryFn: () => getClients({ page_size: 100 }) });
  const employees = useQuery({
    queryKey: ['employees-options'],
    queryFn: () => getEmployees({ active_only: true, page_size: 100 }),
  });
  const templates = useQuery({ queryKey: ['phase-templates'], queryFn: getPhaseTemplates });

  const createMutation = useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      setShowCreate(false);
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });

  const total = projects.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / 9));

  const me = useAuthStore((s) => s.user);
  const canCreate = canAccess(me?.org_level_code, 'L3');

  function clearFilters() {
    setSearch('');
    setType('');
    setStatus('');
    setClientFilter('');
    setLeadFilter('');
    setPage(1);
  }

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-ink">{t('projects.title')}</h1>
            <p className="mt-1 text-sm text-muted">
              Phases, teams and timelines across the studio.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {canCreate && (
              <button onClick={() => setShowCreate(true)} className={primaryBtnClass}>
                <Plus className="h-4 w-4" />
                New Project
              </button>
            )}
          </div>
        </div>
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
            placeholder="Search name or code…"
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
          {PROJECT_TYPE_OPTIONS.map((t) => (
            <option key={t} value={t}>
              {projectTypeLabel(t)}
            </option>
          ))}
        </select>
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
          className={inputClass}
        >
          <option value="">All statuses</option>
          {PROJECT_STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {projectStatusLabel(s)}
            </option>
          ))}
        </select>
        <select
          value={clientFilter}
          onChange={(e) => {
            setClientFilter(e.target.value);
            setPage(1);
          }}
          className={`${inputClass} max-w-48`}
        >
          <option value="">All clients</option>
          {(clients.data?.items ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          value={leadFilter}
          onChange={(e) => {
            setLeadFilter(e.target.value);
            setPage(1);
          }}
          className={`${inputClass} max-w-48`}
        >
          <option value="">All leads</option>
          {(employees.data?.items ?? []).map((e) => (
            <option key={e.id} value={e.id}>
              {e.name}
            </option>
          ))}
        </select>
        {filtersActive && (
          <button onClick={clearFilters} className={secondaryBtnClass}>
            <X className="h-4 w-4" />
            Clear filters
          </button>
        )}
        {!projects.isPending && projects.data && (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 py-1 text-xs font-medium text-ink">
            {total} {total === 1 ? 'project' : 'projects'}
          </span>
        )}
      </div>

      {projects.isPending ? (
        <LogoLoader />
      ) : projects.isError ? (
        <EmptyState
          icon={AlertCircle}
          title={t('projects.couldntBeLoaded')}
          action={
            <button onClick={() => projects.refetch()} className={`${secondaryBtnClass} mt-2`}>
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </button>
          }
        />
      ) : projects.data?.items.length === 0 ? (
        filtersActive ? (
          <EmptyState
            icon={Search}
            title={t('projects.noProjectsMatch')}
            text={t('projects.tryAdjusting')}
            action={
              <button onClick={clearFilters} className={`${secondaryBtnClass} mt-2`}>
                <X className="h-4 w-4" />
                Clear filters
              </button>
            }
          />
        ) : (
          <EmptyState
            icon={FolderKanban}
            title={t('projects.noProjectsYet')}
            text={`${t('projects.startOne')} — phases are generated from the type template automatically.`}
            action={
              canCreate ? (
                <button onClick={() => setShowCreate(true)} className={`${primaryBtnClass} mt-2`}>
                  <Plus className="h-4 w-4" />
                  New Project
                </button>
              ) : undefined
            }
          />
        )
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {projects.data?.items.map((p) => (
              <ProjectCard key={p.id} project={p} />
            ))}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
            <span>
              Showing {total === 0 ? 0 : (page - 1) * 9 + 1}–{Math.min(page * 9, total)} of {total}
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
          <CreateProjectModal
            clients={(clients.data?.items ?? []).map((c) => ({ id: c.id, name: c.name }))}
            leadOptions={(employees.data?.items ?? [])
              .filter((e) => e.org_level_code && levelRank(e.org_level_code) <= 3)
              .map((e) => ({ id: e.id, name: e.name }))}
            templates={templates.data ?? []}
            forceLeadId={
              canAccess(me?.org_level_code, 'L3') && !canAccess(me?.org_level_code, 'L2')
                ? (me?.id ?? null)
                : null
            }
            onClose={() => setShowCreate(false)}
            onSubmit={(payload) => createMutation.mutate(payload)}
            pending={createMutation.isPending}
            error={createMutation.error as { response?: { data?: { detail?: string } } } | null}
          />
        </div>
      )}
    </div>
  );
}

function projectStatusLabel(status: string): string {
  return status.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}

function CreateProjectModal({
  clients,
  leadOptions,
  templates,
  forceLeadId,
  onClose,
  onSubmit,
  pending,
  error,
}: {
  clients: { id: number; name: string }[];
  leadOptions: { id: number; name: string }[];
  templates: { project_type: string; label: string; phases: string[] }[];
  forceLeadId: number | null;
  onClose: () => void;
  onSubmit: (payload: ProjectCreateInput) => void;
  pending: boolean;
  error: { response?: { data?: { detail?: string } } } | null;
}) {
  const me = useAuthStore((s) => s.user);
  const canEditMoney = canAccess(me?.org_level_code, 'L1');
  const today = toISODate(new Date());
  const [name, setName] = useState('');
  const [projectType, setProjectType] = useState<ProjectType>('residential');
  const [clientId, setClientId] = useState<number | ''>('');
  const [leadId, setLeadId] = useState<number | ''>(forceLeadId ?? '');
  const [status, setStatus] = useState('draft');
  const [location, setLocation] = useState('');
  const [budget, setBudget] = useState('');
  const [startDate, setStartDate] = useState(today);
  const [endDate, setEndDate] = useState('');
  const [priority, setPriority] = useState('medium');

  const templatePhases = templates.find((t) => t.project_type === projectType)?.phases ?? [];

  function submit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      name,
      project_type: projectType,
      status: status as ProjectCreateInput['status'],
      client_id: clientId === '' ? null : Number(clientId),
      project_lead_id: forceLeadId !== null ? forceLeadId : leadId === '' ? null : Number(leadId),
      location: location || undefined,
      budget: parseIndianCurrencyInput(budget),
      start_date: startDate || null,
      end_date: endDate || null,
      priority,
    });
  }

  return (
    <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-border bg-surface p-6 shadow-overlay">
      <h2 className="text-lg font-semibold tracking-tight text-ink">New Project</h2>
      <p className="mt-0.5 text-sm text-muted">
        Phases ({templatePhases.length}) will be auto-created from the {projectType} template.
      </p>
      <form onSubmit={submit} className="mt-4 space-y-4">
        <label className="block">
          <span className={labelClass}>Project name</span>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Project name"
            className={fieldClass}
          />
        </label>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="block">
            <span className={labelClass}>Type</span>
            <select
              value={projectType}
              onChange={(e) => setProjectType(e.target.value as ProjectType)}
              className={fieldClass}
            >
              {PROJECT_TYPE_OPTIONS.map((t) => (
                <option key={t} value={t}>
                  {projectTypeLabel(t)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className={labelClass}>Status</span>
            <select value={status} onChange={(e) => setStatus(e.target.value)} className={fieldClass}>
              {PROJECT_STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {projectStatusLabel(s)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="block">
            <span className={labelClass}>Client</span>
            <select
              value={clientId}
              onChange={(e) => setClientId(e.target.value === '' ? '' : Number(e.target.value))}
              className={fieldClass}
            >
              <option value="">No client</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className={labelClass}>Project lead</span>
            {forceLeadId !== null ? (
              <div className="flex h-10 items-center rounded-md border border-border bg-surfaceWarm px-3 text-sm text-muted">
                You will lead this project
              </div>
            ) : (
              <select
                value={leadId}
                onChange={(e) => setLeadId(e.target.value === '' ? '' : Number(e.target.value))}
                className={fieldClass}
              >
                <option value="">No project lead</option>
                {leadOptions.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name}
                  </option>
                ))}
              </select>
            )}
          </label>
        </div>
        <label className="block">
          <span className={labelClass}>Location</span>
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Koregaon Park, Pune"
            className={fieldClass}
          />
        </label>
        {canEditMoney && (
          <label className="block">
            <span className={labelClass}>Budget (INR)</span>
            <CurrencyInput value={budget} onChange={setBudget} placeholder="e.g. 25,00,000" className="mt-0" />
          </label>
        )}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <label className="block">
            <span className={labelClass}>Start date</span>
            <DatePicker value={startDate} onChange={setStartDate} className="mt-1" />
          </label>
          <label className="block">
            <span className={labelClass}>End date</span>
            <DatePicker value={endDate} onChange={setEndDate} className="mt-1" />
          </label>
          <label className="block">
            <span className={labelClass}>Priority</span>
            <select value={priority} onChange={(e) => setPriority(e.target.value)} className={fieldClass}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
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
          <button type="submit" disabled={pending} className={primaryBtnClass}>
            {pending ? 'Creating…' : 'Create Project'}
          </button>
        </div>
      </form>
    </div>
  );
}
