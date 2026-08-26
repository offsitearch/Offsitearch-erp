import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Save, Settings as SettingsIcon } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getSettings, upsertSettings } from '../../api/settings';
import { Skeleton } from '../../components/ui/Skeleton';
import TimeInput from '../../components/ui/TimeInput';
import { useToast } from '../../components/Toast';
import { canAccess } from '../../lib/constants';
import type { Setting } from '../../lib/types';
import { useAuthStore } from '../../store/authStore';
import { HolidaysTab } from './HolidaysTab';
import { SecurityTab } from './SecurityTab';
import { UsersTab } from './UsersTab';
import { BackupTab } from './BackupTab';
import { inputClass, primaryBtnClass, modalLabelClass } from '../../lib/styles';

type TabKey = 'company' | 'attendance' | 'leave' | 'holidays' | 'users' | 'security' | 'backup';

const BASE_TABS: { key: TabKey; label: string }[] = [
  { key: 'company', label: 'Company' },
  { key: 'attendance', label: 'Attendance' },
  { key: 'leave', label: 'Leave Policy' },
  { key: 'holidays', label: 'Holidays' },
  { key: 'users', label: 'Users' },
  { key: 'security', label: 'Security' },
];

export default function SettingsPage() {
  const { toast } = useToast();
  const [searchParams] = useSearchParams();
  const me = useAuthStore((s) => s.user);
  // Backup carries every table in the DB (incl. salary/finance) — L0/L1 only.
  const canSeeBackup = canAccess(me?.org_level_code, 'L1');

  // Google OAuth lands back on /settings?tab=backup&drive=<result>.
  const requestedTab = searchParams.get('tab');
  const driveResult = searchParams.get('drive');
  const initialTab: TabKey =
    requestedTab === 'backup' && canSeeBackup ? 'backup' : 'company';
  const [tab, setTab] = useState<TabKey>(initialTab);

  useEffect(() => {
    if (driveResult === 'connected') toast('Google Drive connected — one-click backups are ready', 'success');
    else if (driveResult === 'error') toast('Google Drive connection failed. Please try again.', 'error');
    else if (driveResult === 'not_configured')
      toast('Google backup needs one-time server setup first (see instructions)', 'error');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [driveResult]);

  const tabs = canSeeBackup ? [...BASE_TABS, { key: 'backup' as TabKey, label: 'Backup' }] : BASE_TABS;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-ink sm:text-2xl">Settings & Admin</h1>
        <p className="mt-1 text-sm text-muted">
          Company profile, attendance & leave policy, holidays and user accounts.
        </p>
      </div>

      <div className="flex flex-wrap gap-1.5 rounded-lg border border-border bg-surface p-1">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition ${
              tab === t.key ? 'bg-orange text-white' : 'text-muted hover:text-ink'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'company' && <CompanyTab />}
      {tab === 'attendance' && <AttendanceTab />}
      {tab === 'leave' && <LeaveTab />}
      {tab === 'holidays' && <HolidaysTab />}
      {tab === 'users' && <UsersTab />}
      {tab === 'security' && <SecurityTab />}
      {tab === 'backup' && canSeeBackup && <BackupTab />}
    </div>
  );
}

function SettingsForm({
  title,
  subtitle,
  icon,
  children,
  saving,
  onSave,
}: {
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  saving: boolean;
  onSave: () => void;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy/10 text-navy">
          {icon}
        </div>
        <div>
          <h2 className="text-base font-bold text-ink">{title}</h2>
          <p className="text-sm text-muted">{subtitle}</p>
        </div>
      </div>
      <div className="mt-5 space-y-4">{children}</div>
      <div className="mt-5 flex justify-end border-t border-border pt-4">
        <button onClick={onSave} disabled={saving} className={primaryBtnClass}>
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Save changes
        </button>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children?: React.ReactNode }) {
  return (
    <label className={modalLabelClass}>
      {label}
      <div className="mt-1">{children}</div>
    </label>
  );
}

function useSettingsGroup(group: string) {
  return useQuery({
    queryKey: ['settings', group],
    queryFn: () => getSettings(group),
  });
}

