import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Building2, Check, ChevronDown, ChevronRight, Copy, Eye, EyeOff, Plus, RefreshCw, RotateCcw, Search } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  createEmployee,
  getDepartments,
  getDepartmentDesignations,
  getEmployees,
  getEmployeeSkills,
  getOrgLevels,
  updateEmployee,
} from '../../api/employees';
import { Modal } from '../../components/Modal';
import { canAccess, LEVEL_BADGE, LEVEL_LABELS, LEVEL_ORDER, levelLabel, levelRank } from '../../lib/constants';
import type { LevelCode } from '../../lib/constants';
import type { EmployeeCreateOut, EmployeeListItem, OrgLevel } from '../../lib/types';
import { useAuthStore } from '../../store/authStore';
import { encodeId } from '../../lib/obfuscate';
import { EmployeeTabs } from './components/EmployeeTabs';
import { EmptyState } from '../../components/ui/EmptyState';
import { LogoLoader } from '../../components/LogoLoader';
import { useTranslation } from 'react-i18next';
import { primaryBtnClass, inputClass, pageBtnClass, secondaryBtnClass } from '../../lib/styles';

const primaryBtnSmallClass =
  'inline-flex h-10 items-center justify-center gap-2 rounded-md bg-orange px-4 text-sm font-medium text-white transition hover:bg-orangeDark focus:outline-none focus-visible:ring-2 focus-visible:ring-orange/50 disabled:cursor-not-allowed disabled:opacity-60';

