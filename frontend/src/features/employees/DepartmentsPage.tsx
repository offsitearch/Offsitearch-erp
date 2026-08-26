import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Building2, Pencil, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useAuthStore } from '../../store/authStore';
import {
  createDepartment,
  deleteDepartment,
  getDepartments,
  getEmployees,
  updateDepartment,
} from '../../api/employees';
import { EmployeeTabs } from './components/EmployeeTabs';
import { canAccess } from '../../lib/constants';
import { EmptyState } from '../../components/ui/EmptyState';
import { LogoLoader } from '../../components/LogoLoader';
import { useTranslation } from 'react-i18next';
import { primaryBtnClass, secondaryBtnClass, dangerBtnClass, modalFieldClass as fieldClass, labelClass } from '../../lib/styles';

export default function DepartmentsPage() {
  const { t } = useTranslation();
  const currentUser = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<{
    id: number;
    name: string;
    head_id: number | null;
    description: string;
    is_active: boolean;
  } | null>(null);
  const [deleting, setDeleting] = useState<{ id: number; name: string; memberCount: number } | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);

  const isSuperAdmin = canAccess(currentUser?.org_level_code, 'L1');

  const departments = useQuery({ queryKey: ['departments'], queryFn: getDepartments });

  const employees = useQuery({
    queryKey: ['employees', 'department-heads'],
    queryFn: () => getEmployees({ active_only: true, page_size: 100 }),
    enabled: isSuperAdmin,
  });

  const createMutation = useMutation({
    mutationFn: () => createDepartment({ name, description: description || undefined }),
    onSuccess: () => {
      setShowCreate(false);
      setName('');
      setDescription('');
      setError(null);
      queryClient.invalidateQueries({ queryKey: ['departments'] });
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail ?? 'Failed to create department. Please try again.');
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: {
      id: number;
      name?: string;
      description?: string;
      head_id?: number | null;
      is_active?: boolean;
    }) => updateDepartment(payload.id, payload),
    onSuccess: () => {
      setEditing(null);
      setError(null);
      queryClient.invalidateQueries({ queryKey: ['departments'] });
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail ?? 'Failed to update department. Please try again.');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteDepartment(id),
    onSuccess: () => {
      setDeleting(null);
      queryClient.invalidateQueries({ queryKey: ['departments'] });
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail ?? 'Failed to delete department.');
      setDeleting(null);
    },
  });

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-ink">{t('employees.title')}</h1>
             <p className="mt-1 text-sm text-muted">{t('employees.deptSubtitle')}</p>
          </div>
          {isSuperAdmin && (
            <button onClick={() => setShowCreate(true)} className={primaryBtnClass}>
              <Plus className="h-4 w-4" />
              New Department
            </button>
          )}
        </div>
        <EmployeeTabs level={currentUser?.org_level_code} />
      </header>

      {error && (
        <div className="rounded-md border border-danger/30 bg-dangerSoft px-3 py-2.5 text-sm text-danger">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline hover:no-underline">
            Dismiss
          </button>
        </div>
      )}

      {departments.isPending ? (
        <LogoLoader />
      ) : departments.isError ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border px-4 py-12 text-center">
          <AlertCircle className="h-6 w-6 text-danger" />
           <p className="text-sm font-medium text-ink">{t('settings.couldntLoadDepartments')}</p>
          <button onClick={() => departments.refetch()} className={secondaryBtnClass}>
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </button>
        </div>
      ) : departments.data?.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="No departments yet."
          text="Create your first department to start organising the studio."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {departments.data?.map((dept) => (
            <div key={dept.id} className="rounded-lg border border-border bg-surface p-5 shadow-card">
              <div className="flex items-start justify-between gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-navy/5 text-navy">
                  <Building2 className="h-5 w-5" />
                </span>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center rounded-full bg-navy/5 px-2.5 py-0.5 text-xs font-medium text-navy">
                    {dept.member_count} {dept.member_count === 1 ? t('employees.member') : t('employees.members')}
                  </span>
                  {isSuperAdmin && (
                    <>
                      <button
                        onClick={() =>
                          setEditing({
                            id: dept.id,
                            name: dept.name,
                            head_id: dept.head_id ?? null,
                            description: dept.description ?? '',
                            is_active: dept.is_active,
                          })
                        }
                        className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border bg-surface text-muted transition hover:bg-surfaceWarm hover:text-ink"
                        aria-label={`Edit ${dept.name}`}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() =>
                          setDeleting({ id: dept.id, name: dept.name, memberCount: dept.member_count })
                        }
                        className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border bg-surface text-muted transition hover:bg-dangerSoft hover:text-danger"
                        aria-label={`Delete ${dept.name}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </>
                  )}
                </div>
              </div>
              <h2 className="mt-3 text-base font-semibold tracking-tight text-ink">{dept.name}</h2>
              {dept.description && <p className="mt-1 text-sm text-muted">{dept.description}</p>}
              {dept.head_name && (
                <p className="mt-3 flex items-center gap-1.5 text-xs font-medium text-navy">
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-orange" />
                  Head: {dept.head_name}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
          <div className="max-h-[90vh] w-full max-w-sm overflow-y-auto rounded-lg border border-border bg-surface p-6 shadow-overlay">
            <h2 className="text-lg font-semibold tracking-tight text-ink">{t('employees.newDepartment')}</h2>
             <p className="mt-0.5 text-sm text-muted">{t('employees.addTeamToStudio')}</p>
            <form
              className="mt-4 space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                setError(null);
                createMutation.mutate();
              }}
            >
              <label className="block">
                <span className={labelClass}>Department name</span>
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={t('settings.departmentName')}
                  className={fieldClass}
                />
              </label>
              <label className="block">
                <span className={labelClass}>Description</span>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  placeholder={t('employees.descriptionOptional')}
                  className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink transition focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30"
                />
              </label>
              {error && (
                <div className="rounded-md border border-danger/30 bg-dangerSoft px-3 py-2.5 text-sm text-danger">
                  {error}
                </div>
              )}
              <div className="flex justify-end gap-2 pt-1">
                <button type="button" onClick={() => { setShowCreate(false); setError(null); }} className={secondaryBtnClass}>
                  Cancel
                </button>
                <button type="submit" disabled={createMutation.isPending} className={primaryBtnClass}>
                  {createMutation.isPending ? t('common.loading') : t('employees.createDepartment')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editing && (
        <EditDepartmentModal
          initial={editing}
          employees={employees.data?.items ?? []}
          error={error}
          pending={updateMutation.isPending}
          onClose={() => {
            setEditing(null);
            setError(null);
          }}
          onSubmit={(payload) => {
            setError(null);
            updateMutation.mutate({ id: editing.id, ...payload });
          }}
        />
      )}

      {deleting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
          <div className="max-h-[90vh] w-full max-w-sm overflow-y-auto rounded-lg border border-border bg-surface p-6 shadow-overlay">
            <h2 className="text-lg font-semibold tracking-tight text-ink">{t('employees.deleteDepartment')}</h2>
            <p className="mt-1 text-sm text-muted">
              {deleting.memberCount > 0 ? (
                <>
                  Cannot delete <strong>{deleting.name}</strong> — {deleting.memberCount} employee
                  {deleting.memberCount !== 1 ? 's are' : ' is'} still assigned. Reassign them first.
                </>
              ) : (
                <>
                  Are you sure you want to delete <strong>{deleting.name}</strong>? This cannot be undone.
                </>
              )}
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => { setDeleting(null); setError(null); }}
                className={secondaryBtnClass}
              >
                {deleting.memberCount > 0 ? t('common.close') : t('common.cancel')}
              </button>
              {deleting.memberCount === 0 && (
                <button
                  onClick={() => deleteMutation.mutate(deleting.id)}
                  disabled={deleteMutation.isPending}
                  className={dangerBtnClass}
                >
                  {deleteMutation.isPending ? t('common.loading') : t('employees.deleteDepartment')}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function EditDepartmentModal({
  initial,
  employees,
  error,
  pending,
  onClose,
  onSubmit,
}: {
  initial: { id: number; name: string; head_id: number | null; description: string; is_active: boolean };
  employees: { id: number; name: string }[];
  error: string | null;
  pending: boolean;
  onClose: () => void;
  onSubmit: (payload: {
    name: string;
    description?: string;
    head_id?: number | null;
    is_active?: boolean;
  }) => void;
}) {
  const [name, setName] = useState(initial.name);
  const [description, setDescription] = useState(initial.description);
  const [headId, setHeadId] = useState<number | ''>(initial.head_id ?? '');
  const [isActive, setIsActive] = useState(initial.is_active);
  const { t } = useTranslation();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
      <div className="max-h-[90vh] w-full max-w-sm overflow-y-auto rounded-lg border border-border bg-surface p-6 shadow-overlay">
        <h2 className="text-lg font-semibold tracking-tight text-ink">{t('employees.editDepartment')}</h2>
        <p className="mt-0.5 text-sm text-muted">{t('employees.updateTeamDetails')}</p>
        <form
          className="mt-4 space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({
              name,
              description: description || undefined,
              head_id: headId === '' ? null : headId,
              is_active: isActive,
            });
          }}
        >
          <label className="block">
            <span className={labelClass}>Department name</span>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('settings.departmentName')}
              className={fieldClass}
            />
          </label>
          <label className="block">
            <span className={labelClass}>Description</span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder={t('employees.descriptionOptional')}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink transition focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30"
            />
          </label>
          <label className="block">
            <span className={labelClass}>Department head</span>
            <select
              value={headId}
              onChange={(e) => setHeadId(e.target.value === '' ? '' : Number(e.target.value))}
              className={fieldClass}
            >
              <option value="">{t('employees.noHead')}</option>
              {employees.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="h-4 w-4 rounded border-border text-orange accent-orange"
            />
            Active department
          </label>
          {error && (
            <div className="rounded-md border border-danger/30 bg-dangerSoft px-3 py-2.5 text-sm text-danger">
              {error}
            </div>
          )}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className={secondaryBtnClass}>
              Cancel
            </button>
            <button type="submit" disabled={pending} className={primaryBtnClass}>
              {pending ? t('common.loading') : t('common.save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