function CompanyTab() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const settings = useSettingsGroup('company');

  const [form, setForm] = useState<Record<string, string>>({});
  const initialized = useFormSync(settings.data, 'company', 'profile', form, setForm);

  const save = useMutation({
    mutationFn: () => upsertSettings([{ group: 'company', key: 'profile', value: form }]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'company'] });
      toast('Company profile saved', 'success');
    },
    onError: () => toast('Failed to save company profile', 'error'),
  });

  if (!initialized) return <FormSkeleton />;

  const fields: { key: string; label: string }[] = [
    { key: 'name', label: 'Company name' },
    { key: 'tagline', label: 'Tagline' },
    { key: 'address', label: 'Address' },
    { key: 'phone', label: 'Phone' },
    { key: 'email', label: 'Email' },
    { key: 'gstin', label: 'GSTIN' },
    { key: 'website', label: 'Website' },
  ];

  const paymentFields: { key: string; label: string }[] = [
    { key: 'bank_name', label: 'Bank name' },
    { key: 'account_name', label: 'Account name' },
    { key: 'account_number', label: 'Account number' },
    { key: 'ifsc_code', label: 'IFSC code' },
  ];

  return (
    <SettingsForm
      title="Company profile"
      subtitle="Details shown on invoices and PDF reports."
      icon={<SettingsIcon className="h-5 w-5" />}
      saving={save.isPending}
      onSave={() => save.mutate()}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        {fields.map((f) => (
          <Field key={f.key} label={f.label}>
            <input
              value={form[f.key] ?? ''}
              onChange={(e) => setForm((prev) => ({ ...prev, [f.key]: e.target.value }))}
              className={inputClass}
            />
          </Field>
        ))}
      </div>

      <div className="border-t border-border pt-4">
        <p className="text-sm font-semibold text-ink">Invoice payment details</p>
        <p className="mt-0.5 text-xs text-muted">Shown on the invoice so clients know how to pay you.</p>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          {paymentFields.map((f) => (
            <Field key={f.key} label={f.label}>
              <input
                value={form[f.key] ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, [f.key]: e.target.value }))}
                className={inputClass}
              />
            </Field>
          ))}
          <Field label="UPI ID">
            <input
              value={form.upi_id ?? ''}
              onChange={(e) => setForm((prev) => ({ ...prev, upi_id: e.target.value }))}
              placeholder="studio@upi"
              className={inputClass}
            />
          </Field>
        </div>
      </div>

      <div className="border-t border-border pt-4">
        <Field label="Default invoice terms">
          <textarea
            value={form.default_terms ?? ''}
            onChange={(e) => setForm((prev) => ({ ...prev, default_terms: e.target.value }))}
            rows={3}
            placeholder="e.g. Payment due within 30 days. 1.5% monthly interest on overdue amounts."
            className={`${inputClass} w-full h-auto py-2`}
          />
        </Field>
        <p className="mt-1 text-xs text-muted">
          Used when an invoice has no terms of its own.
        </p>
      </div>
    </SettingsForm>
  );
}

function AttendanceTab() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const settings = useSettingsGroup('attendance');

  const [form, setForm] = useState<{ start: string; end: string; break_minutes: string; min_hours: string }>({
    start: '09:00',
    end: '18:00',
    break_minutes: '60',
    min_hours: '8',
  });
  const [late, setLate] = useState<Record<string, string | number | boolean>>({});
  const initialized = useSettingsLoaded(
    settings.data,
    (list) => {
      const wh = list.find((s: Setting) => s.key === 'working_hours')?.value as Record<string, string | number> | undefined;
      if (wh) {
        setForm({
          start: String(wh.start ?? '09:00'),
          end: String(wh.end ?? '18:00'),
          break_minutes: String(wh.break_minutes ?? 60),
          min_hours: String(wh.min_hours ?? 8),
        });
      }
      const lp = list.find((s: Setting) => s.key === 'late_policy')?.value as Record<string, string | number | boolean> | undefined;
      if (lp) setLate({ ...lp });
    },
  );

  const save = useMutation({
    mutationFn: () =>
      upsertSettings([
        {
          group: 'attendance',
          key: 'working_hours',
          value: { start: form.start, end: form.end, break_minutes: Number(form.break_minutes), min_hours: Number(form.min_hours) },
        },
        { group: 'attendance', key: 'late_policy', value: late },
      ]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'attendance'] });
      toast('Attendance settings saved', 'success');
    },
    onError: () => toast('Failed to save attendance settings', 'error'),
  });

  if (!initialized) return <FormSkeleton />;

  return (
    <SettingsForm
      title="Attendance policy"
      subtitle="Working hours, grace period and late thresholds."
      icon={<SettingsIcon className="h-5 w-5" />}
      saving={save.isPending}
      onSave={() => save.mutate()}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Work start">
          <TimeInput
            value={form.start}
            onChange={(v) => setForm((p) => ({ ...p, start: v }))}
          />
        </Field>
        <Field label="Work end">
          <TimeInput
            value={form.end}
            onChange={(v) => setForm((p) => ({ ...p, end: v }))}
          />
        </Field>
        <Field label="Break (minutes)">
          <input
            type="number"
            value={form.break_minutes}
            onChange={(e) => setForm((p) => ({ ...p, break_minutes: e.target.value }))}
            className={inputClass}
          />
        </Field>
        <Field label="Minimum hours / day">
          <input
            type="number"
            step="0.5"
            value={form.min_hours}
            onChange={(e) => setForm((p) => ({ ...p, min_hours: e.target.value }))}
            className={inputClass}
          />
        </Field>
        <Field label="Grace minutes">
          <input
            type="number"
            value={String(late.grace_minutes ?? '')}
            onChange={(e) => setLate((p) => ({ ...p, grace_minutes: Number(e.target.value) }))}
            className={inputClass}
          />
        </Field>
        <Field label="Late threshold">
          <TimeInput
            value={String(late.late_threshold ?? '09:15')}
            onChange={(v) => setLate((p) => ({ ...p, late_threshold: v }))}
          />
        </Field>
      </div>
      <label className="flex items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          checked={Boolean(late.three_late_equals_one_leave)}
          onChange={(e) => setLate((p) => ({ ...p, three_late_equals_one_leave: e.target.checked }))}
          className="rounded border-border"
        />
        Three late marks equal one leave
      </label>
    </SettingsForm>
  );
}

