import { api } from './client';
import type {
  LeaveBalance,
  LeaveRecord,
  LeaveType,
  LeaveUserRow,
  TeamAvailabilityRow,
} from '../lib/types';

export interface ApplyLeaveInput {
  leave_type: LeaveType;
  from_date: string;
  to_date: string;
  half_day_first?: boolean;
  half_day_second?: boolean;
  reason?: string;
}

/** Fetches leave balances for the current user. */
export async function getLeaveBalances(year?: number): Promise<LeaveBalance[]> {
  const { data } = await api.get<LeaveBalance[]>('/leaves/balance', { params: { year } });
  return data;
}

/** Fetches all of the current user's leave records. */
export async function getMyLeaves(): Promise<LeaveRecord[]> {
  const { data } = await api.get<{ items: LeaveRecord[] }>('/leaves/mine');
  return data.items ?? [];
}

/** Submits a new leave application. */
export async function applyLeave(payload: ApplyLeaveInput): Promise<LeaveRecord> {
  const { data } = await api.post<LeaveRecord>('/leaves', payload);
  return data;
}

/** Cancels an existing leave request. */
export async function cancelLeave(id: number): Promise<LeaveRecord> {
  const { data } = await api.patch<LeaveRecord>(`/leaves/${id}`, { action: 'cancel' });
  return data;
}

/** Fetches all pending leave requests awaiting approval. */
export async function getPendingLeaves(): Promise<LeaveUserRow[]> {
  const { data } = await api.get<{ items: LeaveUserRow[] }>('/leaves/pending');
  return data.items ?? [];
}

/** Approves a pending leave request. */
export async function approveLeave(id: number): Promise<LeaveRecord> {
  const { data } = await api.post<LeaveRecord>(`/leaves/${id}/approve`);
  return data;
}

/** Rejects a pending leave request with a reason. */
export async function rejectLeave(id: number, reason: string): Promise<LeaveRecord> {
  const { data } = await api.post<LeaveRecord>(`/leaves/${id}/reject`, { reason });
  return data;
}

/** Fetches team availability for a given date range. */
export async function getTeamAvailability(
  fromDate: string,
  toDate: string,
): Promise<TeamAvailabilityRow[]> {
  const { data } = await api.get<TeamAvailabilityRow[]>('/leaves/team-availability', {
    params: { from_date: fromDate, to_date: toDate },
  });
  return data;
}
