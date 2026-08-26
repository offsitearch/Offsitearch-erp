import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  Banknote,
  CalendarClock,
  ExternalLink,
  File,
  FileArchive,
  FileImage,
  FileSpreadsheet,
  FileText,
  Pencil,
  Plane,
  RefreshCw,
  RotateCcw,
  Trash2,
  Upload,
  UserRound,
} from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { useDecodedIdRequired as useDecodedId } from '../../lib/useDecodedId';
import Breadcrumbs from '../../components/ui/Breadcrumbs';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { LogoLoader } from '../../components/LogoLoader';
import { Skeleton } from '../../components/ui/Skeleton';
import { useToast } from '../../components/Toast';
import {
  deactivateEmployee,
  deleteEmployeeDocument,
  downloadEmployeeDocument,
  getDepartments,
  getDesignationCatalog,
  getEmployee,
  getEmployeeAttendanceSummary,
  getEmployeeDocuments,
  getEmployeeLeaves,
  getEmployeeSalary,
  getOrgLevels,
  purgeEmployee,
  saveEmployeeSalary,
  updateEmployee,
  uploadEmployeeDocument,
} from '../../api/employees';
import { api } from '../../api/client';
import {
  ATTENDANCE_STATUS_META,
  ATTENDANCE_STATUS_OPTIONS,
  canAccess,
  LEVEL_BADGE,
  employmentTypeLabel,
  leaveStatusMeta,
  leaveTypeLabel,
  levelLabel,
} from '../../lib/constants';
import { formatDate, formatDateRange, formatDayCount, formatDuration } from '../../lib/date';
import { formatIndianCurrencyInput, parseIndianCurrencyInput } from '../../lib/currencyInput';
import CurrencyInput from '../../components/ui/CurrencyInput';
import type { EmployeeProfile, LeaveRecord, OrgLevel } from '../../lib/types';
import { EmployeeTabs } from './components/EmployeeTabs';
import { useTranslation } from 'react-i18next';
import { primaryBtnClass, secondaryBtnClass, dangerBtnClass, smallBtnClass, inputClass, labelClass } from '../../lib/styles';

type Section = 'overview' | 'salary' | 'documents';

const DOC_TYPES = ['offer_letter', 'resume', 'id_proof', 'education', 'appraisal', 'other'];

