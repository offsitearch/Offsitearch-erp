import { api } from './client';
import type { BackupHistoryEntry, BackupStatus } from '../lib/types';

/** Connection + schedule state for the Google Drive backup. */
export async function getBackupStatus(): Promise<BackupStatus> {
  const { data } = await api.get<BackupStatus>('/backup/status');
  return data;
}

/** Recent backup attempts (newest first). */
export async function getBackupHistory(limit = 20): Promise<BackupHistoryEntry[]> {
  const { data } = await api.get<BackupHistoryEntry[]>('/backup/history', { params: { limit } });
  return data ?? [];
}

/** Runs a backup immediately and uploads it to Google Drive. */
export async function runBackupNow(): Promise<BackupHistoryEntry> {
  const { data } = await api.post<BackupHistoryEntry>('/backup/run');
  return data;
}

/** Toggles the scheduled (auto) backup. */
export async function updateBackupSchedule(autoEnabled: boolean, frequency: string): Promise<BackupStatus> {
  const { data } = await api.put<BackupStatus>('/backup/schedule', {
    auto_enabled: autoEnabled,
    frequency,
  });
  return data;
}

/** Removes the stored Google tokens. */
export async function disconnectGoogleDrive(): Promise<void> {
  await api.post('/backup/google/disconnect');
}

/**
 * One-click Google setup: navigate the browser to this URL — it bounces
 * through Google's consent screen and lands back on /settings?tab=backup.
 * A plain link (no auth header) because the endpoint itself just redirects.
 */
export function googleConnectUrl(): string {
  return `${api.defaults.baseURL}/backup/google/connect`;
}

/** Downloads a fresh database dump as a .json.gz file, no Drive required. */
export async function downloadBackupFile(): Promise<void> {
  const response = await api.get('/backup/download', { responseType: 'blob' });
  const blob = response.data as Blob;
  // Prefer the server's timestamped name from Content-Disposition.
  const disposition = (response.headers?.['content-disposition'] as string | undefined) ?? '';
  const match = /filename="([^"]+)"/.exec(disposition);
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = match?.[1] ?? `studioerp-backup-${new Date().toISOString().slice(0, 10)}.json.gz`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
