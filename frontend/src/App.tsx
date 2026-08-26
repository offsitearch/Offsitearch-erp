import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { MobileBlockScreen } from './components/MobileBlockScreen';
import { RequireAuth, RequireRole } from './components/RequireAuth';
import { AppLayout } from './layouts/AppLayout';

const LoginPage = lazy(() => import('./features/auth/LoginPage'));
const DashboardPage = lazy(() => import('./features/dashboard/DashboardPage'));
const MyAttendancePage = lazy(() => import('./features/attendance/AttendancePage'));
const MyLeavesPage = lazy(() => import('./features/leaves/MyLeavesPage'));
const ApplyLeavePage = lazy(() => import('./features/leaves/ApplyLeavePage'));
const LeaveApprovalsPage = lazy(() => import('./features/leaves/LeaveApprovalsPage'));
const EmployeeDirectoryPage = lazy(() => import('./features/employees/EmployeeDirectoryPage'));
const EmployeeProfilePage = lazy(() => import('./features/employees/EmployeeProfilePage'));
const OrgChartPage = lazy(() => import('./features/employees/OrgChartPage'));
const DepartmentsPage = lazy(() => import('./features/employees/DepartmentsPage'));
const ProjectsPage = lazy(() => import('./features/projects/ProjectsPage'));
const ProjectDetailPage = lazy(() => import('./features/projects/ProjectDetailPage'));
const ClientsPage = lazy(() => import('./features/clients/ClientsPage'));
const ClientProfilePage = lazy(() => import('./features/clients/ClientProfilePage'));
const TaskBoardPage = lazy(() => import('./features/tasks/TaskBoardPage'));
const MyTimesheetsPage = lazy(() => import('./features/timesheets/MyTimesheetsPage'));
const TimesheetApprovalsPage = lazy(
  () => import('./features/timesheets/TimesheetApprovalsPage'),
);
const FinanceDashboardPage = lazy(() => import('./features/finance/FinanceDashboardPage'));
const InvoicesPage = lazy(() => import('./features/finance/InvoicesPage'));
const ExpensesPage = lazy(() => import('./features/finance/ExpensesPage'));
const MyExpensesPage = lazy(() => import('./features/finance/MyExpensesPage'));
const PayrollPage = lazy(() => import('./features/finance/PayrollPage'));
const NotFoundPage = lazy(() => import('./features/errors/NotFoundPage'));
const ReportsPage = lazy(() => import('./features/reports/ReportsPage'));
const NoticeBoardPage = lazy(() => import('./features/notices/NoticeBoardPage'));
const MeetingsPage = lazy(() => import('./features/meetings/MeetingsPage'));
const NotificationsPage = lazy(() => import('./features/notifications/NotificationsPage'));
const SiteVisitsPage = lazy(() => import('./features/siteVisits/SiteVisitsPage'));
const SettingsPage = lazy(() => import('./features/settings/SettingsPage'));

function PageLoader() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-paper" role="status" aria-label="Loading page">
      <div className="flex flex-col items-center gap-4">
        <svg viewBox="0 0 40 40" fill="none" className="h-16 w-16" aria-hidden="true">
          <rect x="2" y="24" width="6" height="14" rx="2" fill="currentColor" className="text-navy animate-loader-bar" style={{ animationDelay: '0ms' }} />
          <rect x="9.5" y="16" width="6" height="22" rx="2" fill="currentColor" className="text-navy animate-loader-bar" style={{ animationDelay: '100ms' }} />
          <rect x="17" y="20" width="6" height="18" rx="2" fill="currentColor" className="text-navy animate-loader-bar" style={{ animationDelay: '200ms' }} />
          <rect x="24.5" y="8" width="6" height="30" rx="2" fill="#C9964A" className="animate-loader-bar" style={{ animationDelay: '300ms' }} />
          <rect x="32" y="26" width="6" height="12" rx="2" fill="currentColor" className="text-navy animate-loader-bar" style={{ animationDelay: '400ms' }} />
        </svg>
        <p className="text-sm font-semibold tracking-wide text-muted animate-pulse">Loading...</p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
    <MobileBlockScreen />
    <div className="desktop-only">
    <Suspense fallback={<PageLoader />}>
      <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />

          <Route path="/attendance" element={<MyAttendancePage />} />

          <Route path="/leaves" element={<Navigate to="/leaves/my" replace />} />
          <Route path="/leaves/my" element={<MyLeavesPage />} />
          <Route path="/leaves/apply" element={<ApplyLeavePage />} />
          <Route element={<RequireRole minLevel="L3" />}>
            <Route path="/leaves/approvals" element={<LeaveApprovalsPage />} />
          </Route>

          <Route element={<RequireRole minLevel="L3" />}>
            <Route path="/employees" element={<EmployeeDirectoryPage />} />
            <Route path="/employees/org-chart" element={<OrgChartPage />} />
            <Route path="/employees/:id" element={<EmployeeProfilePage />} />
          </Route>
          <Route element={<RequireRole minLevel="L2" />}>
            <Route path="/departments" element={<DepartmentsPage />} />
          </Route>

          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:id" element={<ProjectDetailPage />} />

          <Route element={<RequireRole minLevel="L3" />}>
            <Route path="/clients" element={<ClientsPage />} />
            <Route path="/clients/:id" element={<ClientProfilePage />} />
          </Route>

          <Route path="/tasks" element={<TaskBoardPage />} />

          <Route path="/timesheets" element={<MyTimesheetsPage />} />
          <Route element={<RequireRole minLevel="L3" />}>
            <Route path="/timesheets/approvals" element={<TimesheetApprovalsPage />} />
          </Route>

          <Route path="/notices" element={<NoticeBoardPage />} />
          <Route path="/meetings" element={<MeetingsPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/site-visits" element={<SiteVisitsPage />} />

          <Route path="/finance" element={<Navigate to="/finance/overview" replace />} />
          <Route element={<RequireRole minLevel="L1" />}>
            <Route path="/finance/overview" element={<FinanceDashboardPage />} />
            <Route path="/finance/invoices" element={<InvoicesPage />} />
            <Route path="/finance/expenses" element={<ExpensesPage />} />
          </Route>
          <Route path="/finance/my-expenses" element={<MyExpensesPage />} />
          <Route element={<RequireRole minLevel="L1" />}>
            <Route path="/finance/payroll" element={<PayrollPage />} />
          </Route>

          {/* Reports: projects & finance reports carry financial data (L0/L1 only). */}
          <Route element={<RequireRole minLevel="L1" />}>
            <Route path="/reports" element={<ReportsPage />} />
          </Route>
          <Route element={<RequireRole minLevel="L2" />}>
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
    </div>
    </ErrorBoundary>
  );
}
