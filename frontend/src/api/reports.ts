import { api } from './client';
import type {
  AttendanceReportRow,
  FinanceReportData,
  HrReportData,
  ProjectsReportData,
  TimesheetsReportData,
} from '../lib/types';

/** Fetches a projects report as JSON. */
export async function getProjectsReport(params: {
  status?: string;
  project_type?: string;
}): Promise<ProjectsReportData> {
  return fetchExport<ProjectsReportData>('/reports/projects', params);
}

/** Fetches a finance report as JSON. */
export async function getFinanceReport(params: {
  period?: 'month' | 'quarter' | 'year' | 'all';
}): Promise<FinanceReportData> {
  return fetchExport<FinanceReportData>('/reports/finance', params);
}

/** Fetches an HR report as JSON. */
export async function getHrReport(params: { month: number; year: number }): Promise<HrReportData> {
  return fetchExport<HrReportData>('/reports/hr', params);
}

/** Fetches a timesheets report as JSON (L2+). */
export async function getTimesheetsReport(
  params: {
    from_date: string;
    to_date: string;
    department_id?: number;
    employee_id?: number;
    group_by?: 'day' | 'week' | 'month';
  },
): Promise<TimesheetsReportData> {
  return fetchExport<TimesheetsReportData>('/reports/timesheets', params);
}

/** Active employees for the timesheet report filters (L2+). */
export async function getTimesheetEmployeeOptions(
  departmentId?: number,
): Promise<Array<{ id: number; name: string; employee_id: string | null }>> {
  const { data } = await api.get('/reports/timesheets/options', {
    params: { department_id: departmentId },
  });
  return data;
}

export async function getAttendanceReport(
  from_date: string,
  to_date: string,
  format: 'csv' | 'xlsx',
  department_id?: number,
): Promise<Blob>;

export async function getAttendanceReport(
  from_date: string,
  to_date: string,
  format: 'json',
  department_id?: number,
): Promise<AttendanceReportRow[]>;

/** Fetches an attendance report as JSON or a downloadable blob. */
export async function getAttendanceReport(
  from_date: string,
  to_date: string,
  format: 'json' | 'csv' | 'xlsx',
  department_id?: number,
): Promise<AttendanceReportRow[] | Blob> {
  if (format === 'json') {
    const { data } = await api.get<{ from_date: string; to_date: string; rows: AttendanceReportRow[] }>(
      '/attendance/report',
      { params: { from_date, to_date, format, department_id } },
    );
    return data.rows ?? [];
  }
  return fetchExport('/attendance/report', { from_date, to_date, format, department_id }) as Promise<Blob>;
}

async function fetchExport<T = Blob>(
  path: string,
  params: Record<string, string | number | undefined>,
): Promise<T> {
  const { data } = await api.get<T>(path, { params });
  return data;
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/** Downloads a report file and triggers a browser download. */
export async function downloadReportFile(
  path: '/reports/projects' | '/reports/finance' | '/reports/hr' | '/reports/timesheets',
  params: Record<string, string | number | undefined>,
  filename: string,
): Promise<void> {
  const { data } = await api.get(path, { params, responseType: 'blob' });
  downloadBlob(data as Blob, filename);
}

/** Downloads an attendance report as a file. */
export async function downloadAttendanceFile(
  from_date: string,
  to_date: string,
  format: 'csv' | 'xlsx',
  department_id?: number,
): Promise<void> {
  const { data } = await api.get('/attendance/report', {
    params: { from_date, to_date, format, department_id },
    responseType: 'blob',
  });
  downloadBlob(data as Blob, `attendance_report.${format}`);
}
