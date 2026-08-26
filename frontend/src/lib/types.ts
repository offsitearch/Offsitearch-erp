/**
 * Central type definitions for the Studio ERP frontend.
 *
 * Mirrors the backend Pydantic schemas. Keep in sync with
 * backend/app/schemas/ when adding new entities or fields.
 */

/** Organizational seniority level (L1–L6). Drives authorization: L1 is most senior. */
export interface OrgLevel {
  id: number;
  code: string;
  name: string;
  description: string | null;
  rank: number;
  is_active: boolean;
}

export interface User {
  id: number;
  login_id: string;
  employee_id: string | null;
  email: string;
  contact_email: string | null;
  name: string;
  department_id: number | null;
  org_level_id?: number | null;
  org_level_code?: string | null;
  org_level_name?: string | null;
  designation: string | null;
  must_change_password?: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface DashboardSummary {
  total_employees: number;
  present_today: number;
  active_projects: number;
  revenue_this_month: number;
  pending_tasks: number;
}

export type AttendanceStatus =
  | 'present'
  | 'absent'
  | 'late'
  | 'half_day'
  | 'work_from_home'
  | 'on_leave';

export type AttendanceMethod = 'web' | 'manual' | 'qr' | 'gps' | 'ip';

export interface AttendanceRecord {
  id: number;
  user_id: number;
  date: string;
  check_in_time: string | null;
  check_out_time: string | null;
  status: AttendanceStatus;
  late_minutes: number;
  total_hours: string | null;
  check_in_method: AttendanceMethod;
  check_in_location: string | null;
  notes: string | null;
  marked_by: number | null;
}

export interface AttendanceUserRow extends AttendanceRecord {
  user_name: string;
  employee_id: string | null;
  designation: string | null;
  department: string | null;
}

export interface MonthlySummary {
  user: User;
  records: AttendanceRecord[];
  totals: Record<string, number>;
}

export interface Holiday {
  id: number;
  name: string;
  date: string;
  is_recurring: boolean;
}

export interface ReportRow {
  date: string;
  user_id: number;
  user_name: string;
  employee_id: string | null;
  designation: string | null;
  department: string | null;
  phone: string | null;
  status: AttendanceStatus;
  check_in_time: string | null;
  check_out_time: string | null;
  late_minutes: number;
  total_hours: string | null;
}

export interface UserBrief {
  id: number;
  login_id: string;
  employee_id: string | null;
  name: string;
  email: string;
  contact_email: string | null;
  department_id: number | null;
  department: string | null;
  org_level_id?: number | null;
  org_level_code?: string | null;
  org_level_name?: string | null;
  designation: string | null;
  is_active: boolean;
}

export type LeaveType =
  | 'casual'
  | 'sick'
  | 'earned'
  | 'compensatory'
  | 'maternity'
  | 'paternity'
  | 'work_from_home'
  | 'unpaid';

export type LeaveStatus = 'pending' | 'approved' | 'rejected' | 'cancelled';

export interface LeaveBalance {
  leave_type: LeaveType;
  year: number;
  allocated: string;
  used: string;
  remaining: string;
}

export interface LeaveRecord {
  id: number;
  user_id: number;
  leave_type: LeaveType;
  from_date: string;
  to_date: string;
  total_days: string;
  half_day_first: boolean;
  half_day_second: boolean;
  reason: string | null;
  status: LeaveStatus;
  approved_by: number | null;
  approved_at: string | null;
  rejection_reason: string | null;
  created_at: string;
}

export interface LeaveUserRow extends LeaveRecord {
  user_name: string;
  employee_id: string | null;
  designation: string | null;
  department: string | null;
}

export interface TeamAvailabilityRow {
  user_id: number;
  user_name: string;
  department: string | null;
  leave_type: LeaveType;
  status: LeaveStatus;
  from_date: string;
  to_date: string;
}

export interface EmployeeProfile {
  id: number;
  login_id?: string;
  employee_id: string | null;
  email: string;
  contact_email: string | null;
  phone: string | null;
  name: string;
  department_id: number | null;
  department: string | null;
  org_level_id: number | null;
  org_level_code: string | null;
  org_level_name: string | null;
  designation: string | null;
  reporting_to_id: number | null;
  reports_to_name: string | null;
  date_of_joining: string | null;
  date_of_birth: string | null;
  gender: string | null;
  blood_group: string | null;
  address: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  skills: string[] | null;
  employment_type: string;
  is_active: boolean;
  created_at: string;
}

export interface EmployeeListItem {
  id: number;
  employee_id: string | null;
  name: string;
  email: string;
  contact_email: string | null;
  department: string | null;
  org_level_code: string | null;
  org_level_name: string | null;
  designation: string | null;
  employment_type: string;
  is_active: boolean;
}

export interface EmployeePage {
  items: EmployeeListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface SalaryRecord {
  user_id: number;
  ctc_annual: string;
  basic: string;
  hra: string;
  special_allowance: string;
  pf_deduction: string;
  bank_name: string | null;
  account_number: string | null;
  ifsc_code: string | null;
  effective_from: string | null;
}

export interface EmployeeDocument {
  id: number;
  user_id: number;
  doc_type: string;
  file_name: string;
  uploaded_by: number | null;
  uploaded_at: string;
}

export interface Department {
  id: number;
  name: string;
  head_id: number | null;
  description: string | null;
  is_active: boolean;
  head_name: string | null;
  member_count: number;
}

export interface OrgChartNode {
  user_id: number;
  name: string;
  employee_id: string | null;
  designation: string | null;
  department_id: number | null;
  department_name: string | null;
  org_level_code: string | null;
  org_level_name: string | null;
  reports_to_id: number | null;
  children: OrgChartNode[];
}

export interface AttendanceSummary {
  user_id: number;
  month: number;
  year: number;
  totals: Record<string, number>;
  total_hours: string;
  days_worked: number;
}

export type ProjectType =
  | 'residential'
  | 'commercial'
  | 'interior'
  | 'institutional'
  | 'landscape'
  | 'urban_planning'
  | 'renovation'
  | 'mixed_use';

export type ProjectStatus =
  | 'draft'
  | 'concept'
  | 'design'
  | 'under_review'
  | 'in_construction'
  | 'completed'
  | 'on_hold'
  | 'cancelled';

export type PhaseStatus = 'not_started' | 'in_progress' | 'completed' | 'delayed';

export type ClientType = 'individual' | 'company' | 'developer' | 'government';

export type CommunicationType = 'call' | 'email' | 'meeting' | 'site_visit';

export interface ProjectPhase {
  id: number;
  project_id: number;
  name: string;
  order_index: number;
  start_date: string | null;
  end_date: string | null;
  status: PhaseStatus;
  completion_pct: string;
  studio_fee: string | null;
}

export interface ProjectTeamMember {
  id: number;
  user_id: number;
  name: string;
  designation: string | null;
  role: string | null;
}

export interface ProjectListItem {
  id: number;
  project_code: string;
  name: string;
  project_type: ProjectType;
  client_id: number | null;
  client_name: string | null;
  location: string | null;
  status: ProjectStatus;
  project_lead_id: number | null;
  lead_name: string | null;
  priority: string;
  start_date: string | null;
  end_date: string | null;
  progress_pct: string;
  budget: string | null;
  studio_fee: string | null;
  hours_logged: string | null;
}

export interface ProjectPage {
  items: ProjectListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface ProjectDetail {
  id: number;
  project_code: string;
  name: string;
  description: string | null;
  project_type: ProjectType;
  category: string | null;
  client_id: number | null;
  client_name: string | null;
  location: string | null;
  plot_area: string | null;
  built_up_area: string | null;
  no_of_floors: string | null;
  coordinates: string | null;
  // Money fields are omitted by the API below the financial boundary (L0/L1).
  budget?: string | null;
  studio_fee?: string | null;
  fee_type?: string | null;
  fee_percent?: string | null;
  start_date: string | null;
  end_date: string | null;
  status: ProjectStatus;
  project_lead_id: number | null;
  lead_name: string | null;
  priority: string;
  progress_pct: string;
  team: ProjectTeamMember[];
  phases: ProjectPhase[];
  created_at: string;
}

export interface ProjectCreateInput {
  name: string;
  project_type: ProjectType;
  description?: string;
  category?: string;
  client_id?: number | null;
  location?: string;
  plot_area?: number | null;
  built_up_area?: number | null;
  no_of_floors?: string;
  budget?: number | null;
  studio_fee?: number | null;
  fee_type?: string;
  fee_percent?: number | null;
  start_date?: string | null;
  end_date?: string | null;
  status?: ProjectStatus;
  project_lead_id?: number | null;
  priority?: string;
  team?: { user_id: number; role?: string | null }[];
}

export interface TimelineRow {
  id: number;
  name: string;
  order_index: number;
  status: PhaseStatus;
  start_date: string | null;
  end_date: string | null;
  completion_pct: string;
}

export interface TimelineData {
  project_id: number;
  start_date: string | null;
  end_date: string | null;
  rows: TimelineRow[];
}

export interface PhaseTemplate {
  project_type: ProjectType;
  label: string;
  phases: string[];
}

export interface ClientListItem {
  id: number;
  name: string;
  client_type: ClientType;
  company_name: string | null;
  contact_person: string | null;
  phone: string | null;
  email: string | null;
  source: string | null;
  // Omitted by the API below the financial boundary (L0/L1).
  budget_range?: string | null;
  deal_stage: string;
  next_follow_up_date: string | null;
  next_follow_up_action: string | null;
  is_active: boolean;
  project_count: number;
}

export interface ClientPage {
  items: ClientListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface ClientDetail {
  id: number;
  name: string;
  client_type: ClientType;
  company_name: string | null;
  contact_person: string | null;
  phone: string | null;
  phone_secondary: string | null;
  email: string | null;
  address: string | null;
  gst_number: string | null;
  pan_number: string | null;
  source: string | null;
  referred_by: number | null;
  referred_name: string | null;
  // Omitted by the API below the financial boundary (L0/L1).
  budget_range?: string | null;
  interest: string | null;
  notes: string | null;
  deal_stage: string;
  next_follow_up_date: string | null;
  next_follow_up_action: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ClientProjectSummary {
  id: number;
  project_code: string;
  name: string;
  project_type: ProjectType;
  status: ProjectStatus;
  start_date: string | null;
  end_date: string | null;
  progress_pct: string;
  budget: string | null;
  studio_fee: string | null;
}

export interface FinancialSummary {
  total_projects: number;
  // Money fields are omitted by the API below the financial boundary (L0/L1).
  total_budget?: string;
  total_studio_fee?: string;
  invoiced?: string;
  received?: string;
  outstanding?: string;
}

export interface Communication {
  id: number;
  client_id: number;
  user_id: number;
  user_name: string;
  type: CommunicationType;
  subject: string | null;
  notes: string | null;
  occurred_at: string;
}

export interface ClientProfile {
  client: ClientDetail;
  projects: ClientProjectSummary[];
  communications: Communication[];
  financial_summary: FinancialSummary;
}

export interface ClientCreateInput {
  name: string;
  client_type?: ClientType;
  company_name?: string;
  contact_person?: string;
  phone?: string;
  phone_secondary?: string;
  email?: string;
  address?: string;
  gst_number?: string;
  pan_number?: string;
  source?: string;
  referred_by?: number | null;
  budget_range?: string;
  interest?: string;
  notes?: string;
  deal_stage?: string;
  next_follow_up_date?: string | null;
  next_follow_up_action?: string | null;
}

export interface CommunicationInput {
  type: CommunicationType;
  subject?: string;
  notes?: string;
  occurred_at?: string;
}

export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent';

export type TaskStatus = 'todo' | 'in_progress' | 'review' | 'done' | 'blocked';

export interface ChecklistItem {
  id: number;
  task_id: number;
  text: string;
  is_done: boolean;
}

export interface Task {
  id: number;
  title: string;
  description: string | null;
  project_id: number | null;
  project_name: string | null;
  phase_id: number | null;
  assigned_to: number | null;
  assignee_name: string | null;
  priority: TaskPriority;
  status: TaskStatus;
  start_date: string | null;
  due_date: string | null;
  estimated_hours: string | null;
  actual_hours: string | null;
  parent_task_id: number | null;
  tags: string[] | null;
  checklist: ChecklistItem[];
  created_at: string;
  updated_at: string;
}

export interface TaskPage {
  items: Task[];
  total: number;
  page: number;
  page_size: number;
}

export interface TaskBoardColumn {
  status: TaskStatus;
  tasks: Task[];
}

export interface TaskBoardData {
  columns: TaskBoardColumn[];
}

export interface TaskCreateInput {
  title: string;
  description?: string;
  project_id?: number | null;
  phase_id?: number | null;
  assigned_to?: number | null;
  priority?: TaskPriority;
  status?: TaskStatus;
  start_date?: string | null;
  due_date?: string | null;
  estimated_hours?: number | null;
  tags?: string[];
}

export interface TaskUpdateInput {
  title?: string;
  description?: string;
  project_id?: number | null;
  phase_id?: number | null;
  assigned_to?: number | null;
  priority?: TaskPriority;
  status?: TaskStatus;
  start_date?: string | null;
  due_date?: string | null;
  estimated_hours?: number | null;
  actual_hours?: number | null;
  tags?: string[];
}

export type InvoiceStatus = 'draft' | 'sent' | 'partial' | 'paid' | 'overdue' | 'cancelled';

export type PaymentMethod = 'bank_transfer' | 'upi' | 'cash' | 'cheque' | 'card';

export type ExpenseStatus = 'pending' | 'approved' | 'rejected';

export type ExpenseCategory =
  | 'travel'
  | 'material'
  | 'software'
  | 'printing'
  | 'subcontract'
  | 'office'
  | 'utilities'
  | 'salary'
  | 'other';

export interface InvoiceItem {
  id: number;
  invoice_id: number;
  description: string;
  hsn_sac: string | null;
  quantity: string;
  rate: string;
  amount: string;
}

export interface InvoiceItemInput {
  description: string;
  hsn_sac?: string | null;
  quantity: number;
  rate: number;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  client_id: number;
  client_name: string | null;
  project_id: number | null;
  project_code: string | null;
  invoice_date: string;
  due_date: string;
  subtotal: string;
  tax_percent: string;
  tax_amount: string;
  total: string;
  status: InvoiceStatus;
  sent_at: string | null;
  paid_amount: string;
  payment_date: string | null;
  payment_method: PaymentMethod | null;
  notes: string | null;
  terms: string | null;
  items: InvoiceItem[];
}

export interface InvoiceCreateInput {
  client_id: number;
  project_id?: number | null;
  invoice_date: string;
  due_date: string;
  tax_percent: number;
  items: InvoiceItemInput[];
  notes?: string | null;
  terms?: string | null;
}

export interface Expense {
  id: number;
  category: ExpenseCategory;
  description: string | null;
  amount: string;
  expense_date: string | null;
  project_id: number | null;
  project_code: string | null;
  paid_by: string | null;
  receipt_path: string | null;
  status: ExpenseStatus;
  approved_by: number | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PayrollEntry {
  user_id: number;
  user_name: string | null;
  employee_id: string | null;
  designation: string | null;
  department: string | null;
  working_days: number;
  gross_salary: string;
  deductions: string;
  net_pay: string;
}

export interface PayrollRun {
  id: number | null;
  month: number;
  year: number;
  status: string;
  processed_by: number | null;
  processed_at: string | null;
  is_preview: boolean;
  total_pay: string;
  entries: PayrollEntry[];
}

export interface FinanceOverview {
  period: string;
  from: string;
  to: string;
  invoiced: string;
  received: string;
  outstanding: string;
  expenses: string;
  profit: string;
  invoice_count: number;
  paid_count: number;
  overdue_count: number;
  expense_count: number;
  previous?: FinanceOverview | null;
}

export type NoticeImportance = 'low' | 'medium' | 'high';

export interface Notice {
  id: number;
  title: string;
  body: string | null;
  importance: NoticeImportance;
  is_pinned: boolean;
  is_active: boolean;
  publish_date: string | null;
  expiry_date: string | null;
  created_by: number | null;
  created_at: string;
}

export interface NoticeInput {
  title: string;
  body?: string | null;
  importance?: NoticeImportance;
  is_pinned?: boolean;
  is_active?: boolean;
  publish_date?: string | null;
  expiry_date?: string | null;
}

export type MeetingType = 'internal' | 'client' | 'site' | 'video';
export type MeetingStatus = 'scheduled' | 'completed' | 'cancelled';
export type RsvpStatus = 'pending' | 'accepted' | 'declined';

export interface MeetingAttendee {
  user_id: number;
  name: string;
  email: string;
  rsvp_status: RsvpStatus;
}

export interface Meeting {
  id: number;
  title: string;
  description: string | null;
  meeting_type: MeetingType;
  scheduled_at: string;
  duration_minutes: number;
  location: string | null;
  meeting_link: string | null;
  status: MeetingStatus;
  organizer_id: number | null;
  organizer_name: string | null;
  attendees: MeetingAttendee[];
  my_rsvp: RsvpStatus | null;
}

export interface MeetingInput {
  title: string;
  description?: string | null;
  meeting_type?: MeetingType;
  scheduled_at: string;
  duration_minutes?: number;
  location?: string | null;
  meeting_link?: string | null;
  status?: MeetingStatus;
  attendee_ids?: number[];
}

export interface Notification {
  id: number;
  title: string;
  body: string | null;
  type: string;
  link: string | null;
  read_at: string | null;
  created_at: string;
}

export type SiteVisitStatus = 'scheduled' | 'completed' | 'cancelled';

export interface SiteVisitPhoto {
  id: number;
  file_path: string;
  caption: string | null;
  uploaded_by: number | null;
  uploaded_at: string;
}

export interface SiteVisit {
  id: number;
  project_id: number | null;
  project_code: string | null;
  project_name: string | null;
  visit_date: string;
  start_time: string | null;
  end_time: string | null;
  status: SiteVisitStatus;
  purpose: string | null;
  notes: string | null;
  location: string | null;
  weather: string | null;
  attendance_notes: string | null;
  created_by: number | null;
  creator_name: string | null;
  completed_at: string | null;
  photos: SiteVisitPhoto[];
}

export interface SiteVisitInput {
  project_id: number;
  visit_date: string;
  start_time?: string | null;
  end_time?: string | null;
  status?: SiteVisitStatus;
  purpose?: string | null;
  notes?: string | null;
  location?: string | null;
  weather?: string | null;
  attendance_notes?: string | null;
}

export interface Setting {
  id: number;
  group: string;
  key: string;
  value: Record<string, unknown>;
}

export interface SettingInput {
  group: string;
  key: string;
  value: Record<string, unknown>;
}

export interface HolidayInput {
  name: string;
  date: string;
  is_recurring?: boolean;
  applicable_to?: string;
}

export interface HolidayFull extends Holiday {
  applicable_to: string;
}

export interface UserAdmin extends UserBrief {
  org_level_id: number | null;
  phone: string | null;
  date_of_joining: string | null;
}

export interface UserAdminCreateOut extends UserAdmin {
  generated_password: string;
}

/** One-time view of a freshly regenerated password. Never stored. */
export interface RegeneratedCredentials {
  login_id: string;
  name: string;
  generated_password: string;
}

export interface UserCreateInput {
  name: string;
  contact_email?: string | null;
  password?: string;
  department_id?: number | null;
  org_level_id?: number | null;
  designation?: string | null;
  employee_id?: string | null;
  phone?: string | null;
  date_of_joining?: string | null;
}

export interface UserUpdateInput {
  name?: string;
  contact_email?: string | null;
  password?: string;
  department_id?: number | null;
  /** Send 0 to clear the level, a level id to set it; omit to leave unchanged. */
  org_level_id?: number | null;
  designation?: string | null;
  employee_id?: string | null;
  phone?: string | null;
  is_active?: boolean;
}

export interface EmployeeCreateOut extends EmployeeProfile {
  generated_password: string;
}

export interface ChangePasswordInput {
  current_password: string;
  new_password: string;
}

export type ReportFormat = 'json' | 'csv' | 'xlsx';

export interface ReportResponse {
  title: string;
  summary: Record<string, string | number>;
  rows: Array<Record<string, string | number | null>>;
  columns?: string[];
}

export interface AttendanceReportRow {
  date: string;
  user_id: number;
  user_name: string;
  employee_id: string | null;
  designation: string | null;
  department: string | null;
  phone: string | null;
  status: string;
  check_in_time: string | null;
  check_out_time: string | null;
  late_minutes: number;
  total_hours: string | null;
}

/* ── Typed report payloads (/reports/*) ─────────────────────── */

export interface ProjectsReportRow {
  project_code: string;
  name: string;
  client_name: string | null;
  project_type: string;
  status: string;
  progress_pct: number;
  budget: number | string | null;
  studio_fee: number | string | null;
  expenses: number | string;
  hours_logged: number;
}

export interface ProjectsReportData {
  title: string;
  summary: {
    total_projects: number;
    active_projects: number;
    total_budget: number | string;
    total_studio_fee: number | string;
    total_expenses: number | string;
    total_hours: number;
  };
  rows: ProjectsReportRow[];
}

export interface FinanceReportRow {
  invoice_number: string;
  client_name: string | null;
  invoice_date: string;
  due_date: string | null;
  total: number | string;
  paid_amount: number | string;
  outstanding: number | string;
  status: string;
}

export interface FinanceExpenseRow {
  category: string;
  amount: number | string;
}

export interface FinanceReportData {
  title: string;
  summary: {
    period: string;
    from: string;
    to: string;
    invoiced: number | string;
    received: number | string;
    outstanding: number | string;
    expenses: number | string;
    profit: number | string;
    invoice_count: number;
  };
  rows: FinanceReportRow[];
  expense_rows: FinanceExpenseRow[];
  aging: { '0_30': number | string; '31_60': number | string; '61_90': number | string; '90_plus': number | string };
}

export interface HrReportRow {
  employee_id: string | null;
  name: string;
  department: string | null;
  designation: string | null;
  org_level_code: string | null;
  present_days: number;
  absent_days: number;
  attendance_pct: number | null;
  leave_days_ytd: number;
}

export interface HrReportData {
  title: string;
  summary: {
    month: number;
    year: number;
    total_employees: number;
    total_present_days: number;
    total_absent_days: number;
    avg_attendance_pct: number | null;
  };
  rows: HrReportRow[];
  headcount_dept: Array<{ department: string; count: number }>;
  headcount_level: Array<{ level: string; count: number }>;
}

export interface TimesheetReportGroup {
  label: string;
  hours: number;
  rows: Array<{
    date: string | null;
    project: string;
    description: string | null;
    hours: number;
  }>;
}

export interface TimesheetReportEmployee {
  user_id: number;
  employee_id: string | null;
  employee_name: string;
  department: string | null;
  total_hours: number;
  groups: TimesheetReportGroup[];
}

export interface TimesheetsReportData {
  title: string;
  summary: {
    from: string;
    to: string;
    group_by: 'day' | 'week' | 'month';
    total_hours: number;
    employees: number;
    projects: number;
    periods: number;
  };
  rows: Array<{
    project_code: string | null;
    project_name: string;
    employee_id: string | null;
    employee_name: string;
    hours: number;
  }>;
  employees: TimesheetReportEmployee[];
}

/* ── Backup (L0/L1 only) ────────────────────────────────────── */

export interface BackupStatus {
  configured: boolean;
  connected: boolean;
  account_email: string | null;
  auto_enabled: boolean;
  frequency: string;
  last_backup_at: string | null;
  last_backup_status: string | null;
}

export interface BackupHistoryEntry {
  id: number;
  status: string;
  trigger: string;
  destination: string;
  file_name: string | null;
  file_size_bytes: number | null;
  error_message: string | null;
  created_at: string;
}

/* ── Timesheets ─────────────────────────────────────────────── */

export type TimesheetStatus = 'draft' | 'submitted' | 'approved' | 'rejected';

export interface TimesheetEntry {
  id: number;
  project_id: number | null;
  task_id: number | null;
  date: string;
  hours: string | number;
  description: string | null;
  project_name?: string | null;
  task_title?: string | null;
}

export type TimesheetDayStatus = TimesheetStatus;

export interface TimesheetDay {
  date: string;
  status: TimesheetDayStatus;
  submitted_at?: string | null;
  approved_by_name?: string | null;
  approved_at?: string | null;
  rejection_reason?: string | null;
}

export interface TimesheetDetail {
  id: number;
  user_id: number;
  user_name: string | null;
  employee_id: string | null;
  week_start: string;
  week_end: string;
  status: TimesheetStatus;
  total_hours: string | number;
  submitted_at: string | null;
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  entries: TimesheetEntry[];
  days?: TimesheetDay[];
}

export interface TimesheetRow {
  id: number;
  user_id: number;
  user_name: string | null;
  employee_id: string | null;
  department: string | null;
  week_start: string;
  week_end: string;
  status: TimesheetStatus;
  total_hours: string | number;
  entry_count: number;
  submitted_at: string | null;
  approved_by_name: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
}

export interface TimesheetPage {
  items: TimesheetRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface TimesheetWeekSaveInput {
  week_start: string;
  entries: Array<{
    project_id?: number | null;
    task_id?: number | null;
    date: string;
    hours: number;
    description?: string | null;
  }>;
}
