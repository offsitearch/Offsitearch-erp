/**
 * UI constants: role labels, status metadata, sidebar nav, and
 * label/display-name mappings for every domain enum.
 */
import type {
  AttendanceMethod,
  AttendanceStatus,
  ClientType,
  CommunicationType,
  ExpenseCategory,
  ExpenseStatus,
  InvoiceStatus,
  LeaveStatus,
  LeaveType,
  MeetingStatus,
  MeetingType,
  NoticeImportance,
  PaymentMethod,
  PhaseStatus,
  ProjectStatus,
  ProjectType,
  SiteVisitStatus,
  TaskPriority,
  TaskStatus,
  TimesheetStatus,
} from './types';
import type { LucideIcon } from 'lucide-react';
import { CheckCircle2, Clock, Home, MinusCircle, Palmtree, XCircle } from 'lucide-react';

// ── Organizational seniority levels (L0–L6) ──────────────────────────
// L0 is the most senior. Authorization = "at least this level".

export const LEVEL_ORDER = ['L0', 'L1', 'L2', 'L3', 'L4', 'L5', 'L6'] as const;
export type LevelCode = (typeof LEVEL_ORDER)[number];

export const LEVEL_LABELS: Record<LevelCode, string> = {
  L0: 'CEO',
  L1: 'Director',
  L2: 'Department Head',
  L3: 'Project / Team Lead',
  L4: 'Sr. Professional',
  L5: 'Professional',
  L6: 'Intern',
};

export const LEVEL_DESCRIPTIONS: Record<LevelCode, string> = {
  L0: 'Chief Executive Officer — founder/owner; highest authority',
  L1: 'Single studio director — executive authority (only one)',
  L2: 'Operations head, delivery head, etc.',
  L3: 'Project manager, project lead, team lead, etc.',
  L4: 'Sr. architect, Sr. designer, etc.',
  L5: 'Architect, designer, etc.',
  L6: 'Interns and entry-level staff',
};

/** Tailwind classes for level chips, keyed by level code. */
export const LEVEL_BADGE: Record<LevelCode, string> = {
  L0: 'bg-ink text-paper',
  L1: 'bg-danger/10 text-danger',
  L2: 'bg-orange/10 text-orange',
  L3: 'bg-navy/10 text-navy',
  L4: 'bg-orangeDark/10 text-orangeDark',
  L5: 'bg-graphite/10 text-graphite',
  L6: 'bg-success/10 text-success',
};

/** Returns the canonical label for an org-level code, or the code itself. */
export function levelLabel(code: string | null | undefined): string {
  if (!code) return '';
  return LEVEL_LABELS[code as LevelCode] ?? code;
}

/** Rank of a level code (1 = most senior); unknown codes sort last. */
export function levelRank(code: string | null | undefined): number {
  if (!code) return LEVEL_ORDER.length + 1;
  const idx = LEVEL_ORDER.indexOf(code as LevelCode);
  return idx === -1 ? LEVEL_ORDER.length + 1 : idx + 1;
}

const EMPLOYMENT_TYPE_LABELS: Record<string, string> = {
  FULL_TIME: 'Full Time',
  PART_TIME: 'Part Time',
  CONTRACT: 'Contract',
  INTERNSHIP: 'Internship',
};

