import { api } from './client';
import type {
  AttendanceRecord,
  AttendanceUserRow,
  Holiday,
  MonthlySummary,
  ReportRow,
  UserBrief,
} from '../lib/types';

export interface CheckInInput {
  method: 'web' | 'manual' | 'qr' | 'gps' | 'ip';
  location?: string;
  notes?: string;
}

export interface BulkEntry {
  user_id: number;
  status: string;
  check_in_time?: string | null;
  check_out_time?: string | null;
  notes?: string;
}

/** Records the current user's check-in. */
export async function checkIn(payload: CheckInInput): Promise<AttendanceRecord> {
  const { data } = await api.post<AttendanceRecord>('/attendance/check-in', payload);
  return data;
}

/** Records the current user's check-out. */
export async function checkOut(): Promise<AttendanceRecord> {
  const { data } = await api.post<AttendanceRecord>('/attendance/check-out', {});
  return data;
}

/** Fetches the current user's monthly attendance summary. */
export async function getMyAttendance(
  month?: number,
  year?: number,
): Promise<MonthlySummary> {
  const { data } = await api.get<MonthlySummary>('/attendance/me', {
    params: { month, year },
  });
  return data;
}

/** Fetches all attendance records for a specific date. */
export async function getDateAttendance(
  date: string,
  departmentId?: number | null,
  status?: string | null,
): Promise<AttendanceUserRow[]> {
  const { data } = await api.get<AttendanceUserRow[]>(`/attendance/date/${date}`, {
    params: { department_id: departmentId ?? undefined, status: status ?? undefined },
  });
  return data;
}

/** Fetches the list of company holidays for a year. */
export async function getHolidays(year?: number): Promise<Holiday[]> {
  const { data } = await api.get<Holiday[]>('/attendance/holidays', {
    params: { year },
  });
  return data;
}

/** Bulk-sets attendance entries for a given date. */
export async function bulkMark(date: string, entries: BulkEntry[]): Promise<void> {
  await api.post('/attendance/bulk', { date, entries });
}

/** Updates an individual attendance record. */
export async function updateAttendance(
  id: number,
  patch: {
    status?: string;
    check_in_time?: string | null;
    check_out_time?: string | null;
    notes?: string | null;
  },
): Promise<AttendanceRecord> {
  const { data } = await api.patch<AttendanceRecord>(`/attendance/${id}`, patch);
  return data;
}

/** Fetches attendance report rows for a date range. */
export async function getReportRows(
  fromDate: string,
  toDate: string,
  departmentId?: number | null,
): Promise<ReportRow[]> {
  const { data } = await api.get<{ from_date: string; to_date: string; rows: ReportRow[] }>(
    '/attendance/report',
    { params: { from_date: fromDate, to_date: toDate, department_id: departmentId ?? undefined } },
  );
  return data.rows;
}

/** Downloads the attendance report as an XLSX file. */
export async function downloadReportXlsx(
  fromDate: string,
  toDate: string,
  departmentId?: number | null,
): Promise<void> {
  const response = await api.get('/attendance/report', {
    params: { from_date: fromDate, to_date: toDate, department_id: departmentId ?? undefined, format: 'xlsx' },
    responseType: 'blob',
  });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = `attendance_${fromDate}_${toDate}.xlsx`;
  link.click();
  URL.revokeObjectURL(url);
}

/** Fetches a brief list of users, optionally filtered by department. */
export async function listUsers(departmentId?: number | null): Promise<UserBrief[]> {
  const { data } = await api.get<UserBrief[]>('/users', {
    params: { department_id: departmentId ?? undefined },
  });
  return data;
}
