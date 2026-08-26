import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowRight,
  CalendarCheck,
  CalendarOff,
  CalendarPlus,
  CheckCircle2,
  Clock,
  FilePlus2,
  FolderKanban,
  IndianRupee,
  ListTodo,
  Loader2,
  LogIn,
  LogOut,
  Megaphone,
  Palmtree,
  Plus,
  RefreshCw,
  Users,
  Wallet,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { checkIn, checkOut, getMyAttendance, getDateAttendance } from '../../api/attendance';
import { fetchDashboardSummary } from '../../api/auth';
import { getClients } from '../../api/clients';
import { getFinanceOverview } from '../../api/finance';
import { getPendingLeaves, getTeamAvailability } from '../../api/leave';
import { getNotices } from '../../api/notices';
import { getProjects } from '../../api/projects';
import { getTasks } from '../../api/tasks';
import { addDays, weekStartFor } from '../../lib/date';
import { OffsiteMark } from '../../components/BrandLogo';
import { EmptyState } from '../../components/ui/EmptyState';
import { MetricCard } from '../../components/ui/MetricCard';
import { SectionCard } from '../../components/ui/SectionCard';
import { Skeleton } from '../../components/ui/Skeleton';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { TrendChip } from '../../components/ui/TrendChip';
import {
  ATTENDANCE_STATUS_META,
  canAccess,
  formatINR,
  leaveTypeLabel,
  noticeImportanceMeta,
  projectStatusMeta,
  taskPriorityMeta,
  taskStatusMeta,
} from '../../lib/constants';
import { formatDateRange, formatDuration, formatMinutesDuration, formatTime, toISODate } from '../../lib/date';
import type { AttendanceStatus, ProjectStatus, TaskStatus } from '../../lib/types';
import { useAuthStore } from '../../store/authStore';
import { encodeId } from '../../lib/obfuscate';
import { useTranslation } from 'react-i18next';

const CLOSED_PROJECT_STATUSES: ProjectStatus[] = ['completed', 'cancelled', 'on_hold'];
const OPEN_TASK_STATUSES: TaskStatus[] = ['todo', 'in_progress', 'review', 'blocked'];
const PRESENT_STATUSES: AttendanceStatus[] = ['present', 'late', 'work_from_home', 'half_day'];

function greetingForHour(hour: number, t: (key: string) => string): string {
  if (hour < 12) return t('dashboard.greetingMorning');
  if (hour < 17) return t('dashboard.greetingAfternoon');
  return t('dashboard.greetingEvening');
}

function useNow(intervalMs = 30_000): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs]);
  return now;
}

