import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Network, Pencil, RefreshCw } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { getOrgChart, getOrgLevels, updateEmployee } from '../../api/employees';
import { canAccess, LEVEL_LABELS, LEVEL_ORDER, levelLabel, levelRank } from '../../lib/constants';
import type { LevelCode } from '../../lib/constants';
import type { OrgChartNode } from '../../lib/types';
import { useAuthStore } from '../../store/authStore';
import { encodeId } from '../../lib/obfuscate';
import { EmployeeTabs } from './components/EmployeeTabs';
import { EmptyState } from '../../components/ui/EmptyState';
import { LogoLoader } from '../../components/LogoLoader';
import { useTranslation } from 'react-i18next';
import { smallBtnClass, modalFieldClass, modalLabelClass, primaryBtnClass, secondaryBtnClass } from '../../lib/styles';

function initials(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

// Tiers are keyed by organizational level (L1–L6), not by RBAC role —
// levels describe seniority only and never grant permissions.
const TIER_STYLES: Record<string, { border: string; bg: string; dot: string; labelBg: string; labelText: string }> = {
  L1: {
    border: 'border-danger/40',
    bg: 'bg-danger/5',
    dot: 'bg-danger',
    labelBg: 'bg-danger/10',
    labelText: 'text-danger',
  },
  L2: {
    border: 'border-orange/40',
    bg: 'bg-orange/5',
    dot: 'bg-orange',
    labelBg: 'bg-orange/10',
    labelText: 'text-orange',
  },
  L3: {
    border: 'border-navy/40',
    bg: 'bg-navy/5',
    dot: 'bg-navy',
    labelBg: 'bg-navy/10',
    labelText: 'text-navy',
  },
  L4: {
    border: 'border-orangeDark/40',
    bg: 'bg-orangeDark/5',
    dot: 'bg-orangeDark',
    labelBg: 'bg-orangeDark/10',
    labelText: 'text-orangeDark',
  },
  L5: {
    border: 'border-graphite/30',
    bg: 'bg-graphite/5',
    dot: 'bg-graphite',
    labelBg: 'bg-graphite/10',
    labelText: 'text-graphite',
  },
  L6: {
    border: 'border-success/40',
    bg: 'bg-success/5',
    dot: 'bg-success',
    labelBg: 'bg-success/10',
    labelText: 'text-success',
  },
};

const UNASSIGNED_STYLE = TIER_STYLES.L5;

interface FlatPerson {
  user_id: number;
  name: string;
  designation: string | null;
  department_name: string | null;
  org_level_code: string | null;
  org_level_name: string | null;
}

interface TierGroup {
  code: string;
  label: string;
  people: FlatPerson[];
}

interface DepartmentGroup {
  name: string;
  people: FlatPerson[];
}

function flattenTree(nodes: OrgChartNode[]): FlatPerson[] {
  const result: FlatPerson[] = [];
  const seen = new Set<number>();
  function walk(list: OrgChartNode[]) {
    for (const node of list) {
      if (!seen.has(node.user_id)) {
        seen.add(node.user_id);
        result.push({
          user_id: node.user_id,
          name: node.name,
          designation: node.designation,
          department_name: node.department_name ?? null,
          org_level_code: node.org_level_code ?? null,
          org_level_name: node.org_level_name ?? null,
        });
      }
      if (node.children.length > 0) walk(node.children);
    }
  }
  walk(nodes);
  return result;
}

/** Splits a tier's people into k-ary department branches ("No department" last). */
function groupByDepartment(people: FlatPerson[]): DepartmentGroup[] {
  const grouped = new Map<string, FlatPerson[]>();
  for (const p of people) {
    const key = p.department_name ?? '__none__';
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(p);
  }
  const entries = [...grouped.entries()];
  entries.sort((a, b) => {
    if (a[0] === '__none__') return 1;
    if (b[0] === '__none__') return -1;
    return a[0].localeCompare(b[0]);
  });
  return entries.map(([name, people]) => ({
    name: name === '__none__' ? '' : name,
    people: people.sort((a, b) => a.name.localeCompare(b.name)),
  }));
}

function PersonCard({
  person,
  isAdmin,
  onPromote,
}: {
  person: FlatPerson;
  isAdmin: boolean;
  onPromote: (person: FlatPerson) => void;
}) {
  const tier = TIER_STYLES[person.org_level_code ?? ''] ?? UNASSIGNED_STYLE;
  return (
    <div className="group relative">
      <Link
        to={`/employees/${encodeId(person.user_id)}`}
        className={`flex flex-col items-center rounded-lg border ${tier.border} ${tier.bg} px-4 py-3 text-center shadow-card transition hover:shadow-overlay`}
      >
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white/80 text-xs font-semibold text-navy shadow-sm">
          {initials(person.name)}
        </span>
        <p className="mt-2 truncate text-sm font-medium text-ink max-w-[8rem] hover:underline">{person.name}</p>
        {person.designation && (
          <p className="truncate text-xs text-muted max-w-[8rem]">{person.designation}</p>
        )}
        {person.org_level_code && (
          <span
            className="mt-1.5 rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-navy"
            title={person.org_level_name ?? undefined}
          >
            {person.org_level_code} · {levelLabel(person.org_level_code)}
          </span>
        )}
      </Link>
      {isAdmin && (
        <button
          onClick={() => onPromote(person)}
          className="absolute -right-1.5 -top-1.5 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-border bg-surface text-muted shadow-card opacity-0 transition group-hover:opacity-100 hover:text-ink"
          title="Edit designation / level"
        >
          <Pencil className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}

function DepartmentBranch({
  group,
  isAdmin,
  onPromote,
  noDepartmentLabel,
}: {
  group: DepartmentGroup;
  isAdmin: boolean;
  onPromote: (person: FlatPerson) => void;
  noDepartmentLabel: string;
}) {
  return (
    <div className="flex flex-col items-center">
      <div className="h-4 w-px bg-border" />
      <div className="rounded-lg border border-border bg-surfaceWarm/50 px-3 py-3">
        <div className="mb-3 flex items-center justify-center gap-1.5 border-b border-border/70 pb-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-graphite">
            {group.name || noDepartmentLabel}
          </span>
          <span className="rounded-full bg-navy/10 px-1.5 py-0.5 text-[10px] font-medium text-navy">
            {group.people.length}
          </span>
        </div>
        <div className="flex flex-wrap justify-center gap-3">
          {group.people.map((person) => (
            <PersonCard key={person.user_id} person={person} isAdmin={isAdmin} onPromote={onPromote} />
          ))}
        </div>
      </div>
    </div>
  );
}

function TierRow({
  tier,
  isAdmin,
  onPromote,
  isLast,
  noDepartmentLabel,
}: {
  tier: TierGroup;
  isAdmin: boolean;
  onPromote: (person: FlatPerson) => void;
  isLast: boolean;
  noDepartmentLabel: string;
}) {
  const style = TIER_STYLES[tier.code] ?? UNASSIGNED_STYLE;
  const departments = useMemo(() => groupByDepartment(tier.people), [tier.people]);
  return (
    <div className="flex flex-col items-center">
      {!isLast && <div className="h-8 w-px bg-border" />}
      <div className="flex flex-col items-center rounded-xl border border-border bg-surface px-4 py-4 sm:px-6 sm:py-5 shadow-card">
        <div className="mb-4 flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${style.dot}`} />
          <span className={`text-xs font-semibold uppercase tracking-wider ${style.labelText}`}>
            {tier.label}
          </span>
          <span className={`rounded-full ${style.labelBg} px-2 py-0.5 text-[11px] font-medium ${style.labelText}`}>
            {tier.people.length}
          </span>
        </div>
        <div className="flex flex-wrap items-start justify-center gap-3">
          {departments.map((group) => (
            <DepartmentBranch
              key={group.name || '__none__'}
              group={group}
              isAdmin={isAdmin}
              onPromote={onPromote}
              noDepartmentLabel={noDepartmentLabel}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default function OrgChartPage() {
  const { t } = useTranslation();
  const currentUser = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const [promoting, setPromoting] = useState<FlatPerson | null>(null);

  const isAdmin = canAccess(currentUser?.org_level_code, 'L1');

  const chart = useQuery({ queryKey: ['employees', 'org-chart'], queryFn: getOrgChart });

  const tiers = useMemo(() => {
    if (!chart.data || chart.data.length === 0) return [];
    const people = flattenTree(chart.data);
    const grouped = new Map<string, FlatPerson[]>();
    for (const p of people) {
      const code = p.org_level_code ?? 'none';
      if (!grouped.has(code)) grouped.set(code, []);
      grouped.get(code)!.push(p);
    }
    const orderedCodes = [...LEVEL_ORDER, 'none'] as const;
    return orderedCodes
      .filter((code) => grouped.has(code) && grouped.get(code)!.length > 0)
      .map((code) => ({
        code,
        label: code === 'none' ? 'Level not set' : `${code} · ${LEVEL_LABELS[code]}`,
        people: grouped.get(code)!.sort((a, b) => a.name.localeCompare(b.name)),
      }));
  }, [chart.data]);

  const promoteMutation = useMutation({
    mutationFn: ({
      userId,
      payload,
    }: {
      userId: number;
      payload: { designation?: string; org_level_id?: number };
    }) => updateEmployee(userId, payload),
    onSuccess: () => {
      setPromoting(null);
      queryClient.invalidateQueries({ queryKey: ['employees'] });
    },
  });

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">{t('employees.title')}</h1>
           <p className="mt-1 text-sm text-muted">{t('employees.orgChartSubtitle')}</p>
        </div>
        <EmployeeTabs level={currentUser?.org_level_code} />
      </header>

      <section className="overflow-x-auto rounded-lg border border-border bg-paper/40 shadow-card">
        {chart.isPending ? (
          <LogoLoader />
        ) : chart.isError ? (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <AlertCircle className="h-6 w-6 text-danger" />
             <p className="text-sm font-medium text-ink">{t('employees.couldntLoadOrgChart')}</p>
            <button onClick={() => chart.refetch()} className={smallBtnClass}>
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </button>
          </div>
        ) : tiers.length === 0 ? (
          <EmptyState
            icon={Network}
            title={t('employees.noEmployeesYet')}
            text={t('employees.addEmployeesSeeHierarchy')}
          />
        ) : (
          <div className="flex flex-col items-center gap-0 p-4 sm:p-8">
            {tiers.map((tier, i) => (
              <TierRow
                key={tier.code}
                tier={tier}
                isAdmin={isAdmin}
                onPromote={setPromoting}
                isLast={i === tiers.length - 1}
                noDepartmentLabel={t('employees.noDepartment')}
              />
            ))}
          </div>
        )}
      </section>

      {promoting && (
        <PromoteModal
          person={promoting}
          pending={promoteMutation.isPending}
          error={promoteMutation.error as { response?: { data?: { detail?: string } } } | null}
          onClose={() => {
            setPromoting(null);
            promoteMutation.reset();
          }}
          onSubmit={(payload) => promoteMutation.mutate({ userId: promoting.user_id, payload })}
        />
      )}
    </div>
  );
}

function PromoteModal({
  person,
  pending,
  error,
  onClose,
  onSubmit,
}: {
  person: FlatPerson;
  pending: boolean;
  error: { response?: { data?: { detail?: string } } } | null;
  onClose: () => void;
  onSubmit: (payload: { designation?: string; org_level_id?: number }) => void;
}) {
  const currentUser = useAuthStore((s) => s.user);
  const [designation, setDesignation] = useState(person.designation ?? '');
  const [orgLevelId, setOrgLevelId] = useState<number | ''>('');
  const orgLevels = useQuery({ queryKey: ['org-levels'], queryFn: getOrgLevels });
  const { t } = useTranslation();

  const sortedLevels = useMemo(
    () => [...(orgLevels.data ?? [])].sort((a, b) => a.rank - b.rank),
    [orgLevels.data],
  );

  // Resolves once the levels query finishes loading.
  const currentLevelId = sortedLevels.find((l) => l.code === person.org_level_code)?.id;

  useEffect(() => {
    if (orgLevelId === '' && currentLevelId !== undefined) setOrgLevelId(currentLevelId);
  }, [currentLevelId, orgLevelId]);

  // Nobody can target a level more senior than their own; non-L0/L1
  // actors additionally cannot assign a level as senior as their own.
  const actorIsExecutive = canAccess(currentUser?.org_level_code, 'L1');
  const actorRank = levelRank(currentUser?.org_level_code);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload: { designation?: string; org_level_id?: number } = {};
    if (designation !== (person.designation ?? '')) payload.designation = designation || undefined;
    if (orgLevelId !== '' && orgLevelId !== currentLevelId) payload.org_level_id = orgLevelId;
    if (Object.keys(payload).length === 0) return;
    onSubmit(payload);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
      <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-lg border border-border bg-surface p-6 shadow-overlay">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-navy/5 text-sm font-semibold text-navy">
            {initials(person.name)}
          </span>
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-ink">{person.name}</h2>
             <p className="text-sm text-muted">{t('employees.updateRoleDesignation')}</p>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <label className="block">
            <span className={modalLabelClass}>Designation</span>
            <input
              value={designation}
              onChange={(e) => setDesignation(e.target.value)}
              placeholder="e.g. Senior Architect"
              className={modalFieldClass}
            />
          </label>
          <label className="block">
            <span className={modalLabelClass}>Org level</span>
            <select
              value={orgLevelId}
              onChange={(e) => setOrgLevelId(e.target.value === '' ? '' : Number(e.target.value))}
              className={modalFieldClass}
            >
              <option value="">Not set</option>
              {sortedLevels.map((l) => (
                <option
                  key={l.id}
                  value={l.id}
                  disabled={
                    levelRank(l.code) < actorRank ||
                    (!actorIsExecutive && levelRank(l.code) === actorRank)
                  }
                >
                  {l.code} — {LEVEL_LABELS[l.code as LevelCode] ?? l.name}
                </option>
              ))}
            </select>
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
              {pending ? t('common.loading') : t('common.update')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