/** Formats an employment type (e.g. "FULL_TIME") as "Full Time". */
export function employmentTypeLabel(type: string | null | undefined): string {
  if (!type) return '—';
  return (
    EMPLOYMENT_TYPE_LABELS[type] ??
    type.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

/** True when the user's level is equal or senior to the required level. */
export function canAccess(userLevel: string | null | undefined, required: string): boolean {
  if (!userLevel) return false;
  return levelRank(userLevel) <= levelRank(required);
}

interface StatusMeta {
  label: string;
  dot: string;
  cell: string;
  badge: string;
}

interface AttendanceStatusMeta extends StatusMeta {
  onDark: string;
  iconColor: string;
  icon: LucideIcon;
  short: string;
}

export const ATTENDANCE_STATUS_META: Record<AttendanceStatus, AttendanceStatusMeta> = {
  present: {
    label: 'Present',
    short: 'Present',
    dot: 'bg-success',
    cell: 'bg-successSoft',
    badge: 'bg-successSoft text-success',
    onDark: 'text-success',
    iconColor: 'text-success',
    icon: CheckCircle2,
  },
  late: {
    label: 'Late',
    short: 'Late',
    dot: 'bg-warning',
    cell: 'bg-warningSoft',
    badge: 'bg-warningSoft text-warning',
    onDark: 'text-warning',
    iconColor: 'text-warning',
    icon: Clock,
  },
  half_day: {
    label: 'Half Day',
    short: 'Half Day',
    dot: 'bg-navy',
    cell: 'bg-navy/10',
    badge: 'bg-navy/10 text-navy',
    onDark: 'text-info',
    iconColor: 'text-navy',
    icon: MinusCircle,
  },
  work_from_home: {
    label: 'Work From Home',
    short: 'WFH',
    dot: 'bg-info',
    cell: 'bg-infoSoft',
    badge: 'bg-infoSoft text-info',
    onDark: 'text-info',
    iconColor: 'text-info',
    icon: Home,
  },
  absent: {
    label: 'Absent',
    short: 'Absent',
    dot: 'bg-danger',
    cell: 'bg-dangerSoft',
    badge: 'bg-dangerSoft text-danger',
    onDark: 'text-danger',
    iconColor: 'text-danger',
    icon: XCircle,
  },
  on_leave: {
    label: 'On Leave',
    short: 'On Leave',
    dot: 'bg-navy',
    cell: 'bg-navy/10',
    badge: 'bg-navy/10 text-navy',
    onDark: 'text-info',
    iconColor: 'text-navy',
    icon: Palmtree,
  },
};

export const ATTENDANCE_STATUS_OPTIONS: AttendanceStatus[] = [
  'present',
  'late',
  'half_day',
  'work_from_home',
  'absent',
  'on_leave',
];

export const ATTENDANCE_METHOD_LABELS: Record<AttendanceMethod, string> = {
  web: 'Web',
  manual: 'Manual',
  qr: 'QR',
  gps: 'GPS',
  ip: 'IP',
};

export const LEAVE_TYPE_LABELS: Record<LeaveType, string> = {
  casual: 'Casual Leave',
  sick: 'Sick Leave',
  earned: 'Earned Leave',
  compensatory: 'Compensatory Off',
  maternity: 'Maternity Leave',
  paternity: 'Paternity Leave',
  work_from_home: 'Work From Home',
  unpaid: 'Unpaid Leave',
};

export const LEAVE_TYPE_OPTIONS: LeaveType[] = [
  'casual',
  'sick',
  'earned',
  'compensatory',
  'maternity',
  'paternity',
  'work_from_home',
  'unpaid',
];

export const LEAVE_STATUS_META: Record<LeaveStatus, StatusMeta> = {
  pending: { label: 'Pending', dot: 'bg-warning', cell: 'bg-warningSoft', badge: 'bg-warningSoft text-warning' },
  approved: { label: 'Approved', dot: 'bg-success', cell: 'bg-successSoft', badge: 'bg-successSoft text-success' },
  rejected: { label: 'Rejected', dot: 'bg-danger', cell: 'bg-dangerSoft', badge: 'bg-dangerSoft text-danger' },
  cancelled: { label: 'Cancelled', dot: 'bg-graphite/40', cell: 'bg-graphite/10', badge: 'bg-graphite/10 text-muted' },
};

export function leaveTypeLabel(type: LeaveType): string {
  return LEAVE_TYPE_LABELS[type] ?? type;
}

export function leaveStatusMeta(status: LeaveStatus) {
  return LEAVE_STATUS_META[status] ?? LEAVE_STATUS_META.pending;
}

export const TIMESHEET_STATUS_META: Record<TimesheetStatus, StatusMeta> = {
  draft: { label: 'Draft', dot: 'bg-graphite/40', cell: 'bg-graphite/10', badge: 'bg-graphite/10 text-muted' },
  submitted: { label: 'Submitted', dot: 'bg-warning', cell: 'bg-warningSoft', badge: 'bg-warningSoft text-warning' },
  approved: { label: 'Approved', dot: 'bg-success', cell: 'bg-successSoft', badge: 'bg-successSoft text-success' },
  rejected: { label: 'Rejected', dot: 'bg-danger', cell: 'bg-dangerSoft', badge: 'bg-dangerSoft text-danger' },
};

export function timesheetStatusMeta(status: TimesheetStatus) {
  return TIMESHEET_STATUS_META[status] ?? TIMESHEET_STATUS_META.draft;
}

/** Hours after which a logged day counts as overtime (display-only chip). */
export const STANDARD_WORKDAY_HOURS = 8;

export const PROJECT_TYPE_LABELS: Record<ProjectType, string> = {
  residential: 'Residential',
  commercial: 'Commercial',
  interior: 'Interior',
  institutional: 'Institutional',
  landscape: 'Landscape',
  urban_planning: 'Urban Planning',
  renovation: 'Renovation',
  mixed_use: 'Mixed-Use',
};

export const PROJECT_TYPE_OPTIONS: ProjectType[] = [
  'residential',
  'commercial',
  'interior',
  'institutional',
  'landscape',
  'urban_planning',
  'renovation',
  'mixed_use',
];

export const PROJECT_STATUS_META: Record<ProjectStatus, StatusMeta> = {
  draft: { label: 'Draft', dot: 'bg-graphite/40', cell: 'bg-graphite/10', badge: 'bg-graphite/10 text-muted' },
  concept: { label: 'Concept', dot: 'bg-info', cell: 'bg-infoSoft', badge: 'bg-infoSoft text-info' },
  design: { label: 'Design', dot: 'bg-navy', cell: 'bg-navy/10', badge: 'bg-navy/10 text-navy' },
  under_review: { label: 'Under Review', dot: 'bg-warning', cell: 'bg-warningSoft', badge: 'bg-warningSoft text-warning' },
  in_construction: { label: 'In Construction', dot: 'bg-orange', cell: 'bg-orange/10', badge: 'bg-orange/10 text-orange' },
  completed: { label: 'Completed', dot: 'bg-success', cell: 'bg-successSoft', badge: 'bg-successSoft text-success' },
  on_hold: { label: 'On Hold', dot: 'bg-navy', cell: 'bg-navy/10', badge: 'bg-navy/10 text-navy' },
  cancelled: { label: 'Cancelled', dot: 'bg-danger', cell: 'bg-dangerSoft', badge: 'bg-dangerSoft text-danger' },
};

export const PROJECT_STATUS_OPTIONS: ProjectStatus[] = [
  'draft',
  'concept',
  'design',
  'under_review',
  'in_construction',
  'completed',
  'on_hold',
  'cancelled',
];

export const PHASE_STATUS_META: Record<PhaseStatus, StatusMeta> = {
  not_started: { label: 'Not Started', dot: 'bg-graphite/40', cell: 'bg-graphite/10', badge: 'bg-graphite/10 text-muted' },
  in_progress: { label: 'In Progress', dot: 'bg-info', cell: 'bg-infoSoft', badge: 'bg-infoSoft text-info' },
  completed: { label: 'Completed', dot: 'bg-success', cell: 'bg-successSoft', badge: 'bg-successSoft text-success' },
  delayed: { label: 'Delayed', dot: 'bg-danger', cell: 'bg-dangerSoft', badge: 'bg-dangerSoft text-danger' },
};

export const CLIENT_TYPE_LABELS: Record<ClientType, string> = {
  individual: 'Individual',
  company: 'Company',
  developer: 'Developer',
  government: 'Government',
};

export const CLIENT_TYPE_OPTIONS: ClientType[] = ['individual', 'company', 'developer', 'government'];

export const CLIENT_TYPE_META: Record<ClientType, StatusMeta> = {
  individual: { label: 'Individual', dot: 'bg-graphite/40', cell: 'bg-graphite/10', badge: 'bg-graphite/10 text-muted' },
  company: { label: 'Company', dot: 'bg-info', cell: 'bg-infoSoft', badge: 'bg-infoSoft text-info' },
  developer: { label: 'Developer', dot: 'bg-navy', cell: 'bg-navy/10', badge: 'bg-navy/10 text-navy' },
  government: { label: 'Government', dot: 'bg-navy', cell: 'bg-navy/10', badge: 'bg-navy/10 text-navy' },
};

export function clientTypeMeta(type: ClientType) {
  return CLIENT_TYPE_META[type] ?? CLIENT_TYPE_META.individual;
}

export const COMMUNICATION_TYPE_LABELS: Record<CommunicationType, string> = {
  call: 'Call',
  email: 'Email',
  meeting: 'Meeting',
  site_visit: 'Site Visit',
};

export const COMMUNICATION_TYPE_OPTIONS: CommunicationType[] = ['call', 'email', 'meeting', 'site_visit'];

export function projectTypeLabel(type: ProjectType): string {
  return PROJECT_TYPE_LABELS[type] ?? type;
}

export function projectStatusMeta(status: ProjectStatus) {
  return PROJECT_STATUS_META[status] ?? PROJECT_STATUS_META.draft;
}

export function phaseStatusMeta(status: PhaseStatus) {
  return PHASE_STATUS_META[status] ?? PHASE_STATUS_META.not_started;
}

export function clientTypeLabel(type: ClientType): string {
  return CLIENT_TYPE_LABELS[type] ?? type;
}

export const TASK_PRIORITY_META: Record<TaskPriority, { label: string; badge: string; dot: string }> = {
  low: { label: 'Low', badge: 'bg-graphite/10 text-muted', dot: 'bg-graphite/40' },
  medium: { label: 'Medium', badge: 'bg-infoSoft text-info', dot: 'bg-info' },
  high: { label: 'High', badge: 'bg-warningSoft text-warning', dot: 'bg-warning' },
  urgent: { label: 'Urgent', badge: 'bg-dangerSoft text-danger', dot: 'bg-danger' },
};

export const TASK_PRIORITY_OPTIONS: TaskPriority[] = ['low', 'medium', 'high', 'urgent'];

export const TASK_STATUS_META: Record<TaskStatus, StatusMeta> = {
  todo: { label: 'To Do', dot: 'bg-graphite/40', cell: 'bg-graphite/10', badge: 'bg-graphite/10 text-muted' },
  in_progress: { label: 'In Progress', dot: 'bg-info', cell: 'bg-infoSoft', badge: 'bg-infoSoft text-info' },
  review: { label: 'In Review', dot: 'bg-warning', cell: 'bg-warningSoft', badge: 'bg-warningSoft text-warning' },
  done: { label: 'Done', dot: 'bg-success', cell: 'bg-successSoft', badge: 'bg-successSoft text-success' },
  blocked: { label: 'Blocked', dot: 'bg-danger', cell: 'bg-dangerSoft', badge: 'bg-dangerSoft text-danger' },
};

export function taskStatusMeta(status: TaskStatus) {
  return TASK_STATUS_META[status] ?? TASK_STATUS_META.todo;
}

export function taskPriorityMeta(priority: TaskPriority) {
  return TASK_PRIORITY_META[priority] ?? TASK_PRIORITY_META.medium;
}

export const INVOICE_STATUS_META: Record<InvoiceStatus, StatusMeta> = {
  draft: { label: 'Draft', dot: 'bg-graphite/40', cell: 'bg-graphite/10', badge: 'bg-graphite/10 text-muted' },
  sent: { label: 'Sent', dot: 'bg-info', cell: 'bg-infoSoft', badge: 'bg-infoSoft text-info' },
  partial: { label: 'Partially Paid', dot: 'bg-warning', cell: 'bg-warningSoft', badge: 'bg-warningSoft text-warning' },
  paid: { label: 'Paid', dot: 'bg-success', cell: 'bg-successSoft', badge: 'bg-successSoft text-success' },
  overdue: { label: 'Overdue', dot: 'bg-danger', cell: 'bg-dangerSoft', badge: 'bg-dangerSoft text-danger' },
  cancelled: { label: 'Cancelled', dot: 'bg-graphite/40', cell: 'bg-graphite/10', badge: 'bg-graphite/10 text-muted' },
};

export function invoiceStatusMeta(status: InvoiceStatus) {
  return INVOICE_STATUS_META[status] ?? INVOICE_STATUS_META.draft;
}

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  bank_transfer: 'Bank Transfer',
  upi: 'UPI',
  cash: 'Cash',
  cheque: 'Cheque',
  card: 'Card',
};

export const PAYMENT_METHOD_OPTIONS: PaymentMethod[] = [
  'bank_transfer',
  'upi',
  'cash',
  'cheque',
  'card',
];

export function paymentMethodLabel(method: PaymentMethod | null | undefined): string {
  if (!method) return '—';
  return PAYMENT_METHOD_LABELS[method] ?? method;
}

export const EXPENSE_STATUS_META: Record<ExpenseStatus, StatusMeta> = {
  pending: { label: 'Pending', dot: 'bg-warning', cell: 'bg-warningSoft', badge: 'bg-warningSoft text-warning' },
  approved: { label: 'Approved', dot: 'bg-success', cell: 'bg-successSoft', badge: 'bg-successSoft text-success' },
  rejected: { label: 'Rejected', dot: 'bg-danger', cell: 'bg-dangerSoft', badge: 'bg-dangerSoft text-danger' },
};

export function expenseStatusMeta(status: ExpenseStatus) {
  return EXPENSE_STATUS_META[status] ?? EXPENSE_STATUS_META.pending;
}

export const EXPENSE_CATEGORY_LABELS: Record<ExpenseCategory, string> = {
  travel: 'Travel',
  material: 'Material',
  software: 'Software',
  printing: 'Printing',
  subcontract: 'Subcontract',
  office: 'Office',
  utilities: 'Utilities',
  salary: 'Salary',
  other: 'Other',
};

export const EXPENSE_CATEGORY_OPTIONS: ExpenseCategory[] = [
  'travel',
  'material',
  'software',
  'printing',
  'subcontract',
  'office',
  'utilities',
  'salary',
  'other',
];

export function expenseCategoryLabel(category: ExpenseCategory): string {
  return EXPENSE_CATEGORY_LABELS[category] ?? category;
}

export const PAYROLL_STATUS_META: Record<string, StatusMeta> = {
  draft: { label: 'Draft', dot: 'bg-graphite/40', cell: 'bg-graphite/10', badge: 'bg-graphite/10 text-muted' },
  processed: { label: 'Processed', dot: 'bg-success', cell: 'bg-successSoft', badge: 'bg-successSoft text-success' },
};

export function payrollStatusMeta(status: string) {
  return PAYROLL_STATUS_META[status] ?? PAYROLL_STATUS_META.draft;
}

export function formatINR(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—';
  const num = Number(value);
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(num);
}

export const NOTICE_IMPORTANCE_META: Record<NoticeImportance, StatusMeta> = {
  low: { label: 'Low', dot: 'bg-graphite/40', cell: 'bg-graphite/10', badge: 'bg-graphite/10 text-muted' },
  medium: { label: 'Medium', dot: 'bg-info', cell: 'bg-infoSoft', badge: 'bg-infoSoft text-info' },
  high: { label: 'High', dot: 'bg-danger', cell: 'bg-dangerSoft', badge: 'bg-dangerSoft text-danger' },
};

export function noticeImportanceMeta(importance: NoticeImportance) {
  return NOTICE_IMPORTANCE_META[importance] ?? NOTICE_IMPORTANCE_META.medium;
}

export const MEETING_TYPE_LABELS: Record<MeetingType, string> = {
  internal: 'Internal',
  client: 'Client',
  site: 'Site',
  video: 'Video call',
};

export const MEETING_TYPE_OPTIONS: MeetingType[] = ['internal', 'client', 'site', 'video'];

export function meetingTypeLabel(type: MeetingType): string {
  return MEETING_TYPE_LABELS[type] ?? type;
}

export const MEETING_STATUS_META: Record<MeetingStatus, StatusMeta> = {
  scheduled: { label: 'Scheduled', dot: 'bg-info', cell: 'bg-infoSoft', badge: 'bg-infoSoft text-info' },
  completed: { label: 'Completed', dot: 'bg-success', cell: 'bg-successSoft', badge: 'bg-successSoft text-success' },
  cancelled: { label: 'Cancelled', dot: 'bg-danger', cell: 'bg-dangerSoft', badge: 'bg-dangerSoft text-danger' },
};

export function meetingStatusMeta(status: MeetingStatus) {
  return MEETING_STATUS_META[status] ?? MEETING_STATUS_META.scheduled;
}

export const SITE_VISIT_STATUS_META: Record<SiteVisitStatus, StatusMeta> = {
  scheduled: { label: 'Scheduled', dot: 'bg-info', cell: 'bg-infoSoft', badge: 'bg-infoSoft text-info' },
  completed: { label: 'Completed', dot: 'bg-success', cell: 'bg-successSoft', badge: 'bg-successSoft text-success' },
  cancelled: { label: 'Cancelled', dot: 'bg-danger', cell: 'bg-dangerSoft', badge: 'bg-dangerSoft text-danger' },
};

export function siteVisitStatusMeta(status: SiteVisitStatus) {
  return SITE_VISIT_STATUS_META[status] ?? SITE_VISIT_STATUS_META.scheduled;
}

export const DEAL_STAGE_META: Record<string, { label: string; badge: string; dot: string }> = {
  lead: { label: 'Lead', badge: 'bg-infoSoft text-info', dot: 'bg-info' },
  proposal: { label: 'Proposal', badge: 'bg-warningSoft text-warning', dot: 'bg-warning' },
  negotiation: { label: 'Negotiation', badge: 'bg-navy/10 text-navy', dot: 'bg-navy' },
  won: { label: 'Won', badge: 'bg-successSoft text-success', dot: 'bg-success' },
  lost: { label: 'Lost', badge: 'bg-dangerSoft text-danger', dot: 'bg-danger' },
};
export const DEAL_STAGE_OPTIONS = ['lead', 'proposal', 'negotiation', 'won', 'lost'] as const;