function relativeTime(iso: string | null): string {
  if (!iso) return '—';
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

function dueLabel(due: string | null, todayISO: string): { text: string; overdue: boolean } {
  if (!due) return { text: 'No due date', overdue: false };
  const date = new Date(`${due}T00:00:00`);
  const label = date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
  if (due < todayISO) return { text: `${label} · overdue`, overdue: true };
  if (due === todayISO) return { text: `${label} · today`, overdue: false };
  return { text: label, overdue: false };
}

function workingDuration(checkInISO: string | null | undefined, now: Date): string {
  if (!checkInISO) return '';
  const started = new Date(checkInISO).getTime();
  if (Number.isNaN(started)) return '';
  const totalMinutes = Math.max(0, Math.floor((now.getTime() - started) / 60_000));
  return formatMinutesDuration(totalMinutes);
}

function hoursBetween(startISO: string | null | undefined, endISO: string | null | undefined): string {
  if (!startISO || !endISO) return '';
  const diff = new Date(endISO).getTime() - new Date(startISO).getTime();
  if (Number.isNaN(diff) || diff <= 0) return '';
  return formatDuration(diff / 3_600_000);
}

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

function completedWithinWeek(updatedAt: string | null): boolean {
  if (!updatedAt) return false;
  const time = new Date(updatedAt).getTime();
  if (Number.isNaN(time)) return false;
  return Date.now() - time < WEEK_MS;
}

function AttentionLink({ to, tone, text, count }: { to: string; tone: string; text: string; count: number }) {
  return (
    <Link
      to={to}
      className="group flex items-center justify-between gap-3 rounded-md px-2 py-2.5 transition hover:bg-surfaceWarm"
    >
      <span className="flex items-center gap-2.5 text-sm text-ink">
        <span className={`h-2 w-2 shrink-0 rounded-full ${tone}`} />
        {text}
      </span>
      <span className="flex items-center gap-1 text-sm font-semibold tabular-nums text-ink">
        {count}
        <ArrowRight className="h-3.5 w-3.5 text-muted transition group-hover:translate-x-0.5 group-hover:text-orange" />
      </span>
    </Link>
  );
}

function StatusCounts({
  counts,
  pending,
  error,
  emptyText,
}: {
  counts: Partial<Record<AttendanceStatus, number>>;
  pending: boolean;
  error: boolean;
  emptyText: string;
}) {
  const rows = Object.entries(ATTENDANCE_STATUS_META)
    .filter(([status]) => (counts[status as AttendanceStatus] ?? 0) > 0)
    .slice(0, 4);
  return (
    <>
      {pending ? (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : error ? (
        <p className="text-sm text-danger">Couldn't load attendance.</p>
      ) : rows.length ? (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {rows.map(([status, meta]) => (
            <div
              key={status}
              className="flex items-center justify-between gap-2 rounded-md bg-surfaceWarm px-3 py-2"
            >
              <span className="flex items-center gap-2 text-sm text-ink">
                <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
                {meta.label}
              </span>
              <span className="text-sm font-semibold tabular-nums text-ink">
                {counts[status as AttendanceStatus]}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted">{emptyText}</p>
      )}
    </>
  );
}

function TaskStrip({
  rows,
  dueToday,
  overdue,
  recentlyDone,
  pending,
  error,
  emptyHint = "You're all set — nothing needs your attention.",
}: {
  rows: Array<{ id: number; title: string; project_name: string | null; due_date: string | null; priority: string; status: string }>;
  dueToday: number;
  overdue: number;
  recentlyDone: number;
  pending: boolean;
  error: boolean;
  emptyHint?: string;
}) {
  const todayISO = toISODate(new Date());
  if (pending) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
      </div>
    );
  }
  if (error) return <p className="text-sm text-danger">Couldn't load tasks.</p>;
  const hasChips = dueToday > 0 || overdue > 0 || recentlyDone > 0;
  return (
    <>
      {hasChips && (
        <div className="mb-3 flex flex-wrap gap-2">
          {dueToday > 0 && (
            <span className="inline-flex items-center rounded-md bg-warningSoft px-2 py-0.5 text-xs font-medium text-warning">
              {dueToday} due today
            </span>
          )}
          {overdue > 0 && (
            <span className="inline-flex items-center rounded-md bg-dangerSoft px-2 py-0.5 text-xs font-medium text-danger">
              {overdue} overdue
            </span>
          )}
          {recentlyDone > 0 && (
            <span className="inline-flex items-center rounded-md bg-successSoft px-2 py-0.5 text-xs font-medium text-success">
              {recentlyDone} done this week
            </span>
          )}
        </div>
      )}
      {rows.length ? (
        <div className="-mx-2 divide-y divide-border">
          {rows.map((t) => {
            const due = dueLabel(t.due_date, todayISO);
            return (
              <Link
                key={t.id}
                to="/tasks"
                className="group flex items-start gap-3 rounded-md px-2 py-2.5 transition hover:bg-surfaceWarm"
              >
                <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${taskPriorityMeta(t.priority as never).dot}`} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-ink transition group-hover:text-orange">
                    {t.title}
                  </span>
                  <span className="mt-0.5 block truncate text-xs text-muted">
                    {t.project_name ?? 'No project'} ·{' '}
                    <span className={due.overdue ? 'font-medium text-danger' : ''}>{due.text}</span>
                  </span>
                </span>
                <StatusBadge className={taskStatusMeta(t.status as never).badge}>
                  {taskStatusMeta(t.status as never).label}
                </StatusBadge>
              </Link>
            );
          })}
        </div>
      ) : (
        <EmptyState icon={CheckCircle2} title="No open tasks" text={emptyHint} dashed={false} />
      )}
    </>
  );
}

function ProjectList({
  projects,
  pending,
  error,
  emptyTitle,
  emptyText,
}: {
  projects: Array<{ id: number; name: string; status: string; progress_pct: string; hours_logged: string | null; studio_fee: string | null }>;
  pending: boolean;
  error: boolean;
  emptyTitle: string;
  emptyText: string;
}) {
  if (pending) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }
  if (error) return <p className="text-sm text-danger">Couldn't load projects.</p>;
  if (!projects.length) {
    return <EmptyState icon={FolderKanban} title={emptyTitle} text={emptyText} />;
  }
  return (
    <div className="-mx-2 divide-y divide-border">
      {projects.map((p) => {
        const statusMeta = projectStatusMeta(p.status as never);
        const progress = Math.min(Math.max(Number(p.progress_pct) || 0, 0), 100);
        return (
          <Link
            key={p.id}
            to={`/projects/${encodeId(p.id)}`}
            className="group -mx-2 block rounded-md px-2 py-2.5 transition hover:bg-surfaceWarm"
          >
            <div className="flex items-center justify-between gap-3">
              <p className="truncate text-sm font-medium text-ink transition group-hover:text-orange">{p.name}</p>
              <StatusBadge className={statusMeta.badge}>{statusMeta.label}</StatusBadge>
            </div>
            <div className="mt-2 flex items-center gap-3">
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-navy/10">
                <div className="h-full rounded-full bg-orange transition-all" style={{ width: `${progress}%` }} />
              </div>
              <span className="text-xs tabular-nums text-muted">{progress}%</span>
            </div>
          </Link>
        );
      })}
    </div>
  );
}

const ghostActionClass =
  'inline-flex items-center gap-1.5 rounded-md border border-white/15 px-3 py-1.5 text-xs font-medium text-white/80 transition hover:border-white/30 hover:bg-white/10 hover:text-white';

export default function DashboardPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const now = useNow();
  const level = user?.org_level_code;
  const isAdmin = canAccess(level, 'L2');
  // Financial data is executive-only (L0/L1) per the financial access policy.
  const isExecutive = canAccess(level, 'L1');
  const isLead = canAccess(level, 'L3') && !isAdmin;
  const isEmployee = !isAdmin && !isLead;

  const todayISO = toISODate(now);
  const firstName = user?.name?.trim().split(/\s+/)[0] ?? 'there';
  const teamTasks = isAdmin || isLead;

  const summary = useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: fetchDashboardSummary,
    staleTime: 60_000,
  });

  const projects = useQuery({
    queryKey: ['projects', 'dashboard'],
    queryFn: () => getProjects({ page_size: 50 }),
    staleTime: 60_000,
  });

  const tasks = useQuery({
    queryKey: ['tasks', 'dashboard', teamTasks ? 'team' : 'mine'],
    queryFn: () => getTasks({ assignee: teamTasks ? undefined : user?.id, page_size: 50 }),
    staleTime: 30_000,
  });

  const attendanceToday = useQuery({
    queryKey: ['attendance', 'today'],
    queryFn: () => getDateAttendance(todayISO),
    enabled: isAdmin || isLead,
  });

  const myDay = useQuery({
    queryKey: ['attendance', 'me', 'today'],
    queryFn: () => getMyAttendance(now.getMonth() + 1, now.getFullYear()),
    staleTime: 30_000,
  });

  const pendingLeaves = useQuery({
    queryKey: ['leaves', 'pending', 'dashboard'],
    queryFn: getPendingLeaves,
    enabled: isAdmin || isLead,
    staleTime: 60_000,
  });

  const weekStartISO = weekStartFor(now);
  const weekEndISO = toISODate(addDays(new Date(`${weekStartISO}T00:00:00`), 6));

  const outThisWeek = useQuery({
    queryKey: ['leaves', 'out-this-week', weekStartISO],
    queryFn: () => getTeamAvailability(weekStartISO, weekEndISO),
    enabled: isAdmin || isLead,
    staleTime: 60_000,
  });

  const finance = useQuery({
    queryKey: ['finance', 'overview', 'dashboard'],
    queryFn: () => getFinanceOverview('month', true),
    enabled: isExecutive,
    staleTime: 120_000,
  });

  const clients = useQuery({
    queryKey: ['clients', 'attention'],
    queryFn: () => getClients({ page_size: 100 }),
    enabled: isAdmin || isLead,
    staleTime: 60_000,
  });

  const prevFinance = finance.data?.previous ?? undefined;

  const notices = useQuery({
    queryKey: ['notices', 'dashboard'],
    queryFn: () => getNotices({ include_inactive: false }),
    enabled: isEmployee,
    staleTime: 60_000,
  });

  const invalidateAfterCheck = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['attendance', 'me'] }),
      queryClient.invalidateQueries({ queryKey: ['attendance', 'today'] }),
      queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
    ]);

  const checkInMutation = useMutation({ mutationFn: checkIn, onSuccess: invalidateAfterCheck });
  const checkOutMutation = useMutation({ mutationFn: checkOut, onSuccess: invalidateAfterCheck });

  const lastUpdatedAt = Math.max(
    summary.dataUpdatedAt,
    projects.dataUpdatedAt,
    tasks.dataUpdatedAt,
    attendanceToday.dataUpdatedAt,
    myDay.dataUpdatedAt,
    pendingLeaves.dataUpdatedAt,
    outThisWeek.dataUpdatedAt,
    finance.dataUpdatedAt,
    clients.dataUpdatedAt,
    notices.dataUpdatedAt,
  );
  const lastUpdated = lastUpdatedAt > 0 ? new Date(lastUpdatedAt) : null;

  const refreshDashboard = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
      queryClient.invalidateQueries({ queryKey: ['attendance'] }),
      queryClient.invalidateQueries({ queryKey: ['leaves'] }),
      queryClient.invalidateQueries({ queryKey: ['notices'] }),
      queryClient.invalidateQueries({ queryKey: ['finance'] }),
      queryClient.invalidateQueries({ queryKey: ['projects'] }),
      queryClient.invalidateQueries({ queryKey: ['tasks'] }),
    ]);

  const [refreshing, setRefreshing] = useState(false);
  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refreshDashboard();
    } finally {
      setRefreshing(false);
    }
  };

  const todayRecord = myDay.data?.records.find((r) => r.date === todayISO);
  const checkedIn = Boolean(todayRecord?.check_in_time);
  const checkedOut = Boolean(todayRecord?.check_out_time);
  const dayState = !checkedIn ? 'not-in' : checkedOut ? 'complete' : 'working';
  const dayStatusDot = dayState === 'not-in' ? 'bg-warning' : dayState === 'working' ? 'bg-success' : 'bg-success';
  const dayStatusLabel = dayState === 'not-in' ? 'Not checked in' : dayState === 'working' ? 'Working' : 'Checked out';
  const dayTotalHours =
    formatDuration(todayRecord?.total_hours ?? null) ||
    hoursBetween(todayRecord?.check_in_time ?? null, todayRecord?.check_out_time ?? null);

  const allActiveProjects = useMemo(
    () => (projects.data?.items ?? []).filter((p) => !CLOSED_PROJECT_STATUSES.includes(p.status)),
    [projects.data],
  );

  const activeProjects = useMemo(
    () => [...allActiveProjects].sort((a, b) => Number(a.progress_pct) - Number(b.progress_pct)).slice(0, 4),
    [allActiveProjects],
  );

  const openProjectCount = allActiveProjects.length;

  const openTasks = useMemo(
    () => (tasks.data?.items ?? []).filter((t) => OPEN_TASK_STATUSES.includes(t.status)),
    [tasks.data],
  );

  const tasksDue = openTasks.filter((t) => t.due_date !== null && t.due_date <= todayISO).length;
  const overdueTasks = openTasks.filter((t) => t.due_date !== null && t.due_date < todayISO).length;
  const dueTodayTasks = openTasks.filter((t) => t.due_date === todayISO).length;
  const recentlyDone = (tasks.data?.items ?? []).filter(
    (t) => t.status === 'done' && completedWithinWeek(t.updated_at),
  ).length;

  const taskRows = useMemo(
    () =>
      [...openTasks]
        .sort((a, b) => {
          if (!a.due_date) return 1;
          if (!b.due_date) return -1;
          return a.due_date.localeCompare(b.due_date);
        })
        .slice(0, 4),
    [openTasks],
  );

  const myProjectIds = useMemo(() => {
    const ids = new Set<number>();
    for (const t of tasks.data?.items ?? []) {
      if (t.project_id != null) ids.add(t.project_id);
    }
    return ids;
  }, [tasks.data]);

  const myProjects = useMemo(() => {
    if (myProjectIds.size === 0) return [];
    const byId = new Map(allActiveProjects.map((p) => [p.id, p]));
    return [...myProjectIds]
      .map((id) => byId.get(id))
      .filter((p): p is NonNullable<typeof p> => Boolean(p))
      .slice(0, 3);
  }, [myProjectIds, allActiveProjects]);

  const notCheckedIn = useMemo(
    () =>
      isAdmin || isLead
        ? (attendanceToday.data ?? []).filter((r) => !r.check_in_time && r.status !== 'on_leave').length
        : 0,
    [attendanceToday.data, isAdmin, isLead],
  );

  const pendingLeavesCount = isAdmin || isLead ? (pendingLeaves.data?.length ?? 0) : 0;

  const upcomingFollowUps = useMemo(() => {
    if (!clients.data?.items) return [];
    const today = toISODate(new Date());
    return clients.data.items.filter(
      (c) => c.next_follow_up_date && c.next_follow_up_date <= today && c.deal_stage !== 'won' && c.deal_stage !== 'lost',
    );
  }, [clients.data]);

  const overdueInvoiceCount = finance.data?.overdue_count ?? 0;

  const attendanceCounts = useMemo(() => {
    const counts: Partial<Record<keyof typeof ATTENDANCE_STATUS_META, number>> = {};
    for (const row of attendanceToday.data ?? []) {
      counts[row.status] = (counts[row.status] ?? 0) + 1;
    }
    return counts;
  }, [attendanceToday.data]);

  const myMonthCounts = useMemo(() => {
    const counts: Partial<Record<keyof typeof ATTENDANCE_STATUS_META, number>> = {};
    for (const row of myDay.data?.records ?? []) {
      counts[row.status] = (counts[row.status] ?? 0) + 1;
    }
    return counts;
  }, [myDay.data]);

  const myPresentDays = useMemo(
    () => (myDay.data?.records ?? []).filter((r) => PRESENT_STATUSES.includes(r.status)).length,
    [myDay.data],
  );

  const monthHoursTotal = useMemo(
    () => (myDay.data?.records ?? []).reduce((sum, r) => sum + (Number(r.total_hours) || 0), 0),
    [myDay.data],
  );

  const noticeRows = useMemo(() => {
    const active = (notices.data ?? []).filter((n) => n.is_active !== false);
    return [...active]
      .sort((a, b) =>
        (b.publish_date ?? b.created_at ?? '').localeCompare(a.publish_date ?? a.created_at ?? ''),
      )
      .slice(0, 2);
  }, [notices.data]);

  const approvedOutThisWeek = useMemo(
    () => (outThisWeek.data ?? []).filter((r) => r.status === 'approved'),
    [outThisWeek.data],
  );

  const attentionItems = [
    { to: '/tasks', tone: 'bg-warning', text: 'Tasks due today or overdue', count: tasksDue, show: true },
    {
      to: '/leaves/approvals',
      tone: 'bg-warning',
      text: 'Leave requests awaiting approval',
      count: pendingLeavesCount,
      show: isAdmin || isLead,
    },
    {
      to: '/attendance?tab=today',
      tone: 'bg-danger',
      text: 'Employees not checked in today',
      count: notCheckedIn,
      show: isAdmin || isLead,
    },
    {
      to: '/clients',
      tone: 'bg-info',
      text: 'Client follow-ups due',
      count: upcomingFollowUps.length,
      show: (isAdmin || isLead) && upcomingFollowUps.length > 0,
    },
    {
      to: '/finance/invoices',
      tone: 'bg-danger',
      text: 'Overdue invoices',
      count: overdueInvoiceCount,
      show: isExecutive && overdueInvoiceCount > 0,
    },
  ].filter((item) => item.show && item.count > 0);

  const attentionTotal = attentionItems.reduce((sum, item) => sum + item.count, 0);
  const attentionLoaded =
    tasks.isFetched &&
    (!(isAdmin || isLead) || pendingLeaves.isFetched) &&
    (!(isAdmin || isLead) || attendanceToday.isFetched) &&
    (!(isAdmin || isLead) || clients.isFetched) &&
    (!isExecutive || finance.isFetched);

  const revenueValue = finance.data ? formatINR(Number(finance.data.received)) : undefined;
  const monthHoursLabel = myDay.data?.records.length ? formatDuration(monthHoursTotal) : '—';

  const metricCards = isAdmin
    ? [
        {
          label: 'Total Employees',
          value: summary.data?.total_employees,
          icon: Users,
          pending: summary.isPending,
          failed: summary.isError,
          to: '/employees',
        },
        {
          label: 'Present Today',
          value: summary.data?.present_today,
          context: `of ${summary.data?.total_employees ?? '—'} employees`,
          icon: CheckCircle2,
          pending: summary.isPending,
          failed: summary.isError,
      to: '/attendance?tab=today',
        },
        {
          label: 'Active Projects',
          value: openProjectCount,
          context: `of ${projects.data?.total ?? '—'} projects`,
          icon: FolderKanban,
          pending: projects.isPending,
          failed: projects.isError,
          to: '/projects',
        },
        ...(isExecutive
          ? [
              {
                label: 'Revenue This Month',
                value: revenueValue,
                context: 'received this month',
                trend:
                  finance.data && prevFinance ? (
                    <TrendChip
                      current={Number(finance.data.received)}
                      previous={Number(prevFinance.received)}
                      label="vs last month"
                    />
                  ) : undefined,
                icon: IndianRupee,
                pending: finance.isPending,
                failed: finance.isError,
                to: '/finance/overview',
              },
            ]
          : []),
      ]
    : isLead
      ? [
          {
            label: 'Active Projects',
            value: openProjectCount,
            context: `of ${projects.data?.total ?? '—'} projects`,
            icon: FolderKanban,
            pending: projects.isPending,
            failed: projects.isError,
            to: '/projects',
          },
          {
            label: 'Open Tasks',
            value: openTasks.length,
            context: 'across the team',
            icon: ListTodo,
            pending: tasks.isPending,
            failed: tasks.isError,
            to: '/tasks',
          },
          {
            label: 'Leave Approvals',
            value: pendingLeavesCount,
            context: 'awaiting your approval',
            icon: CalendarCheck,
            pending: pendingLeaves.isPending,
            failed: pendingLeaves.isError,
            to: '/leaves/approvals',
          },
        ]
      : [
          {
            label: 'My Open Tasks',
            value: openTasks.length,
            icon: ListTodo,
            pending: tasks.isPending,
            failed: tasks.isError,
            to: '/tasks',
          },
          {
            label: 'Due Today',
            value: dueTodayTasks,
            icon: Clock,
            pending: tasks.isPending,
            failed: tasks.isError,
            to: '/tasks',
          },
          {
            label: 'Hours This Month',
            value: monthHoursLabel,
            context: 'across all check-ins',
            icon: CalendarCheck,
            pending: myDay.isPending,
            failed: myDay.isError,
            to: '/attendance?tab=my',
          },
          {
            label: 'Days Present',
            value: myPresentDays,
            context: `of ${myDay.data?.records.length ?? '—'} marked this month`,
            icon: CheckCircle2,
            pending: myDay.isPending,
            failed: myDay.isError,
            to: '/attendance?tab=my',
          },
        ];

  const quickActions = isAdmin
    ? [
        { to: '/leaves/apply', label: 'Apply leave', icon: CalendarPlus },
        { to: '/projects', label: 'New project', icon: Plus },
        ...(isExecutive
          ? [{ to: '/finance/invoices', label: 'New invoice', icon: FilePlus2 }]
          : []),
      ]
    : isLead
      ? [
          { to: '/leaves/apply', label: 'Apply leave', icon: CalendarPlus },
          { to: '/projects', label: 'New project', icon: Plus },
          { to: '/tasks', label: 'My tasks', icon: ListTodo },
        ]
      : [
          { to: '/leaves/apply', label: 'Apply leave', icon: CalendarPlus },
          { to: '/tasks', label: 'My tasks', icon: ListTodo },
          { to: '/attendance?tab=my', label: 'My attendance', icon: CalendarCheck },
        ];

  const heroChips = isAdmin || isLead
    ? [
        { icon: CheckCircle2, color: 'text-success', text: `${summary.data?.present_today ?? '—'} present today` },
        { icon: FolderKanban, color: 'text-orange', text: `${projects.isPending ? '…' : openProjectCount} active projects` },
      ]
    : [
        { icon: ListTodo, color: 'text-orange', text: `${openTasks.length} open tasks` },
        { icon: Clock, color: 'text-success', text: `${dueTodayTasks} due today` },
      ];

  const needsAttentionSection = (
    <SectionCard
      title="Needs Attention"
      icon={AlertTriangle}
      delay="120ms"
      action={
        attentionTotal > 0 ? (
          <span className="inline-flex items-center rounded-full bg-warningSoft px-2 py-0.5 text-xs font-semibold text-warning">
            {attentionTotal}
          </span>
        ) : undefined
      }
    >
      {attentionItems.length > 0 ? (
        <div className="-mx-2 divide-y divide-border">
          {attentionItems.map((item) => (
            <AttentionLink key={item.to} {...item} />
          ))}
        </div>
      ) : attentionLoaded ? (
        <div className="flex items-center gap-2.5 rounded-md bg-successSoft px-3 py-3 text-sm text-ink">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-success" />
          {t('dashboard.allCaughtUp')}
        </div>
      ) : (
        <div className="space-y-3">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-2/3" />
        </div>
      )}
    </SectionCard>
  );

  const whoOutSection = (
    <SectionCard
      title="Who's Out This Week"
      icon={CalendarOff}
      delay="140ms"
      action={
        <Link
          to="/leaves/approvals"
          className="inline-flex items-center gap-1 text-sm font-medium text-navy transition hover:text-orange"
        >
          View all
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      }
    >
      {outThisWeek.isPending ? (
        <div className="space-y-3">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : outThisWeek.isError ? (
        <p className="text-sm text-danger">Couldn't load team availability.</p>
      ) : approvedOutThisWeek.length ? (
        <div className="-mx-2 divide-y divide-border">
          {approvedOutThisWeek.slice(0, 4).map((r) => (
            <Link
              key={r.user_id}
              to="/leaves/approvals"
              className="group flex items-center gap-3 rounded-md px-2 py-2.5 transition hover:bg-surfaceWarm"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-warningSoft text-warning">
                <Palmtree className="h-4 w-4" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-ink transition group-hover:text-orange">
                  {r.user_name}
                </span>
                <span className="block truncate text-xs text-muted">
                  {leaveTypeLabel(r.leave_type)} · {formatDateRange(r.from_date, r.to_date)}
                </span>
              </span>
            </Link>
          ))}
        </div>
      ) : (
        <div className="flex items-center gap-2.5 rounded-md bg-successSoft px-3 py-3 text-sm text-ink">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-success" />
          {t('dashboard.noOneOut')}
        </div>
      )}
    </SectionCard>
  );

  const tasksSection = (
    <SectionCard
      title={isLead ? 'Team Tasks' : 'My Tasks'}
      icon={ListTodo}
      delay="160ms"
      action={
        <Link
          to="/tasks"
          className="inline-flex items-center gap-1 text-sm font-medium text-navy transition hover:text-orange"
        >
          Open board
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      }
    >
      <TaskStrip
        rows={taskRows}
        dueToday={dueTodayTasks}
        overdue={overdueTasks}
        recentlyDone={recentlyDone}
        pending={tasks.isPending}
        error={tasks.isError}
        emptyHint={
          isEmployee
            ? 'Nothing assigned yet — ask your lead to add you to a project.'
            : undefined
        }
      />
    </SectionCard>
  );

  const attendanceTodaySection = (
    <SectionCard
      title="Attendance Today"
      icon={CalendarCheck}
      delay="120ms"
      action={
        <Link
          to="/attendance?tab=today"
          className="inline-flex items-center gap-1 text-sm font-medium text-navy transition hover:text-orange"
        >
          View all
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      }
    >
      <StatusCounts
        counts={attendanceCounts}
        pending={attendanceToday.isPending}
        error={attendanceToday.isError}
        emptyText={t('dashboard.noAttendanceToday')}
      />
    </SectionCard>
  );

  const thisMonthSection = (
    <SectionCard
      title="This Month"
      icon={CalendarCheck}
      delay="120ms"
      action={
        <Link
                  to="/attendance?tab=my"
          className="inline-flex items-center gap-1 text-sm font-medium text-navy transition hover:text-orange"
        >
          View all
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      }
    >
      <StatusCounts
        counts={myMonthCounts}
        pending={myDay.isPending}
        error={myDay.isError}
        emptyText="No attendance marked this month."
      />
    </SectionCard>
  );

  const projectHealthSection = (
    <SectionCard
      title="Project Health"
      icon={FolderKanban}
      delay="160ms"
      action={
        <Link
          to="/projects"
          className="inline-flex items-center gap-1 text-sm font-medium text-navy transition hover:text-orange"
        >
          All projects
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      }
    >
      <ProjectList
        projects={activeProjects}
        pending={projects.isPending}
        error={projects.isError}
        emptyTitle={t('dashboard.noActiveProjects')}
        emptyText={t('dashboard.newProjectsWillAppear')}
      />
    </SectionCard>
  );

  const myProjectsSection = (
    <SectionCard
      title="My Projects"
      icon={FolderKanban}
      delay="180ms"
      action={
        myProjects.length ? (
          <Link
            to="/projects"
            className="inline-flex items-center gap-1 text-sm font-medium text-navy transition hover:text-orange"
          >
            All projects
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        ) : undefined
      }
    >
      <ProjectList
        projects={myProjects}
        pending={projects.isPending}
        error={projects.isError}
        emptyTitle="No projects yet"
        emptyText="Projects you have tasks in will appear here with their progress."
      />
    </SectionCard>
  );

  const revenueSnapshotSection = (
    <SectionCard
      title="Revenue Snapshot"
      icon={Wallet}
      delay="200ms"
      action={
        <Link
          to="/finance/overview"
          className="inline-flex items-center gap-1 text-sm font-medium text-navy transition hover:text-orange"
        >
          Finance
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      }
    >
      {finance.isPending ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      ) : finance.isError ? (
        <p className="text-sm text-danger">Couldn't load revenue.</p>
      ) : finance.data ? (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-md bg-surfaceWarm px-3 py-2.5">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">Received</p>
              <p className="mt-1 text-lg font-semibold tabular-nums text-success">
                {formatINR(Number(finance.data.received))}
              </p>
              {prevFinance && (
                <div className="mt-1">
                  <TrendChip
                    current={Number(finance.data.received)}
                    previous={Number(prevFinance.received)}
                    label="vs last month"
                  />
                </div>
              )}
            </div>
            <div className="rounded-md bg-surfaceWarm px-3 py-2.5">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">Outstanding</p>
              <p className="mt-1 text-lg font-semibold tabular-nums text-warning">
                {formatINR(Number(finance.data.outstanding))}
              </p>
            </div>
            <div className="rounded-md bg-surfaceWarm px-3 py-2.5">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">Invoiced</p>
              <p className="mt-1 text-lg font-semibold tabular-nums text-ink">
                {formatINR(Number(finance.data.invoiced))}
              </p>
              {prevFinance && (
                <div className="mt-1">
                  <TrendChip
                    current={Number(finance.data.invoiced)}
                    previous={Number(prevFinance.invoiced)}
                    label="vs last month"
                  />
                </div>
              )}
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-border pt-3 text-xs">
            <span className="text-muted">
              <span className="font-semibold tabular-nums text-ink">{finance.data.overdue_count}</span> overdue
              invoices
            </span>
            <Link
              to="/finance/invoices"
              className="inline-flex items-center gap-1 font-medium text-navy transition hover:text-orange"
            >
              Open invoices
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </>
      ) : null}
    </SectionCard>
  );

  const noticesSection = (
    <SectionCard
      title="Notice Board"
      icon={Megaphone}
      delay="200ms"
      action={
        noticeRows.length ? (
          <Link
            to="/notices"
            className="inline-flex items-center gap-1 text-sm font-medium text-navy transition hover:text-orange"
          >
            View all
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        ) : undefined
      }
    >
      {notices.isPending ? (
        <div className="space-y-3">
          <Skeleton className="h-11 w-full" />
          <Skeleton className="h-11 w-full" />
        </div>
      ) : noticeRows.length ? (
        <div className="-mx-2 divide-y divide-border">
          {noticeRows.map((n) => (
            <Link
              key={n.id}
              to="/notices"
              className="group flex items-center gap-3 rounded-md px-2 py-2.5 transition hover:bg-surfaceWarm"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-warningSoft text-warning">
                <Megaphone className="h-4 w-4" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-ink transition group-hover:text-orange">
                  {n.title}
                </span>
                <span className="mt-0.5 block truncate text-xs text-muted">
                  {n.is_pinned ? 'Pinned · ' : ''}
                  {relativeTime(n.publish_date ?? n.created_at)}
                </span>
              </span>
              <StatusBadge className={noticeImportanceMeta(n.importance).badge}>
                {noticeImportanceMeta(n.importance).label}
              </StatusBadge>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={Megaphone}
          title={t('dashboard.noNoticesYet')}
          text={t('dashboard.studioAnnouncements')}
        />
      )}
    </SectionCard>
  );

  return (
    <div className="relative">
      <div className="arch-grid-paper pointer-events-none absolute inset-0" aria-hidden="true" />

      <div className="relative z-10 space-y-6">
        <section className="animate-rise relative overflow-hidden rounded-lg bg-navy shadow-card">
          <div className="arch-grid-light pointer-events-none absolute inset-0" aria-hidden="true" />
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full border border-white/10"
          />
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -bottom-32 right-48 h-64 w-64 rounded-full border border-white/5"
          />
          <OffsiteMark
            className="pointer-events-none absolute -left-6 -top-6 h-36 w-36 text-white/[0.04]"
            aria-hidden="true"
          />

          <div className="relative z-10 flex flex-col gap-5 p-5 sm:p-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="min-w-0">
              <div className="mb-2.5 h-px w-12 bg-orange" aria-hidden="true" />
              <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                {greetingForHour(now.getHours(), t)}, {firstName}
              </h1>
              <p className="mt-1 text-sm text-white/60">
                {now.toLocaleDateString('en-IN', {
                  weekday: 'long',
                  day: 'numeric',
                  month: 'long',
                  year: 'numeric',
                })}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {heroChips.map((chip) => (
                  <span
                    key={chip.text}
                    className="inline-flex items-center gap-1.5 rounded-md border border-white/15 bg-white/5 px-2.5 py-1 text-xs font-medium text-white/80"
                  >
                    <chip.icon className={`h-3.5 w-3.5 ${chip.color}`} />
                    {chip.text}
                  </span>
                ))}
              </div>
            </div>

            <div className="w-full max-w-sm shrink-0">
              <div className="rounded-lg border border-white/10 bg-surface/95 p-4 shadow-card">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted">Your day</p>
                  <span className="flex items-center gap-1.5 text-xs font-medium text-graphite">
                    <span className={`h-2 w-2 rounded-full ${dayStatusDot}`} />
                    {dayStatusLabel}
                  </span>
                </div>

                <div className="mt-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">Current time</p>
                  <div className="mt-0.5 flex items-center gap-2">
                    <Clock className="h-5 w-5 text-navy" />
                    <p className="text-2xl font-semibold tracking-tight text-ink">
                      {now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })}
                    </p>
                  </div>
                </div>

                {dayState !== 'not-in' && (
                  <div className="mt-3 space-y-0.5 border-t border-border pt-2.5">
                    {dayState === 'working' && (
                      <p className="text-xs text-muted">
                        Checked in at {formatTime(todayRecord?.check_in_time ?? null)}
                      </p>
                    )}
                    {dayState === 'working' && (
                      <p className="text-xs font-medium text-success">
                        Working {workingDuration(todayRecord?.check_in_time, now)}
                      </p>
                    )}
                    {dayState === 'complete' && (
                      <p className="text-xs text-muted">
                        {formatTime(todayRecord?.check_in_time ?? null)} →{' '}
                        {formatTime(todayRecord?.check_out_time ?? null)}
                      </p>
                    )}
                    {dayState === 'complete' && (
                      <p className="text-xs font-medium text-success">Last session {dayTotalHours}</p>
                    )}
                    {dayState === 'complete' && Number(todayRecord?.overtime_hours ?? 0) > 0 && (
                      <p className="text-xs font-medium text-warning">
                        OT {formatDuration(todayRecord?.overtime_hours ?? null)}
                      </p>
                    )}
                  </div>
                )}

                <div className="mt-4">
                  {dayState === 'not-in' ? (
                    <button
                      onClick={() => checkInMutation.mutate({ method: 'web' })}
                      disabled={checkInMutation.isPending}
                      className="flex h-10 w-full items-center justify-center gap-2 rounded-md bg-orange text-sm font-medium text-white transition hover:bg-orangeDark focus:outline-none focus:ring-2 focus:ring-orange/40 focus:ring-offset-2 focus:ring-offset-surface disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {checkInMutation.isPending ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Checking in…
                        </>
                      ) : (
                        <>
                          <LogIn className="h-4 w-4" />
                          Check In
                        </>
                      )}
                    </button>
                  ) : dayState === 'working' ? (
                    <button
                      onClick={() => checkOutMutation.mutate(undefined)}
                      disabled={checkOutMutation.isPending}
                      className="flex h-10 w-full items-center justify-center gap-2 rounded-md bg-navy text-sm font-medium text-white transition hover:bg-navyDark focus:outline-none focus:ring-2 focus:ring-navy/40 focus:ring-offset-2 focus:ring-offset-surface disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {checkOutMutation.isPending ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Checking out…
                        </>
                      ) : (
                        <>
                          <LogOut className="h-4 w-4" />
                          Check Out
                        </>
                      )}
                    </button>
                  ) : (
                    <button
                      onClick={() => checkInMutation.mutate({ method: 'web' })}
                      disabled={checkInMutation.isPending}
                      className="flex h-10 w-full items-center justify-center gap-2 rounded-md bg-orange text-sm font-medium text-white transition hover:bg-orangeDark focus:outline-none focus:ring-2 focus:ring-orange/40 focus:ring-offset-2 focus:ring-offset-surface disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {checkInMutation.isPending ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Checking in…
                        </>
                      ) : (
                        <>
                          <LogIn className="h-4 w-4" />
                          Check In Again
                        </>
                      )}
                    </button>
                  )}
                </div>

                <Link
          to="/attendance?tab=my"
                  className="mt-3 flex items-center justify-center gap-1 text-xs font-medium text-navy transition hover:text-orange"
                >
                  View my attendance
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                {quickActions.map((action) => (
                  <Link key={action.label} to={action.to} className={ghostActionClass}>
                    <action.icon className="h-3.5 w-3.5" />
                    {action.label}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </section>

        <div className="flex items-center justify-end gap-2">
          <p className="text-xs text-muted">
            {lastUpdated ? `Updated ${relativeTime(lastUpdated.toISOString())}` : 'Updating…'}
          </p>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs font-medium text-navy transition hover:bg-surfaceWarm hover:text-orange focus:outline-none focus:ring-2 focus:ring-orange/40 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {metricCards.map((card, i) => (
            <div key={card.label} className="animate-rise" style={{ animationDelay: `${40 + i * 40}ms` }}>
              <MetricCard {...card} />
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {isAdmin && needsAttentionSection}
          {isAdmin && attendanceTodaySection}
          {isAdmin && whoOutSection}
          {isAdmin && projectHealthSection}
          {isExecutive && revenueSnapshotSection}

          {isLead && needsAttentionSection}
          {isLead && whoOutSection}
          {isLead && tasksSection}
          {isLead && projectHealthSection}

          {isEmployee && tasksSection}
          {isEmployee && whoOutSection}
          {isEmployee && myProjectsSection}
          {isEmployee && thisMonthSection}
          {isEmployee && noticesSection}
        </div>
      </div>
    </div>
  );
}
