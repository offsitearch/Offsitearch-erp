import { api } from './client';
import type {
  TimesheetDetail,
  TimesheetPage,
  TimesheetWeekSaveInput,
} from '../lib/types';

/** Fetches the caller's timesheet for the week containing the given date (ISO). */
export async function getMyWeek(date?: string): Promise<TimesheetDetail> {
  const { data } = await api.get<TimesheetDetail>('/timesheets/week', {
    params: date ? { date } : {},
  });
  return data;
}

/** Replaces every entry of the caller's week sheet (draft/rejected only). */
export async function saveMyWeek(payload: TimesheetWeekSaveInput): Promise<TimesheetDetail> {
  const { data } = await api.put<TimesheetDetail>('/timesheets/week', payload);
  return data;
}

/** Fetches the caller's timesheet history (newest weeks first). */
export async function getMyTimesheets(page = 1, pageSize = 20): Promise<TimesheetPage> {
  const { data } = await api.get<TimesheetPage>('/timesheets/mine', {
    params: { page, page_size: pageSize },
  });
  return data;
}

/** Fetches a single timesheet's full detail (owner or lead+). */
export async function getTimesheet(id: number): Promise<TimesheetDetail> {
  const { data } = await api.get<TimesheetDetail>(`/timesheets/${id}`);
  return data;
}

export interface TimesheetListFilters {
  user_id?: number;
  status?: string;
  from_week?: string;
  to_week?: string;
  page?: number;
  page_size?: number;
}

/** Lists all timesheets with filters (L2+). */
export async function getAllTimesheets(
  filters: TimesheetListFilters = {},
): Promise<TimesheetPage> {
  const { data } = await api.get<TimesheetPage>('/timesheets', { params: filters });
  return data;
}

/** Lists submitted timesheets awaiting review (L3+). */
export async function getPendingTimesheets(): Promise<TimesheetPage> {
  const { data } = await api.get<TimesheetPage>('/timesheets/pending');
  return data;
}

/** Submits the week sheet for approval. */
export async function submitTimesheet(id: number): Promise<TimesheetDetail> {
  const { data } = await api.post<TimesheetDetail>(`/timesheets/${id}/submit`);
  return data;
}

/** Approves a submitted timesheet (lead+). */
export async function approveTimesheet(id: number): Promise<TimesheetDetail> {
  const { data } = await api.post<TimesheetDetail>(`/timesheets/${id}/approve`);
  return data;
}

/** Rejects a submitted timesheet with a required reason (lead+). */
export async function rejectTimesheet(id: number, reason: string): Promise<TimesheetDetail> {
  const { data } = await api.post<TimesheetDetail>(`/timesheets/${id}/reject`, { reason });
  return data;
}

/** Downloads a timesheet week sheet as a PDF receipt. */
export async function downloadTimesheetPdf(id: number): Promise<void> {
  const response = await api.get(`/timesheets/${id}/pdf`, { responseType: 'blob' });
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `timesheet-${id}.pdf`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

/** Submits a single day of the caller's week for approval. */
export async function submitTimesheetDay(id: number, day: string): Promise<TimesheetDetail> {
  const { data } = await api.post<TimesheetDetail>(`/timesheets/${id}/days/${day}/submit`);
  return data;
}

/** Approves a single submitted day (lead+). */
export async function approveTimesheetDay(id: number, day: string): Promise<TimesheetDetail> {
  const { data } = await api.post<TimesheetDetail>(`/timesheets/${id}/days/${day}/approve`);
  return data;
}

/** Rejects a single submitted day with a required reason (lead+). */
export async function rejectTimesheetDay(
  id: number,
  day: string,
  reason: string,
): Promise<TimesheetDetail> {
  const { data } = await api.post<TimesheetDetail>(`/timesheets/${id}/days/${day}/reject`, {
    reason,
  });
  return data;
}

/** Downloads a month export of timesheet entries (own data; other users need L2+). */
export async function downloadTimesheetMonthExport(
  year: number,
  month: number,
  format: 'xlsx' | 'pdf',
  userId?: number,
): Promise<void> {
  const response = await api.get('/timesheets/export/month', {
    responseType: 'blob',
    params: { year, month, format, ...(userId ? { user_id: userId } : {}) },
  });
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `timesheets-${year}-${String(month).padStart(2, '0')}.${format}`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