const LEAVE_TYPE_FIELDS: { key: string; label: string }[] = [
  { key: 'casual', label: 'Casual leave' },
  { key: 'sick', label: 'Sick leave' },
  { key: 'earned', label: 'Earned leave' },
  { key: 'compensatory', label: 'Compensatory off' },
  { key: 'maternity', label: 'Maternity' },
  { key: 'paternity', label: 'Paternity' },
  { key: 'work_from_home', label: 'Work from home' },
  { key: 'unpaid', label: 'Unpaid' },
];

function LeaveTab() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const settings = useSettingsGroup('leave');
  const [form, setForm] = useState<Record<string, string>>({});
  const [carryForward, setCarryForward] = useState('5');
  const initialized = useSettingsLoaded(
    settings.data,
    (list) => {
      const policy = list.find((s: Setting) => s.key === 'policy')?.value as Record<string, number> | undefined;
      if (policy) {
        const next: Record<string, string> = {};
        for (const [k, v] of Object.entries(policy)) {
          next[k] = String(v);
        }
        setForm(next);
        setCarryForward(String(policy.carry_forward ?? 5));
      }
    },
  );

  const save = useMutation({
    mutationFn: () => {
      const policy: Record<string, number> = { carry_forward: Number(carryForward) };
      for (const f of LEAVE_TYPE_FIELDS) {
        policy[f.key] = Number(form[f.key] ?? 0);
      }
      return upsertSettings([{ group: 'leave', key: 'policy', value: policy }]);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'leave'] });
      toast('Leave policy saved', 'success');
    },
    onError: () => toast('Failed to save leave policy', 'error'),
  });

  if (!initialized) return <FormSkeleton />;

  return (
    <SettingsForm
      title="Leave policy"
      subtitle="Annual entitlement per leave type (in days)."
      icon={<SettingsIcon className="h-5 w-5" />}
      saving={save.isPending}
      onSave={() => save.mutate()}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        {LEAVE_TYPE_FIELDS.map((f) => (
          <Field key={f.key} label={f.label}>
            <input
              type="number"
              value={form[f.key] ?? ''}
              onChange={(e) => setForm((p) => ({ ...p, [f.key]: e.target.value }))}
              className={inputClass}
            />
          </Field>
        ))}
        <Field label="Carry forward (days)">
          <input
            type="number"
            value={carryForward}
            onChange={(e) => setCarryForward(e.target.value)}
            className={inputClass}
          />
        </Field>
      </div>
    </SettingsForm>
  );
}

function useFormSync(
  settingsData: Setting[] | undefined,
  group: string,
  key: string,
  form: Record<string, string>,
  setForm: (v: Record<string, string>) => void,
): boolean {
  const [done, setDone] = useState(false);
  useEffect(() => {
    if (done || !settingsData) return;
    const entry = settingsData.find((s) => s.group === group && s.key === key);
    if (entry) {
      const value = (entry.value ?? {}) as Record<string, string>;
      if (Object.keys(form).length === 0) {
        setForm({ ...value });
      }
    }
    setDone(true);
  }, [done, settingsData, group, key, form, setForm]);
  return done;
}

function useSettingsLoaded(
  settingsData: Setting[] | undefined,
  apply: (list: Setting[]) => void,
): boolean {
  const [done, setDone] = useState(false);
  useEffect(() => {
    if (done || !settingsData) return;
    apply(settingsData);
    setDone(true);
  }, [done, settingsData, apply]);
  return done;
}

function FormSkeleton() {
  return (
    <div className="space-y-4 rounded-xl border border-border bg-surface p-5 shadow-card">
      <Skeleton className="h-6 w-1/3 rounded" />
      <Skeleton className="h-24 w-full rounded" />
      <Skeleton className="h-24 w-full rounded" />
    </div>
  );
}
