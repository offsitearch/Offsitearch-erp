import { api } from './client';
import type { Notification } from '../lib/types';

/** Fetches all notifications for the current user. */
export async function getNotifications(): Promise<Notification[]> {
  const { data } = await api.get<{ items: Notification[] }>('/notifications');
  return data.items ?? [];
}

/** Fetches the count of unread notifications. */
export async function getUnreadCount(): Promise<number> {
  const { data } = await api.get<{ count: number }>('/notifications/unread-count');
  return data.count;
}

/** Marks a single notification as read. */
export async function markNotificationRead(id: number): Promise<void> {
  await api.patch(`/notifications/${id}/read`);
}

/** Marks all notifications as read. */
export async function markAllNotificationsRead(): Promise<void> {
  await api.post('/notifications/read-all');
}

/** Deletes a single notification. */
export async function deleteNotification(id: number): Promise<void> {
  await api.delete(`/notifications/${id}`);
}
