import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Copy, Eye, EyeOff, KeyRound, Loader2, Pencil, Plus, Search, UserRound, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getDepartments, getOrgLevels } from '../../api/employees';
import { createUser, getUsers, regeneratePassword, updateUser } from '../../api/settings';
import { EmptyState } from '../../components/ui/EmptyState';
import { LogoLoader } from '../../components/LogoLoader';
import { useToast } from '../../components/Toast';
import {
  LEVEL_BADGE,
  LEVEL_DESCRIPTIONS,
  canAccess,
  levelLabel,
  levelRank,
  type LevelCode,
} from '../../lib/constants';
import type {
  Department,
  OrgLevel,
  RegeneratedCredentials,
  UserAdminCreateOut,
  UserBrief,
  UserCreateInput,
  UserUpdateInput,
} from '../../lib/types';
import { useAuthStore } from '../../store/authStore';
import { inputClass, selectClass, primaryBtnClass, secondaryBtnClass, modalLabelClass } from '../../lib/styles';

export function UsersTab() {
  const me = useAuthStore((s) => s.user);
  const isExecutive = canAccess(me?.org_level_code, 'L1');
  const myRank = levelRank(me?.org_level_code);
  const canManage = canAccess(me?.org_level_code, 'L2');
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState<{ editing?: UserBrief } | null>(null);
  const [createdCredentials, setCreatedCredentials] = useState<UserAdminCreateOut | null>(null);
  const [regenerated, setRegenerated] = useState<RegeneratedCredentials | null>(null);

  const users = useQuery({ queryKey: ['admin-users'], queryFn: () => getUsers({ active_only: false }) });

  const filtered = (users.data ?? []).filter(
    (u) =>
      !search ||
      u.name.toLowerCase().includes(search.toLowerCase()) ||
      u.login_id.includes(search) ||
      u.email.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search users…"
            className={`${inputClass} w-64 pl-9`}
          />
        </div>
        {isExecutive && (
          <button onClick={() => setModal({})} className={primaryBtnClass}>
            <Plus className="h-4 w-4" /> Add User
          </button>
        )}
      </div>

      {!isExecutive && (
        <p className="rounded-lg bg-warningSoft px-4 py-2 text-sm text-warning">
          Only executives (L0/L1) can create or modify user accounts.
        </p>
      )}

      {users.isPending ? (
        <LogoLoader />
      ) : filtered.length === 0 ? (
        <EmptyState icon={UserRound} title="No users found" text="Try a different search." />
      ) : (
        <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border bg-surfaceWarm text-xs uppercase tracking-wide text-muted">
                  <th className="px-4 py-3 font-semibold">Employee</th>
                  <th className="px-4 py-3 font-semibold">Level</th>
                  <th className="px-4 py-3 font-semibold">Designation</th>
                  <th className="px-4 py-3 font-semibold">Department</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  {canManage && <th className="px-4 py-3 text-right font-semibold">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {filtered.map((u) => (
                  <tr key={u.id} className="border-b border-border last:border-0 hover:bg-surfaceWarm">
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-orange text-xs font-bold text-white">
                          {initials(u.name)}
                        </div>
                        <div>
                          <p className="font-medium text-ink">{u.name}</p>
                          <p className="text-xs text-muted">
                            <span className="font-mono font-semibold text-graphite">{u.login_id}</span>
                            {' · '}
                            {u.email}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-2.5">
                      {u.org_level_code ? (
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-semibold ${LEVEL_BADGE[u.org_level_code as LevelCode] ?? 'bg-graphite/10 text-graphite'}`}
                          title={u.org_level_name ?? undefined}
                        >
                          {u.org_level_code} · {levelLabel(u.org_level_code)}
                        </span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-ink">{u.designation ?? '—'}</td>
                    <td className="px-4 py-2.5 text-ink">{u.department ?? '—'}</td>
                    <td className="px-4 py-2.5">
                      {u.is_active ? (
                        <span className="rounded-full bg-successSoft px-2 py-0.5 text-xs font-medium text-success">
                          Active
                        </span>
                      ) : (
                        <span className="rounded-full bg-dangerSoft px-2 py-0.5 text-xs font-medium text-danger">
                          Inactive
                        </span>
                      )}
                    </td>
                    {canManage && (
                      <td className="px-4 py-2.5">
                        <div className="flex justify-end gap-1">
                          {isExecutive && levelRank(u.org_level_code) > myRank && (
                            <button
                              onClick={() =>
                                regeneratePassword(u.id)
                                  .then(setRegenerated)
                                  .catch(() => {})
                              }
                              className="rounded-lg p-1.5 text-muted transition hover:bg-surfaceWarm hover:text-ink"
                              title="Reset password (generates a new one-time password)"
                            >
                              <KeyRound className="h-4 w-4" />
                            </button>
                          )}
                          <button
                            onClick={() => setModal({ editing: u })}
                            className="rounded-lg p-1.5 text-muted transition hover:bg-surfaceWarm hover:text-ink"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {modal && (
        <UserFormModal
          editing={modal.editing}
          onClose={() => setModal(null)}
          onCreated={(data) => {
            setModal(null);
            setCreatedCredentials(data);
          }}
        />
      )}

      {createdCredentials && (
        <OneTimeCredentialsCard
          title="User Created"
          subtitle={`Share these credentials with ${createdCredentials.name}`}
          loginId={createdCredentials.login_id}
          password={createdCredentials.generated_password}
          onClose={() => setCreatedCredentials(null)}
        />
      )}

      {regenerated && (
        <OneTimeCredentialsCard
          title="Password Reset"
          subtitle={`Share a new temporary password with ${regenerated.name}`}
          loginId={regenerated.login_id}
          password={regenerated.generated_password}
          onClose={() => setRegenerated(null)}
        />
      )}
    </div>
  );
}

function initials(name: string): string {
  return name
    .split(' ')
    .map((p) => p[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

interface UserFormValues {
  name: string;
  contact_email: string;
  password: string;
  designation: string;
  department_id: string;
  org_level_id: number | null;
  employee_id: string;
  phone: string;
  is_active: boolean;
}

function UserFormModal({ editing, onClose, onCreated }: { editing?: UserBrief; onClose: () => void; onCreated?: (data: UserAdminCreateOut) => void }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const me = useAuthStore((s) => s.user);
  const departments = useQuery({ queryKey: ['departments'], queryFn: getDepartments });
  const orgLevels = useQuery({ queryKey: ['org-levels'], queryFn: getOrgLevels });

  const [form, setForm] = useState<UserFormValues>({
    name: editing?.name ?? '',
    contact_email: editing?.contact_email ?? '',
    password: '',
    designation: editing?.designation ?? '',
    department_id: editing?.department_id ? String(editing.department_id) : '',
    org_level_id: editing?.org_level_id ?? null,
    employee_id: editing?.employee_id ?? '',
    phone: '',
    is_active: editing?.is_active ?? true,
  });

  useEffect(() => {
    if (!editing && form.org_level_id === null && orgLevels.data) {
      const defaultLevel = orgLevels.data.find((l) => l.code === 'L5');
      if (defaultLevel) set('org_level_id', defaultLevel.id);
    }
  }, [editing, orgLevels.data]);

  const save = useMutation({
    mutationFn: async () => {
      if (editing) {
        const payload: UserUpdateInput = {
          name: form.name,
          contact_email: form.contact_email || null,
          designation: form.designation,
          department_id: form.department_id === '' ? null : Number(form.department_id),
          org_level_id: form.org_level_id,
          employee_id: form.employee_id,
          is_active: form.is_active,
        };
        if (form.password) payload.password = form.password;
        return await updateUser(editing.id, payload);
      } else {
        const payload: UserCreateInput = {
          name: form.name,
          contact_email: form.contact_email || undefined,
          password: form.password || undefined,
          designation: form.designation,
          department_id: form.department_id === '' ? null : Number(form.department_id),
          org_level_id: form.org_level_id,
          employee_id: form.employee_id,
          phone: form.phone,
        };
        return await createUser(payload);
      }
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      if (!editing && data && 'generated_password' in data) {
        onCreated?.(data as UserAdminCreateOut);
      } else {
        toast(editing ? 'User updated' : 'User created', 'success');
        onClose();
      }
    },
    onError: (err) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast(detail ?? 'Failed to save user', 'error');
    },
  });

  function set<K extends keyof UserFormValues>(key: K, value: UserFormValues[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    save.mutate();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-surface p-6 shadow-overlay">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy/10 text-navy">
              <UserRound className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-bold text-ink">{editing ? 'Edit user' : 'Add user'}</h2>
          </div>
          <button onClick={onClose} aria-label="Close" className="rounded-lg p-1 text-muted hover:bg-surfaceWarm">
            <X className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={submit} className="mt-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <label className={modalLabelClass}>
              Full name *
              <input required value={form.name} onChange={(e) => set('name', e.target.value)} className={`${inputClass} mt-1`} />
            </label>
            <label className={modalLabelClass}>
              Contact email (optional)
              <input
                type="email"
                value={form.contact_email}
                onChange={(e) => set('contact_email', e.target.value)}
                placeholder="personal@email.com"
                className={`${inputClass} mt-1`}
              />
            </label>
            <label className={modalLabelClass}>
              Employee ID
              <input
                value={form.employee_id}
                onChange={(e) => set('employee_id', e.target.value)}
                className={`${inputClass} mt-1`}
              />
            </label>
            <label className={modalLabelClass}>
              Designation
              <input
                value={form.designation}
                onChange={(e) => set('designation', e.target.value)}
                className={`${inputClass} mt-1`}
              />
            </label>
            <label className={modalLabelClass}>
              Department
              <select
                value={form.department_id}
                onChange={(e) => set('department_id', e.target.value)}
                className={`${selectClass} mt-1`}
              >
                <option value="">None</option>
                {(departments.data ?? []).map((d: Department) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </label>
            <label className={modalLabelClass}>
              Level
              <select
                value={form.org_level_id ?? ''}
                onChange={(e) => set('org_level_id', e.target.value === '' ? null : Number(e.target.value))}
                className={`${selectClass} mt-1`}
              >
                <option value="">None</option>
                {[...(orgLevels.data ?? [])]
                  .sort((a: OrgLevel, b: OrgLevel) => levelRank(a.code) - levelRank(b.code))
                  .map((l: OrgLevel) => (
                    <option
                      key={l.id}
                      value={l.id}
                      disabled={
                        (l.code === 'L0' && !canAccess(me?.org_level_code, 'L0')) ||
                        (l.code === 'L1' && !canAccess(me?.org_level_code, 'L1'))
                      }
                    >
                      {l.code} — {levelLabel(l.code)}
                    </option>
                  ))}
              </select>
              {(() => {
                const lvl = (orgLevels.data ?? []).find((l) => l.id === form.org_level_id);
                return lvl ? (
                  <span className="mt-1 block text-xs text-muted">
                    {LEVEL_DESCRIPTIONS[lvl.code as LevelCode] ?? lvl.description}
                  </span>
                ) : null;
              })()}
            </label>
            {!editing && (
              <label className={modalLabelClass}>
                Phone
                <input value={form.phone} onChange={(e) => set('phone', e.target.value)} className={`${inputClass} mt-1`} />
              </label>
            )}
            <label className={modalLabelClass}>
              {editing ? 'New password (optional)' : 'Password (optional)'}
              <input
                type="password"
                value={form.password}
                onChange={(e) => set('password', e.target.value)}
                className={`${inputClass} mt-1`}
                placeholder={editing ? 'Leave blank to keep current' : 'Auto-generated if blank'}
              />
            </label>
          </div>
          {editing && (
            <label className="flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => set('is_active', e.target.checked)}
                className="rounded border-border"
              />
              Account active (deactivated users cannot log in)
            </label>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className={secondaryBtnClass}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={save.isPending || !form.name}
              className={primaryBtnClass}
            >
              {save.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {editing ? 'Save changes' : 'Create user'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function OneTimeCredentialsCard({
  title,
  subtitle,
  loginId,
  password,
  onClose,
}: {
  title: string;
  subtitle: string;
  loginId: string;
  password: string;
  onClose: () => void;
}) {
  const [showPassword, setShowPassword] = useState(false);
  const [copiedField, setCopiedField] = useState<'id' | 'password' | null>(null);

  function copyToClipboard(text: string, field: 'id' | 'password') {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
      <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-lg border border-success/30 bg-surface p-6 shadow-overlay">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10 text-success">
            <Check className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-ink">{title}</h2>
            <p className="text-sm text-muted">{subtitle}</p>
          </div>
        </div>
        <div className="mt-4 space-y-3 rounded-lg border border-border bg-paper/60 p-4">
          <div>
            <p className="text-xs font-medium text-muted">User ID</p>
            <div className="mt-1 flex items-center gap-2">
              <code className="flex-1 rounded bg-navy/5 px-2 py-1.5 font-mono text-sm font-bold text-ink">{loginId}</code>
              <button
                onClick={() => copyToClipboard(loginId, 'id')}
                className="rounded p-1 text-muted transition hover:bg-surfaceWarm hover:text-ink"
              >
                {copiedField === 'id' ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
              </button>
            </div>
          </div>
          <div>
            <p className="text-xs font-medium text-muted">
              Temporary password <span className="font-normal">(shown only once)</span>
            </p>
            <div className="mt-1 flex items-center gap-2">
              <code className="flex-1 rounded bg-navy/5 px-2 py-1.5 font-mono text-sm font-medium text-ink">
                {showPassword ? password : '••••••'}
              </code>
              <button
                onClick={() => setShowPassword((v) => !v)}
                className="rounded p-1 text-muted transition hover:bg-surfaceWarm hover:text-ink"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
              <button
                onClick={() => copyToClipboard(password, 'password')}
                className="rounded p-1 text-muted transition hover:bg-surfaceWarm hover:text-ink"
              >
                {copiedField === 'password' ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
              </button>
            </div>
          </div>
        </div>
        <p className="mt-3 flex items-start gap-1.5 text-xs text-warning">
          <KeyRound className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          Share these privately — they are never shown again. The user must set
          their own password at next login.
        </p>
        <div className="mt-5 flex justify-end">
          <button onClick={onClose} className={primaryBtnClass}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
