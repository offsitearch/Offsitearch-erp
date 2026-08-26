import { api } from './client';
import type { Notice, NoticeInput } from '../lib/types';

/** Fetches all notices, optionally including inactive ones. */
export async function getNotices(params: { include_inactive?: boolean } = {}): Promise<Notice[]> {
  const { data } = await api.get<{ items: Notice[] }>('/notices', { params });
  return data.items ?? [];
}

/** Creates a new notice. */
export async function createNotice(payload: NoticeInput): Promise<Notice> {
  const { data } = await api.post<Notice>('/notices', payload);
  return data;
}

/** Updates an existing notice. */
export async function updateNotice(id: number, payload: Partial<NoticeInput>): Promise<Notice> {
  const { data } = await api.patch<Notice>(`/notices/${id}`, payload);
  return data;
}

/** Deletes a notice by ID. */
export async function deleteNotice(id: number): Promise<void> {
  await api.delete(`/notices/${id}`);
}
