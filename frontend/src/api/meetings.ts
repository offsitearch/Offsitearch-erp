import { api } from './client';
import type { Meeting, MeetingInput, RsvpStatus } from '../lib/types';

/** Fetches all meetings. */
export async function getMeetings(): Promise<Meeting[]> {
  const { data } = await api.get<{ items: Meeting[] }>('/meetings');
  return data.items ?? [];
}

/** Creates a new meeting. */
export async function createMeeting(payload: MeetingInput): Promise<Meeting> {
  const { data } = await api.post<Meeting>('/meetings', payload);
  return data;
}

/** Updates an existing meeting. */
export async function updateMeeting(id: number, payload: Partial<MeetingInput>): Promise<Meeting> {
  const { data } = await api.patch<Meeting>(`/meetings/${id}`, payload);
  return data;
}

/** Deletes a meeting by ID. */
export async function deleteMeeting(id: number): Promise<void> {
  await api.delete(`/meetings/${id}`);
}

/** Submits an RSVP response for a meeting. */
export async function rsvpMeeting(id: number, rsvp_status: RsvpStatus): Promise<Meeting> {
  const { data } = await api.post<Meeting>(`/meetings/${id}/rsvp`, null, {
    params: { rsvp_status },
  });
  return data;
}