function initials(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

export default function EmployeeProfilePage() {
  const { t } = useTranslation();
  const userId = useDecodedId();
  const currentUser = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [section, setSection] = useState<Section>('overview');
  const [editing, setEditing] = useState(false);
  const [showPurge, setShowPurge] = useState(false);

  const isAdmin = canAccess(currentUser?.org_level_code, 'L2');
  const isSuperAdmin = canAccess(currentUser?.org_level_code, 'L1');
  // Permanent deletion is reserved for the CEO alone.
  const isCEO = currentUser?.org_level_code === 'L0';
  // Financial data (salary) is L0/L1-only per the financial access policy.
  const canViewSalary = isSuperAdmin;

  const profile = useQuery({
    queryKey: ['employees', userId],
    queryFn: () => getEmployee(userId),
    enabled: Number.isFinite(userId),
  });

  const attendance = useQuery({
    queryKey: ['employees', userId, 'attendance-summary'],
    queryFn: () => getEmployeeAttendanceSummary(userId),
    enabled: Number.isFinite(userId) && isAdmin,
  });

  const salary = useQuery({
    queryKey: ['employees', userId, 'salary'],
    queryFn: () => getEmployeeSalary(userId),
    enabled: Number.isFinite(userId) && canViewSalary,
  });

  const leaves = useQuery({
    queryKey: ['employees', userId, 'leaves'],
    queryFn: () => getEmployeeLeaves(userId),
    enabled: Number.isFinite(userId) && isAdmin,
  });

  const documents = useQuery({
    queryKey: ['employees', userId, 'documents'],
    queryFn: () => getEmployeeDocuments(userId),
    enabled: Number.isFinite(userId),
  });

  const departments = useQuery({ queryKey: ['departments'], queryFn: getDepartments });
  const orgLevels = useQuery({ queryKey: ['org-levels'], queryFn: getOrgLevels });

  const deactivateMutation = useMutation({
    mutationFn: deactivateEmployee,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['employees'] }),
  });

  const purgeMutation = useMutation({
    mutationFn: purgeEmployee,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      toast(`${profile.data?.name ?? 'Employee'} deleted permanently`, 'success');
      setShowPurge(false);
      navigate('/employees');
    },
    onError: () => {
      toast('Failed to delete employee', 'error');
      setShowPurge(false);
    },
  });

  const restoreMutation = useMutation({
    mutationFn: () => updateEmployee(userId, { is_active: true }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['employees'] }),
  });

  const p = profile.data;

  if (profile.isPending) {
    return <LogoLoader />;
  }

  if (!p) {
    return (
      <div className="flex flex-col items-center gap-3 py-20 text-center">
        <AlertCircle className="h-8 w-8 text-danger" />
         <p className="text-sm font-medium text-ink">{t('employees.couldntLoadEmployee')}</p>
        <button onClick={() => profile.refetch()} className={smallBtnClass}>
          <RefreshCw className="h-3.5 w-3.5" />
          Retry
        </button>
      </div>
    );
  }

  const sectionTabs: { key: Section; label: string; icon: typeof FileText }[] = [
    { key: 'overview', label: t('employees.overview'), icon: UserRound },
    { key: 'salary', label: t('employees.salary'), icon: Banknote },
    { key: 'documents', label: t('employees.documents'), icon: FileText },
  ];

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Employees', to: '/employees' }, { label: p.name }]} />
      <header className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex items-center gap-4">
            <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-navy/5 text-lg font-semibold text-navy">
              {initials(p.name)}
            </span>
            <div>
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="text-2xl font-bold tracking-tight text-ink">{p.name}</h1>
                {p.org_level_code && (
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${LEVEL_BADGE[p.org_level_code as keyof typeof LEVEL_BADGE] ?? 'bg-graphite/10 text-graphite'}`}
                    title={p.org_level_name ?? undefined}
                  >
                    {p.org_level_code} · {p.org_level_name ?? levelLabel(p.org_level_code)}
                  </span>
                )}
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    p.is_active ? 'bg-successSoft text-success' : 'bg-surfaceWarm text-muted'
                  }`}
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${p.is_active ? 'bg-success' : 'bg-muted'}`} />
                  {p.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <p className="mt-1 text-sm text-muted">
                {p.employee_id ?? '—'} · {p.designation ?? '—'} ·{' '}
                {`${p.org_level_code ?? ''} ${p.org_level_name ?? ''}`.trim() || '—'}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {isAdmin && (
              <button onClick={() => setEditing(!editing)} className={secondaryBtnClass}>
                <Pencil className="h-4 w-4" />
                {editing ? 'Done' : 'Edit'}
              </button>
            )}
            {isSuperAdmin && (
              <button
                onClick={() => (p.is_active ? deactivateMutation.mutate(p.id) : restoreMutation.mutate())}
                disabled={deactivateMutation.isPending || restoreMutation.isPending}
                className={p.is_active ? dangerBtnClass : secondaryBtnClass}
              >
                {p.is_active ? (
                  <>
                    <Trash2 className="h-4 w-4" />
                    {deactivateMutation.isPending ? 'Deactivating…' : 'Deactivate'}
                  </>
                ) : (
                  <>
                    <RotateCcw className="h-4 w-4" />
                    {restoreMutation.isPending ? 'Restoring…' : 'Restore'}
                  </>
                )}
              </button>
            )}
            {isCEO && p.id !== currentUser?.id && p.org_level_code !== 'L0' && (
              <button onClick={() => setShowPurge(true)} className={dangerBtnClass}>
                <Trash2 className="h-4 w-4" />
                Delete forever
              </button>
            )}
          </div>
        </div>
        <EmployeeTabs level={currentUser?.org_level_code} />
      </header>

      <nav aria-label="Employee details" className="flex flex-wrap items-center gap-1 border-b border-border">
        {sectionTabs
          .filter((tab) => tab.key !== 'salary' || canViewSalary)
          .map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.key}
                onClick={() => setSection(tab.key)}
                className={`inline-flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition ${
                  section === tab.key
                    ? 'border-orange text-ink'
                    : 'border-transparent text-muted hover:border-border hover:text-ink'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
      </nav>

      {section === 'overview' && (
        <Overview
          profile={p}
          editing={editing}
          isAdmin={isAdmin}
          departments={departments.data ?? []}
          orgLevels={orgLevels.data ?? []}
          attendance={attendance.data}
          attendancePending={attendance.isPending}
          leaves={leaves.data ?? []}
          leavesPending={leaves.isPending}
          onSaved={() => {
            setEditing(false);
            queryClient.invalidateQueries({ queryKey: ['employees', userId] });
          }}
        />
      )}
      {section === 'salary' && canViewSalary && <SalarySection userId={userId} salary={salary.data} />}
      {section === 'documents' && (
        <DocumentsSection
          userId={userId}
          documents={documents.data ?? []}
          isAdmin={isAdmin}
          pending={documents.isPending}
          error={documents.isError}
          onRetry={() => documents.refetch()}
        />
      )}

      {showPurge && p && (
        <ConfirmDialog
          title="Delete permanently?"
          message={`${p.name}'s account, timesheets, attendance links, leaves, payroll entries, salary, documents and notifications will be erased for good. Records that only reference them are kept but detached. Their email becomes reusable. This cannot be undone.`}
          confirmLabel={purgeMutation.isPending ? 'Deleting…' : 'Delete forever'}
          tone="danger"
          pending={purgeMutation.isPending}
          onConfirm={() => purgeMutation.mutate(p.id)}
          onClose={() => setShowPurge(false)}
        />
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="rounded-md bg-surfaceWarm px-4 py-3">
      <dt className="text-[11px] font-semibold uppercase tracking-wider text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium text-ink">{value || '—'}</dd>
    </div>
  );
}

function Overview({
  profile,
  editing,
  isAdmin,
  departments,
  orgLevels,
  attendance,
  attendancePending,
  leaves,
  leavesPending,
  onSaved,
}: {
  profile: EmployeeProfile;
  editing: boolean;
  isAdmin: boolean;
  departments: { id: number; name: string }[];
  orgLevels: OrgLevel[];
  attendance: { totals: Record<string, number>; total_hours: string; days_worked: number } | undefined;
  attendancePending: boolean;
  leaves: LeaveRecord[];
  leavesPending: boolean;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    phone: profile.phone ?? '',
    emergency_contact_name: profile.emergency_contact_name ?? '',
    emergency_contact_phone: profile.emergency_contact_phone ?? '',
    address: profile.address ?? '',
    skills: (profile.skills ?? []).join(', '),
    department_id: profile.department_id ?? '' as number | '',
    org_level_id: profile.org_level_id ?? '' as number | '',
    designation: profile.designation ?? '',
  });
  const [error, setError] = useState<string | null>(null);

  const designations = useQuery({
    queryKey: ['employees', 'designation-catalog'],
    queryFn: getDesignationCatalog,
    enabled: editing && isAdmin,
  });

  const effectiveLevelId = form.org_level_id !== '' ? form.org_level_id : profile.org_level_id;
  const effectiveLevelCode =
    orgLevels.find((l) => l.id === effectiveLevelId)?.code ?? null;
  const levelDesignations =
    (effectiveLevelCode && designations.data?.[effectiveLevelCode]) || [];
  // Keep the current value selectable even when it is not part of the
  // level's catalog (e.g. legacy free-text data).
  const designationOptions =
    form.designation && !levelDesignations.includes(form.designation)
      ? [form.designation, ...levelDesignations]
      : levelDesignations;

  const handleOrgLevelChange = (value: string) => {
    const nextId: number | '' = value === '' ? '' : Number(value);
    const nextCode =
      nextId === ''
        ? profile.org_level_code
        : orgLevels.find((l) => l.id === nextId)?.code ?? null;
    const allowed = (nextCode && designations.data?.[nextCode]) || [];
    setForm((f) => ({
      ...f,
      org_level_id: nextId,
      designation: allowed.includes(f.designation) ? f.designation : '',
    }));
  };

  const mutation = useMutation({
    mutationFn: (payload: typeof form) =>
      updateEmployee(profile.id, {
        phone: payload.phone || undefined,
        emergency_contact_name: payload.emergency_contact_name || undefined,
        emergency_contact_phone: payload.emergency_contact_phone || undefined,
        address: payload.address || undefined,
        skills: payload.skills
          ? payload.skills.split(',').map((s) => s.trim()).filter(Boolean)
          : undefined,
        department_id: isAdmin ? (payload.department_id === '' ? null : payload.department_id) : undefined,
        org_level_id: isAdmin ? (payload.org_level_id === '' ? null : payload.org_level_id) : undefined,
        designation: isAdmin ? (payload.designation || undefined) : undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees', profile.id] });
      onSaved();
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail ?? 'Failed to save changes. Please try again.');
    },
  });

  const summaryOrder = ATTENDANCE_STATUS_OPTIONS;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <section className="rounded-lg border border-border bg-surface shadow-card">
          <div className="border-b border-border px-5 py-4">
            <h2 className="text-sm font-semibold text-ink">{t('employees.professional')}</h2>
             <p className="mt-0.5 text-xs text-muted">{t('employees.roleAndPosition')}</p>
          </div>
          {editing && isAdmin ? (
            <div className="grid grid-cols-1 gap-4 p-5 sm:grid-cols-2">
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-muted">Department</span>
                <select
                  value={form.department_id}
                  onChange={(e) => setForm({ ...form, department_id: e.target.value === '' ? '' : Number(e.target.value) })}
                  className="h-10 w-full rounded-md border border-border bg-surface px-3 text-sm text-ink transition focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30"
                >
                  <option value="">No department</option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-muted">Designation</span>
                <select
                  value={form.designation}
                  onChange={(e) => setForm({ ...form, designation: e.target.value })}
                  disabled={designationOptions.length === 0}
                  className="h-10 w-full rounded-md border border-border bg-surface px-3 text-sm text-ink transition focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30"
                >
                  <option value="">
                    {designationOptions.length === 0
                      ? effectiveLevelCode
                        ? `No designations defined for ${effectiveLevelCode}`
                        : 'Select an org level first'
                      : 'No designation'}
                  </option>
                  {designationOptions.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-muted">Org level</span>
                <select
                  value={form.org_level_id}
                  onChange={(e) => handleOrgLevelChange(e.target.value)}
                  className="h-10 w-full rounded-md border border-border bg-surface px-3 text-sm text-ink transition focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30"
                >
                  <option value="">No change</option>
                  {orgLevels.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.code} · {l.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          ) : (
            <dl className="grid grid-cols-1 gap-3 p-5 sm:grid-cols-2">
              <Row label="Department" value={profile.department} />
              <Row label="Designation" value={profile.designation} />
              <Row
                label="Org level"
                value={
                  profile.org_level_code
                    ? `${profile.org_level_code} · ${profile.org_level_name ?? levelLabel(profile.org_level_code)}`
                    : null
                }
              />
              <Row label="Employment type" value={employmentTypeLabel(profile.employment_type)} />
              <Row label="Date of joining" value={profile.date_of_joining ? formatDate(profile.date_of_joining) : null} />
              <Row label="Reports to" value={profile.reports_to_name} />
              <Row label="Email" value={profile.email} />
            </dl>
          )}
        </section>

        <section className="rounded-lg border border-border bg-surface shadow-card">
          <div className="border-b border-border px-5 py-4">
            <h2 className="text-sm font-semibold text-ink">{t('employees.personalAndContact')}</h2>
            <p className="mt-0.5 text-xs text-muted">Contact details and emergency information.</p>
          </div>
          {editing ? (
            <form
              className="space-y-4 p-5"
              onSubmit={(e) => {
                e.preventDefault();
                setError(null);
                mutation.mutate(form);
              }}
            >
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <label className="block">
                  <span className={labelClass}>Phone</span>
                  <input
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    placeholder="Phone"
                    className={inputClass}
                  />
                </label>
                <label className="block">
                  <span className={labelClass}>Emergency contact</span>
                  <input
                    value={form.emergency_contact_name}
                    onChange={(e) => setForm({ ...form, emergency_contact_name: e.target.value })}
                    placeholder="Emergency contact name"
                    className={inputClass}
                  />
                </label>
                <label className="block">
                  <span className={labelClass}>Emergency phone</span>
                  <input
                    value={form.emergency_contact_phone}
                    onChange={(e) => setForm({ ...form, emergency_contact_phone: e.target.value })}
                    placeholder="Emergency contact phone"
                    className={inputClass}
                  />
                </label>
                <label className="block">
                  <span className={labelClass}>Skills</span>
                  <input
                    value={form.skills}
                    onChange={(e) => setForm({ ...form, skills: e.target.value })}
                    placeholder="Skills (comma separated)"
                    className={inputClass}
                  />
                </label>
              </div>
              <label className="block">
                <span className={labelClass}>Address</span>
                <textarea
                  value={form.address}
                  onChange={(e) => setForm({ ...form, address: e.target.value })}
                  rows={2}
                  placeholder="Address"
                  className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink transition focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30"
                />
              </label>
              {error && (
                <div className="rounded-md border border-danger/30 bg-dangerSoft px-3 py-2.5 text-sm text-danger">
                  {error}
                </div>
              )}
              <button type="submit" disabled={mutation.isPending} className={primaryBtnClass}>
                {mutation.isPending ? 'Saving…' : 'Save changes'}
              </button>
            </form>
          ) : (
            <dl className="grid grid-cols-1 gap-3 p-5 sm:grid-cols-2">
              <Row label="Phone" value={profile.phone} />
              <Row label="Date of birth" value={profile.date_of_birth ? formatDate(profile.date_of_birth) : null} />
              <Row label="Gender" value={profile.gender} />
              <Row label="Blood group" value={profile.blood_group} />
              <Row label="Emergency contact" value={profile.emergency_contact_name} />
              <Row label="Emergency phone" value={profile.emergency_contact_phone} />
              <Row label="Skills" value={(profile.skills ?? []).join(', ') || null} />
              <div className="sm:col-span-2">
                <Row label="Address" value={profile.address} />
              </div>
            </dl>
          )}
        </section>
      </div>

      <div className="space-y-6">
        <section className="rounded-lg border border-border bg-surface shadow-card">
          <div className="flex items-center gap-2 border-b border-border px-5 py-4">
            <CalendarClock className="h-4 w-4 text-orange" />
            <h2 className="text-sm font-semibold text-ink">{t('employees.thisMonth')}</h2>
          </div>
          {attendancePending ? (
            <div className="space-y-3 p-5">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          ) : !attendance ? (
            <p className="p-5 text-sm text-muted">No attendance data yet.</p>
          ) : (
            <div className="p-5">
              <dl className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <dt className="text-muted">Days worked</dt>
                  <dd className="font-semibold tabular-nums text-ink">{attendance.days_worked ?? 0}</dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-muted">Total hours</dt>
                  <dd className="font-semibold tabular-nums text-ink">
                    {formatDuration(attendance.total_hours) || '0h'}
                  </dd>
                </div>
              </dl>
              <div className="my-3 border-t border-border" />
              <div className="space-y-1">
                {summaryOrder.map((status) => {
                  const meta = ATTENDANCE_STATUS_META[status];
                  const count = attendance.totals?.[status] ?? 0;
                  const Icon = meta.icon;
                  return (
                    <div
                      key={status}
                      className="flex items-center gap-3 rounded-md px-3 py-2 transition hover:bg-surfaceWarm"
                    >
                      <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${meta.cell}`}>
                        <Icon className={`h-4 w-4 ${meta.iconColor}`} />
                      </span>
                      <span className="flex-1 text-sm text-ink">{meta.label}</span>
                      <span className="text-lg font-semibold tabular-nums text-ink">{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </section>

        <section className="rounded-lg border border-border bg-surface shadow-card">
          <div className="flex items-center gap-2 border-b border-border px-5 py-4">
            <Plane className="h-4 w-4 text-orange" />
            <h2 className="text-sm font-semibold text-ink">{t('leaves.leaveHistory')}</h2>
          </div>
          {leavesPending ? (
            <div className="space-y-3 p-5">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          ) : leaves.length === 0 ? (
            <p className="p-5 text-sm text-muted">No leave records yet.</p>
          ) : (
            <div className="p-3">
              {[...leaves]
                .sort((a, b) => b.created_at.localeCompare(a.created_at))
                .slice(0, 6)
                .map((leave) => {
                  const meta = leaveStatusMeta(leave.status);
                  return (
                    <div
                      key={leave.id}
                      className="flex items-center gap-3 rounded-md px-2 py-2 transition hover:bg-surfaceWarm"
                    >
                      <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${meta.cell}`}>
                        <Plane className={`h-4 w-4 ${meta.dot.replace('bg-', 'text-')}`} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-ink">
                          {leaveTypeLabel(leave.leave_type)}
                        </span>
                        <span className="block text-xs text-muted">
                          {formatDateRange(leave.from_date, leave.to_date)}
                        </span>
                      </span>
                      <span className="text-xs font-medium tabular-nums text-muted">
                        {formatDayCount(leave.total_days)}
                      </span>
                    </div>
                  );
                })}
            </div>
          )}
        </section>

        <section className="rounded-lg border border-border bg-surface p-5 shadow-card">
          <h2 className="text-sm font-semibold text-ink">{t('employees.status')}</h2>
          <p className="mt-3">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                profile.is_active ? 'bg-successSoft text-success' : 'bg-surfaceWarm text-muted'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${profile.is_active ? 'bg-success' : 'bg-muted'}`}
              />
              {profile.is_active ? 'Active' : 'Inactive'}
            </span>
          </p>
          {profile.date_of_joining && (
            <p className="mt-3 text-xs text-muted">Joined {formatDate(profile.date_of_joining)}</p>
          )}
        </section>
      </div>
    </div>
  );
}

function SalarySection({
  userId,
  salary,
}: {
  userId: number;
  salary: { ctc_annual: string; basic: string; hra: string; special_allowance: string; pf_deduction: string; bank_name: string | null; account_number: string | null; ifsc_code: string | null } | undefined;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    ctc_annual: salary?.ctc_annual ? formatIndianCurrencyInput(salary.ctc_annual) : '',
    basic: salary?.basic ? formatIndianCurrencyInput(salary.basic) : '',
    hra: salary?.hra ? formatIndianCurrencyInput(salary.hra) : '',
    special_allowance: salary?.special_allowance ? formatIndianCurrencyInput(salary.special_allowance) : '',
    pf_deduction: salary?.pf_deduction ? formatIndianCurrencyInput(salary.pf_deduction) : '',
    bank_name: salary?.bank_name ?? '',
    account_number: salary?.account_number ?? '',
    ifsc_code: salary?.ifsc_code ?? '',
  });
  const [error, setError] = useState<string | null>(null);

  const money = (value: string) => {
    const num = parseIndianCurrencyInput(value);
    return num == null ? undefined : String(num);
  };

  const mutation = useMutation({
    mutationFn: (payload: typeof form) =>
      saveEmployeeSalary(userId, {
        ctc_annual: money(payload.ctc_annual),
        basic: money(payload.basic),
        hra: money(payload.hra),
        special_allowance: money(payload.special_allowance),
        pf_deduction: money(payload.pf_deduction),
        bank_name: payload.bank_name || undefined,
        account_number: payload.account_number || undefined,
        ifsc_code: payload.ifsc_code || undefined,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['employees', userId, 'salary'] }),
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail ?? 'Failed to save salary. Please try again.');
    },
  });

  const fmt = (value: string) => {
    const num = Number(value);
    return Number.isFinite(num) ? num.toLocaleString('en-IN') : value;
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <section className="rounded-lg border border-border bg-surface shadow-card lg:col-span-2">
        <div className="flex items-center gap-2 border-b border-border px-5 py-4">
          <Banknote className="h-4 w-4 text-orange" />
          <h2 className="text-sm font-semibold text-ink">{t('employees.salaryComponents')}</h2>
        </div>
        <form
          className="grid grid-cols-1 gap-4 p-5 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            mutation.mutate(form);
          }}
        >
          <label className="block">
            <span className={labelClass}>Annual CTC</span>
            <CurrencyInput
              value={form.ctc_annual}
              onChange={(ctc_annual) => setForm({ ...form, ctc_annual })}
              placeholder="Annual CTC"
            />
          </label>
          <label className="block">
            <span className={labelClass}>Basic / month</span>
            <CurrencyInput value={form.basic} onChange={(basic) => setForm({ ...form, basic })} placeholder="Basic / month" />
          </label>
          <label className="block">
            <span className={labelClass}>HRA / month</span>
            <CurrencyInput value={form.hra} onChange={(hra) => setForm({ ...form, hra })} placeholder="HRA / month" />
          </label>
          <label className="block">
            <span className={labelClass}>Special allowance</span>
            <CurrencyInput
              value={form.special_allowance}
              onChange={(special_allowance) => setForm({ ...form, special_allowance })}
              placeholder="Special allowance"
            />
          </label>
          <label className="block">
            <span className={labelClass}>PF deduction</span>
            <CurrencyInput
              value={form.pf_deduction}
              onChange={(pf_deduction) => setForm({ ...form, pf_deduction })}
              placeholder="PF deduction"
            />
          </label>
          <label className="block">
            <span className={labelClass}>Bank name</span>
            <input
              value={form.bank_name}
              onChange={(e) => setForm({ ...form, bank_name: e.target.value })}
              placeholder="Bank name"
              className={inputClass}
            />
          </label>
          <label className="block">
            <span className={labelClass}>Account number</span>
            <input
              value={form.account_number}
              onChange={(e) => setForm({ ...form, account_number: e.target.value })}
              placeholder="Account number"
              className={inputClass}
            />
          </label>
          <label className="block">
            <span className={labelClass}>IFSC code</span>
            <input
              value={form.ifsc_code}
              onChange={(e) => setForm({ ...form, ifsc_code: e.target.value })}
              placeholder="IFSC code"
              className={inputClass}
            />
          </label>
          {error && (
            <div className="rounded-md border border-danger/30 bg-dangerSoft px-3 py-2.5 text-sm text-danger sm:col-span-2">
              {error}
            </div>
          )}
          <div className="sm:col-span-2">
            <button type="submit" disabled={mutation.isPending} className={primaryBtnClass}>
              {mutation.isPending ? 'Saving…' : 'Save salary'}
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-lg border border-border bg-surface p-5 shadow-card">
        <h2 className="text-sm font-semibold text-ink">{t('employees.currentPackage')}</h2>
        <p className="mt-3 text-3xl font-semibold tracking-tight text-ink">
          {salary ? fmt(salary.ctc_annual) : '—'}
        </p>
        <p className="text-sm text-muted">INR / annum</p>
        <dl className="mt-6 space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <dt className="text-muted">Basic</dt>
            <dd className="font-medium tabular-nums text-ink">{salary ? fmt(salary.basic) : '—'}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-muted">HRA</dt>
            <dd className="font-medium tabular-nums text-ink">{salary ? fmt(salary.hra) : '—'}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-muted">Special</dt>
            <dd className="font-medium tabular-nums text-ink">
              {salary ? fmt(salary.special_allowance) : '—'}
            </dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-muted">PF deduction</dt>
            <dd className="font-medium tabular-nums text-ink">{salary ? fmt(salary.pf_deduction) : '—'}</dd>
          </div>
        </dl>
      </section>
    </div>
  );
}

function getDocIcon(fileName: string) {
  const ext = fileName.split('.').pop()?.toLowerCase();
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext || '')) return FileImage;
  if (['xls', 'xlsx', 'csv'].includes(ext || '')) return FileSpreadsheet;
  if (['zip', 'rar', '7z'].includes(ext || '')) return FileArchive;
  if (['pdf'].includes(ext || '')) return FileText;
  return File;
}

function DocumentsSection({
  userId,
  documents,
  isAdmin,
  pending,
  error,
  onRetry,
}: {
  userId: number;
  documents: { id: number; doc_type: string; file_name: string; uploaded_at: string }[];
  isAdmin: boolean;
  pending: boolean;
  error: boolean;
  onRetry: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [docType, setDocType] = useState(DOC_TYPES[0]);
  const [file, setFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const upload = useMutation({
    mutationFn: () => uploadEmployeeDocument(userId, file as File, docType),
    onSuccess: () => {
      setFile(null);
      setUploadError(null);
      queryClient.invalidateQueries({ queryKey: ['employees', userId, 'documents'] });
    },
    onError: () => setUploadError("Couldn't upload the document. Please try again."),
  });

  const deleteMut = useMutation({
    mutationFn: (docId: number) => deleteEmployeeDocument(userId, docId),
    onSuccess: () => {
      setDeletingId(null);
      queryClient.invalidateQueries({ queryKey: ['employees', userId, 'documents'] });
      toast('Document deleted', 'success');
    },
    onError: () => {
      setDeletingId(null);
      toast('Failed to delete document', 'error');
    },
  });

  return (
    <div className="space-y-6">
      {isAdmin && (
        <section className="rounded-lg border border-border bg-surface p-5 shadow-card">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-ink">
            <Upload className="h-4 w-4 text-orange" />
            Upload document
          </h2>
          <div className="mt-4 flex flex-wrap items-end gap-3">
            <label className="block">
              <span className={labelClass}>Type</span>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className={inputClass}
              >
                {DOC_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className={labelClass}>File</span>
              <input
                type="file"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="h-10 text-sm text-muted file:mr-3 file:h-10 file:rounded-md file:border-0 file:bg-navy file:px-3 file:text-xs file:font-semibold file:text-white"
              />
            </label>
            <button
              onClick={() => file && upload.mutate()}
              disabled={!file || upload.isPending}
              className={primaryBtnClass}
            >
              {upload.isPending ? 'Uploading…' : 'Upload'}
            </button>
          </div>
          {uploadError && (
            <div className="mt-3 rounded-md border border-danger/30 bg-dangerSoft px-3 py-2.5 text-sm text-danger">
              {uploadError}
            </div>
          )}
        </section>
      )}

      <section className="overflow-hidden rounded-lg border border-border bg-surface shadow-card">
        <div className="border-b border-border px-5 py-4">
          <h2 className="text-sm font-semibold text-ink">{t('employees.documents')}</h2>
          <p className="mt-0.5 text-xs text-muted">{t('employees.employmentAndPersonalRecords')}</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-left text-sm">
            <thead className="border-b border-border bg-paper/60 text-[11px] font-semibold uppercase tracking-wider text-muted">
              <tr>
                <th className="px-4 py-3">Document</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Uploaded</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {pending ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8">
                    <div className="space-y-3">
                      {Array.from({ length: 3 }).map((_, i) => (
                        <Skeleton key={i} className="h-5 w-full" />
                      ))}
                    </div>
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={4} className="px-4 py-12">
                    <div className="flex flex-col items-center gap-3 text-center">
                      <AlertCircle className="h-6 w-6 text-danger" />
                      <p className="text-sm font-medium text-ink">Couldn't load documents.</p>
                      <button onClick={onRetry} className={smallBtnClass}>
                        <RefreshCw className="h-3.5 w-3.5" />
                        Retry
                      </button>
                    </div>
                  </td>
                </tr>
              ) : documents.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-12 text-center">
                    <FileText className="mx-auto h-8 w-8 text-border" />
                    <p className="mt-2 text-sm font-medium text-ink">No documents uploaded yet.</p>
                    <p className="mt-0.5 text-xs text-muted">Uploaded documents will appear here.</p>
                  </td>
                </tr>
              ) : (
                documents.map((doc) => {
                  const DocIcon = getDocIcon(doc.file_name);
                  return (
                    <tr key={doc.id} className="transition hover:bg-surfaceWarm">
                      <td className="px-4 py-3">
                        <span className="flex items-center gap-2 font-medium text-ink">
                          <DocIcon className="h-4 w-4 shrink-0 text-muted" />
                          <span className="truncate">{doc.file_name}</span>
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center rounded-full bg-navy/5 px-2.5 py-0.5 text-xs font-medium text-navy">
                          {doc.doc_type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-muted">{formatDate(doc.uploaded_at)}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <a
                            href={`${api.defaults.baseURL}/employees/${userId}/documents/${doc.id}/download`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-navy transition hover:bg-navy/5 hover:text-navyDark"
                            title="Preview"
                          >
                            <ExternalLink className="h-4 w-4" />
                          </a>
                          <button
                            onClick={() => downloadEmployeeDocument(userId, doc.id)}
                            className="text-sm font-medium text-navy underline-offset-2 hover:underline"
                          >
                            Download
                          </button>
                          {isAdmin && (
                            <button
                              onClick={() => setDeletingId(doc.id)}
                              className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted transition hover:bg-dangerSoft hover:text-danger"
                              title="Delete"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      {deletingId !== null && (
        <ConfirmDialog
          title="Delete document"
          message="Are you sure you want to delete this document? This action cannot be undone."
          confirmLabel="Delete"
          tone="danger"
          pending={deleteMut.isPending}
          onConfirm={() => deleteMut.mutate(deletingId)}
          onClose={() => setDeletingId(null)}
        />
      )}
    </div>
  );
}