function initials(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

interface DepartmentGroup {
  name: string;
  employees: EmployeeListItem[];
}

export default function EmployeeDirectoryPage() {
  const { t } = useTranslation();
  const currentUser = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [departmentId, setDepartmentId] = useState<number | ''>('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('active');
  const [skill, setSkill] = useState('');
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const isSuperAdmin = canAccess(currentUser?.org_level_code, 'L1');
  const isAdmin = canAccess(currentUser?.org_level_code, 'L2');

  const departments = useQuery({ queryKey: ['departments'], queryFn: getDepartments });
  const skills = useQuery({ queryKey: ['employees', 'skills'], queryFn: getEmployeeSkills });
  const orgLevels = useQuery({ queryKey: ['org-levels'], queryFn: getOrgLevels });

  const employees = useQuery({
    queryKey: ['employees', search, departmentId, statusFilter, skill, page],
    queryFn: () =>
      getEmployees({
        search: search || undefined,
        department_id: departmentId === '' ? undefined : departmentId,
        skill: skill || undefined,
        active_only: statusFilter === 'active' ? true : false,
        inactive_only: statusFilter === 'inactive' ? true : false,
        page,
        page_size: 50,
      }),
  });

  const [createdCredentials, setCreatedCredentials] = useState<EmployeeCreateOut | null>(null);

  const createMutation = useMutation({
    mutationFn: createEmployee,
    onSuccess: (data) => {
      setShowCreate(false);
      setCreatedCredentials(data);
      queryClient.invalidateQueries({ queryKey: ['employees'] });
    },
  });

  const restoreMutation = useMutation({
    mutationFn: (id: number) => updateEmployee(id, { is_active: true }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['employees'] }),
  });

  const groups = useMemo(() => {
    const empMap = new Map<string, EmployeeListItem[]>();
    if (employees.data?.items) {
      for (const emp of employees.data.items) {
        const dept = emp.department ?? 'Unassigned';
        if (!empMap.has(dept)) empMap.set(dept, []);
        empMap.get(dept)!.push(emp);
      }
    }
    const result: DepartmentGroup[] = [];
    if (departments.data) {
      for (const dept of departments.data) {
        result.push({ name: dept.name, employees: empMap.get(dept.name) ?? [] });
      }
    }
    const assignedNames = new Set(departments.data?.map((d) => d.name) ?? []);
    for (const [name, items] of empMap) {
      if (!assignedNames.has(name)) {
        result.push({ name, employees: items });
      }
    }
    result.sort((a, b) => {
      if (a.name === 'Unassigned') return 1;
      if (b.name === 'Unassigned') return -1;
      return a.name.localeCompare(b.name);
    });
    return result;
  }, [employees.data?.items, departments.data]);

  const total = employees.data?.total ?? 0;

  function toggleGroup(name: string) {
    setCollapsed((prev) => ({ ...prev, [name]: !prev[name] }));
  }

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-ink">{t('employees.title')}</h1>
             <p className="mt-1 text-sm text-muted">{t('employees.directoryOfEveryone')}</p>
          </div>
          {isAdmin && (
            <button onClick={() => setShowCreate(true)} className={primaryBtnClass}>
              <Plus className="h-4 w-4" />
              Add Employee
            </button>
          )}
        </div>
        <EmployeeTabs level={currentUser?.org_level_code} />
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
            placeholder={t('employees.searchPlaceholder')}
            className={`${inputClass} w-full sm:w-72 pl-9`}
          />
        </label>
        <select
          value={departmentId}
          onChange={(e) => {
            setDepartmentId(e.target.value === '' ? '' : Number(e.target.value));
            setPage(1);
          }}
          className={inputClass}
        >
          <option value="">{t('attendance.allDepartments')}</option>
          {departments.data
            ?.filter((d) => d.is_active)
            .map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
        </select>
        <select
          value={skill}
          onChange={(e) => {
            setSkill(e.target.value);
            setPage(1);
          }}
          className={inputClass}
        >
          <option value="">{t('employees.allSkills')}</option>
          {skills.data?.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as 'all' | 'active' | 'inactive');
            setPage(1);
          }}
          className={inputClass}
        >
          <option value="all">{t('employees.allStatuses')}</option>
          <option value="active">{t('employees.activeOnly')}</option>
          <option value="inactive">{t('employees.inactiveOnly')}</option>
        </select>
        {!employees.isPending && employees.data && (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 py-1 text-xs font-medium text-ink">
            {total} {total === 1 ? 'employee' : 'employees'}
          </span>
        )}
      </div>

      {employees.isPending ? (
        <LogoLoader />
      ) : employees.isError ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border px-4 py-12 text-center">
          <AlertCircle className="h-6 w-6 text-danger" />
           <p className="text-sm font-medium text-ink">{t('employees.couldntLoadDirectory')}</p>
          <button onClick={() => employees.refetch()} className={pageBtnClass}>
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </button>
        </div>
      ) : groups.length === 0 ? (
        <EmptyState
          icon={Building2}
          title={t('employees.noEmployeesFound')}
          text={t('employees.tryDifferentSearch')}
        />
      ) : (
        <div className="space-y-4">
          {groups.map((group) => {
            const isCollapsed = collapsed[group.name];
            return (
              <div key={group.name} className="rounded-lg border border-border bg-surface shadow-card">
                <button
                  onClick={() => toggleGroup(group.name)}
                  className="flex w-full items-center gap-3 px-5 py-3.5 text-left transition hover:bg-surfaceWarm"
                >
                  {isCollapsed ? (
                    <ChevronRight className="h-4 w-4 shrink-0 text-muted" />
                  ) : (
                    <ChevronDown className="h-4 w-4 shrink-0 text-muted" />
                  )}
                  <Building2 className="h-4 w-4 shrink-0 text-navy" />
                  <span className="text-sm font-semibold text-ink">{group.name}</span>
                  <span className="rounded-full bg-navy/5 px-2 py-0.5 text-xs font-medium text-navy">
                    {group.employees.length}
                  </span>
                </button>
                {!isCollapsed && (
                  <div className="grid grid-cols-1 gap-3 border-t border-border px-5 py-4 sm:grid-cols-2 lg:grid-cols-3">
                    {group.employees.map((emp) => (
                      <Link
                        key={emp.id}
                        to={`/employees/${encodeId(emp.id)}`}
                        className="group rounded-lg border border-border bg-paper/40 p-4 transition hover:border-orange/40 hover:shadow-card"
                      >
                        <div className="flex items-start gap-3">
                          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-navy/5 text-xs font-semibold text-navy">
                            {initials(emp.name)}
                          </span>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium text-ink group-hover:underline">
                              {emp.name}
                            </p>
                            <p className="truncate text-xs text-muted">
                              {emp.designation ?? '—'}
                            </p>
                            <p className="mt-0.5 truncate text-xs text-muted">
                              {emp.employee_id ?? '—'} · {emp.email}
                            </p>
                          </div>
                        </div>
                        <div className="mt-3 flex items-center justify-between gap-2">
                          <span className="flex items-center gap-1.5">
                            <span
                              className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${LEVEL_BADGE[emp.org_level_code as LevelCode] ?? 'bg-graphite/10 text-muted'}`}
                              title={emp.org_level_name ?? undefined}
                            >
                              {emp.org_level_code ? `${emp.org_level_code} · ${levelLabel(emp.org_level_code)}` : '—'}
                            </span>
                          </span>
                          <span className="flex items-center gap-1.5">
                            <span
                              className={`h-1.5 w-1.5 rounded-full ${emp.is_active ? 'bg-success' : 'bg-muted'}`}
                            />
                            <span className="text-xs text-muted">
                              {emp.is_active ? t('common.active') : t('common.inactive')}
                            </span>
                          </span>
                        </div>
                        {!emp.is_active && isSuperAdmin && (
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              restoreMutation.mutate(emp.id);
                            }}
                            disabled={restoreMutation.isPending}
                            className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-navy underline-offset-2 hover:underline"
                          >
                            <RotateCcw className="h-3 w-3" />
                            Restore
                          </button>
                        )}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {total > 50 && (
        <footer className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
          <span>
            Page {page} of {Math.max(1, Math.ceil(total / 50))}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className={pageBtnClass}
            >
              Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(Math.ceil(total / 50), p + 1))}
              disabled={page >= Math.ceil(total / 50)}
              className={pageBtnClass}
            >
              Next
            </button>
          </div>
        </footer>
      )}

      {showCreate && (
        <Modal onClose={() => setShowCreate(false)} maxWidth="max-w-md">
          <CreateEmployeeModal
            departments={departments.data ?? []}
            orgLevels={orgLevels.data ?? []}
            onClose={() => setShowCreate(false)}
            onSubmit={(payload) => createMutation.mutate(payload)}
            pending={createMutation.isPending}
            error={createMutation.error as { response?: { data?: { detail?: string } } } | null}
          />
        </Modal>
      )}

      {createdCredentials && (
        <CredentialsCard
          credentials={createdCredentials}
          onClose={() => setCreatedCredentials(null)}
        />
      )}
    </div>
  );
}

function CreateEmployeeModal({
  departments,
  orgLevels,
  onClose,
  onSubmit,
  pending,
  error,
}: {
  departments: { id: number; name: string; is_active?: boolean }[];
  orgLevels: OrgLevel[];
  onClose: () => void;
  onSubmit: (payload: {
    name: string;
    contact_email?: string;
    department_id?: number | null;
    org_level_id?: number | null;
    designation?: string;
    phone?: string;
  }) => void;
  pending: boolean;
  error: { response?: { data?: { detail?: string } } } | null;
}) {
  const { t } = useTranslation();
  const currentUser = useAuthStore((s) => s.user);
  const [name, setName] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [designation, setDesignation] = useState('');
  const [departmentId, setDepartmentId] = useState<number | ''>('');
  const [orgLevelId, setOrgLevelId] = useState<number | ''>('');

  const deptDesignations = useQuery({
    queryKey: ['employees', 'department-designations'],
    queryFn: getDepartmentDesignations,
  });

  // Only strictly junior levels are selectable — never the actor's own level
  // or anything above it.
  const actorRank = levelRank(currentUser?.org_level_code);
  const sortedLevels = useMemo(
    () =>
      [...orgLevels]
        .filter((l) => levelRank(l.code) > actorRank)
        .sort(
          (a, b) =>
            LEVEL_ORDER.indexOf(a.code as LevelCode) - LEVEL_ORDER.indexOf(b.code as LevelCode),
        ),
    [orgLevels, actorRank],
  );

  // Default new employees to L5 once the levels are loaded.
  useEffect(() => {
    if (orgLevelId !== '' || sortedLevels.length === 0) return;
    const l5 = sortedLevels.find((l) => l.code === 'L5');
    setOrgLevelId((l5 ?? sortedLevels[sortedLevels.length - 1]).id);
  }, [sortedLevels, orgLevelId]);

  const activeDepartments = useMemo(() => departments.filter((d) => d.is_active !== false), [departments]);

  const selectedDepartment = activeDepartments.find((d) => d.id === departmentId) ?? null;
  const designationOptions =
    (selectedDepartment && deptDesignations.data?.[selectedDepartment.name]) || null;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (orgLevelId === '') return;
    onSubmit({
      name,
      contact_email: contactEmail,
      phone,
      designation: designation || undefined,
      department_id: departmentId === '' ? null : departmentId,
      org_level_id: orgLevelId,
    });
  }

  const fieldClass = `${inputClass} w-full`;
  const labelClass = 'mb-1 block text-xs font-medium text-muted';

  return (
    <div className="w-full max-w-md rounded-lg border border-border bg-surface p-6 shadow-overlay">
      <h2 className="text-lg font-semibold tracking-tight text-ink">{t('employees.addEmployee')}</h2>
      <p className="mt-0.5 text-sm text-muted">{t('employees.loginEmailAutoGenerated')}</p>
      <form onSubmit={submit} className="mt-4 space-y-4">
        <label className="block">
          <span className={labelClass}>{t('employees.fullNameRequired')}</span>
          <input required value={name} onChange={(e) => setName(e.target.value)} placeholder="Full name" className={fieldClass} />
        </label>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="block">
            <span className={labelClass}>{t('employees.emailRequired')}</span>
            <input
              type="email"
              required
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              placeholder="name@email.com"
              className={fieldClass}
            />
          </label>
          <label className="block">
            <span className={labelClass}>{t('employees.phoneRequired')}</span>
            <input
              type="tel"
              required
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+91 98765 43210"
              className={fieldClass}
            />
          </label>
        </div>
        <label className="block">
          <span className={labelClass}>{t('common.role')}</span>
          <select
            required
            value={orgLevelId}
            onChange={(e) => setOrgLevelId(e.target.value === '' ? '' : Number(e.target.value))}
            className={fieldClass}
          >
            {orgLevelId === '' && <option value="">Select level</option>}
            {sortedLevels.map((l) => (
              <option key={l.id} value={l.id}>
                {l.code} — {LEVEL_LABELS[l.code as LevelCode] ?? l.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className={labelClass}>{t('employees.department')}</span>
          <select
            value={departmentId}
            onChange={(e) => {
              setDepartmentId(e.target.value === '' ? '' : Number(e.target.value));
              setDesignation('');
            }}
            className={fieldClass}
          >
            <option value="">{t('employees.noDepartment')}</option>
            {activeDepartments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className={labelClass}>{t('employees.designation')}</span>
          {designationOptions && designationOptions.length > 0 ? (
            <select
              required
              value={designation}
              onChange={(e) => setDesignation(e.target.value)}
              disabled={!selectedDepartment}
              className={fieldClass}
            >
              <option value="" disabled>
                {selectedDepartment ? 'Select designation' : 'Select a department first'}
              </option>
              {designationOptions.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={designation}
              onChange={(e) => setDesignation(e.target.value)}
              placeholder="Designation"
              className={fieldClass}
            />
          )}
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
          <button type="submit" disabled={pending || sortedLevels.length === 0} className={primaryBtnSmallClass}>
            {pending ? 'Creating…' : 'Create Employee'}
          </button>
        </div>
      </form>
    </div>
  );
}


function CredentialsCard({
  credentials,
  onClose,
}: {
  credentials: EmployeeCreateOut;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [showPassword, setShowPassword] = useState(false);
  const [copiedField, setCopiedField] = useState<'id' | 'password' | null>(null);

  function copyToClipboard(text: string, field: 'id' | 'password') {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  }

  return (
    <Modal onClose={onClose} maxWidth="max-w-md">
      <div className="p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10 text-success">
            <Check className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-ink">{t('employees.employeeCreated')}</h2>
            <p className="text-sm text-muted">{t('employees.shareCredentialsWith', { name: credentials.name })}</p>
          </div>
        </div>
        <div className="mt-4 space-y-3 rounded-lg border border-border bg-paper/60 p-4">
          <div>
            <p className="text-xs font-medium text-muted">User ID</p>
            <div className="mt-1 flex items-center gap-2">
              <code className="flex-1 rounded bg-navy/5 px-2 py-1.5 font-mono text-sm font-bold text-ink">{credentials.login_id}</code>
              <button
                onClick={() => copyToClipboard(credentials.login_id ?? '', 'id')}
                className="rounded p-1 text-muted transition hover:bg-surfaceWarm hover:text-ink"
              >
                {copiedField === 'id' ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
              </button>
            </div>
          </div>
          <div>
            <p className="text-xs font-medium text-muted">{t('common.password')}</p>
            <div className="mt-1 flex items-center gap-2">
              <code className="flex-1 rounded bg-navy/5 px-2 py-1.5 text-sm font-medium text-ink">
                {showPassword ? credentials.generated_password : '••••••'}
              </code>
              <button
                onClick={() => setShowPassword((v) => !v)}
                className="rounded p-1 text-muted transition hover:bg-surfaceWarm hover:text-ink"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
              <button
                onClick={() => copyToClipboard(credentials.generated_password, 'password')}
                className="rounded p-1 text-muted transition hover:bg-surfaceWarm hover:text-ink"
              >
                {copiedField === 'password' ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
              </button>
            </div>
          </div>
        </div>
        <div className="mt-5 flex justify-end">
          <button onClick={onClose} className={primaryBtnSmallClass}>
            Done
          </button>
        </div>
      </div>
    </Modal>
  );
}
