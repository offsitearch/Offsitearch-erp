import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircle2,
  CloudUpload,
  HardDriveDownload,
  Link2,
  Loader2,
  RefreshCw,
  ShieldCheck,
  Unlink,
  XCircle,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import {
  disconnectGoogleDrive,
  downloadBackupFile,
  getBackupHistory,
  getBackupStatus,
  googleConnectUrl,
  runBackupNow,
  updateBackupSchedule,
} from '../../api/backup';
import { LogoLoader } from '../../components/LogoLoader';
import { useToast } from '../../components/Toast';
import { formatDateTime } from '../../lib/date';
import { primaryBtnClass, secondaryBtnClass, smallInputClass } from '../../lib/styles';

function formatSize(bytes: number | null): string {
  if (bytes == null) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function BackupTab() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const status = useQuery({ queryKey: ['backup-status'], queryFn: getBackupStatus });
  const history = useQuery({ queryKey: ['backup-history'], queryFn: () => getBackupHistory() });

  const [autoEnabled, setAutoEnabled] = useState(false);
  const [frequency, setFrequency] = useState('daily');
  const [scheduleDirty, setScheduleDirty] = useState(false);

  // Surface the OAuth round-trip result (Google bounces back with
  // ?drive=connected|error|not_configured) once, then strip the param.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const drive = params.get('drive');
    if (!drive) return;
    if (drive === 'connected') toast('Google Drive connected', 'success');
    else if (drive === 'not_configured') toast('Backend Google credentials are not set up yet', 'error');
    else toast('Google Drive connection failed — try again', 'error');
    params.delete('drive');
    const rest = params.toString();
    window.history.replaceState(
      null,
      '',
      `${window.location.pathname}?${rest}${window.location.hash}`,
    );
    queryClient.invalidateQueries({ queryKey: ['backup-status'] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync local schedule form once the status arrives.
  useEffect(() => {
    if (!status.data || scheduleDirty) return;
    setAutoEnabled(status.data.auto_enabled);
    setFrequency(status.data.frequency);
  }, [status.data, scheduleDirty]);

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ['backup-status'] });
    queryClient.invalidateQueries({ queryKey: ['backup-history'] });
  };

  const runNow = useMutation({
    mutationFn: runBackupNow,
    onSuccess: (entry) => {
      toast(`Backup uploaded (${formatSize(entry.file_size_bytes)})`, 'success');
      refreshAll();
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast(err.response?.data?.detail ?? 'Backup failed', 'error');
      refreshAll();
    },
  });

  const download = useMutation({
    mutationFn: downloadBackupFile,
    onSuccess: () => toast('Backup file downloaded', 'success'),
    onError: () => toast('Failed to generate backup file', 'error'),
  });

  const saveSchedule = useMutation({
    mutationFn: () => updateBackupSchedule(autoEnabled, frequency),
    onSuccess: (data) => {
      queryClient.setQueryData(['backup-status'], data);
      setScheduleDirty(false);
      toast(data.auto_enabled ? `Automatic backup enabled (${frequency})` : 'Automatic backup disabled', 'success');
    },
    onError: () => toast('Failed to save backup schedule', 'error'),
  });

  const disconnect = useMutation({
    mutationFn: disconnectGoogleDrive,
    onSuccess: () => {
      toast('Google Drive disconnected', 'success');
      refreshAll();
    },
    onError: () => toast('Failed to disconnect Google Drive', 'error'),
  });

  if (status.isPending) {
    return <LogoLoader />;
  }

  const s = status.data;

  return (
    <div className="space-y-4">
      {/* ── Connection card ─────────────────────────────────── */}
      <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy/10 text-navy">
              {s?.connected ? <ShieldCheck className="h-5 w-5 text-success" /> : <Link2 className="h-5 w-5" />}
            </div>
            <div>
              <h2 className="text-base font-bold text-ink">Google Drive backup</h2>
              {s?.connected ? (
                <p className="mt-0.5 flex items-center gap-1.5 text-sm text-muted">
                  <CheckCircle2 className="h-4 w-4 text-success" />
                  Connected to <span className="font-medium text-ink">{s.account_email}</span>
                  {s.last_backup_at && (
                    <span className="text-muted">· last backup {formatDateTime(s.last_backup_at)}</span>
                  )}
                </p>
              ) : (
                <p className="mt-0.5 text-sm text-muted">
                  One click to connect — your backups upload to a private “StudioERP Backups” folder in
                  your Drive. Only this app’s own files are accessible.
                </p>
              )}
            </div>
          </div>
          {s?.connected ? (
            <button onClick={() => disconnect.mutate()} disabled={disconnect.isPending} className={secondaryBtnClass}>
              {disconnect.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Unlink className="h-4 w-4" />}
              Disconnect
            </button>
          ) : (
            <a href={googleConnectUrl()} className={primaryBtnClass}>
              <CloudUpload className="h-4 w-4" />
              Connect Google Drive
            </a>
          )}
        </div>

        {!s?.configured && (
          <div className="mt-4 rounded-lg border border-warning/30 bg-warningSoft px-4 py-3 text-sm text-graphite">
            <p className="font-medium text-warning">One-time admin setup required</p>
            <p className="mt-1">
              Ask whoever hosts the backend to set these environment variables once (Google Cloud Console →
              Credentials → OAuth client), then this button works with a single click forever:
            </p>
            <ul className="mt-2 space-y-1 font-mono text-xs">
              <li>GOOGLE_CLIENT_ID=…apps.googleusercontent.com</li>
              <li>GOOGLE_CLIENT_SECRET=…</li>
              <li>GOOGLE_REDIRECT_URI=&lt;backend-url&gt;/api/v1/backup/google/callback</li>
            </ul>
            <p className="mt-2">
              Until then you can still download manual backup files below — they work without any setup.
            </p>
          </div>
        )}

        {/* ── Actions ─────────────────────────────────────────── */}
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-border pt-4">
          <button onClick={() => runNow.mutate()} disabled={runNow.isPending || !s?.connected} className={primaryBtnClass}>
            {runNow.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <CloudUpload className="h-4 w-4" />}
            Back up now
          </button>
          <button onClick={() => download.mutate()} disabled={download.isPending} className={secondaryBtnClass}>
            {download.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <HardDriveDownload className="h-4 w-4" />
            )}
            Download backup file (.json.gz)
          </button>
        </div>

        {/* ── Schedule ────────────────────────────────────────── */}
        <div className="mt-4 border-t border-border pt-4">
          <div className="flex flex-wrap items-end gap-x-6 gap-y-3">
            <label className="flex items-center gap-2 pb-2 text-sm font-medium text-ink">
              <input
                type="checkbox"
                checked={autoEnabled}
                onChange={(e) => {
                  setAutoEnabled(e.target.checked);
                  setScheduleDirty(true);
                }}
                disabled={!s?.connected}
                className="rounded border-border"
              />
              Automatic backups
            </label>
            <label className="flex flex-col gap-1 text-sm text-muted">
              <span>Frequency</span>
              <select
                value={frequency}
                onChange={(e) => {
                  setFrequency(e.target.value);
                  setScheduleDirty(true);
                }}
                disabled={!s?.connected}
                className={`${smallInputClass} w-auto pr-8`}
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
              </select>
            </label>
            {scheduleDirty && (
              <button onClick={() => saveSchedule.mutate()} disabled={saveSchedule.isPending} className={primaryBtnClass}>
                {saveSchedule.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                Save schedule
              </button>
            )}
          </div>
          {!s?.connected && (
            <p className="mt-2 text-xs text-muted">
              Connect Google Drive above to enable automatic backups.
            </p>
          )}
        </div>
      </div>

      {/* ── History ───────────────────────────────────────────── */}
      <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
        <p className="border-b border-border bg-surfaceWarm px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted">
          Backup history
        </p>
        {(history.data ?? []).length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-muted">
            No backups yet — connect Drive or download a file above to create the first one.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-xs uppercase tracking-wide text-muted">
                  <th className="px-4 py-3 font-semibold">When</th>
                  <th className="px-4 py-3 font-semibold">Trigger</th>
                  <th className="px-4 py-3 font-semibold">Destination</th>
                  <th className="px-4 py-3 font-semibold">File</th>
                  <th className="px-4 py-3 text-right font-semibold">Size</th>
                  <th className="px-4 py-3 font-semibold">Result</th>
                </tr>
              </thead>
              <tbody>
                {(history.data ?? []).map((entry) => (
                  <tr key={entry.id} className="border-b border-border last:border-0 hover:bg-surfaceWarm">
                    <td className="whitespace-nowrap px-4 py-2.5 text-ink">{formatDateTime(entry.created_at)}</td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          entry.trigger === 'auto' ? 'bg-navy/10 text-navy' : 'bg-graphite/10 text-graphite'
                        }`}
                      >
                        {entry.trigger === 'auto' ? 'Automatic' : 'Manual'}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-graphite">
                      {entry.destination === 'google_drive' ? 'Google Drive' : 'Local file'}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-graphite">{entry.file_name ?? '—'}</td>
                    <td className="whitespace-nowrap px-4 py-2.5 text-right tabular-nums text-ink">
                      {formatSize(entry.file_size_bytes)}
                    </td>
                    <td className="px-4 py-2.5">
                      {entry.status === 'success' ? (
                        <span className="inline-flex items-center gap-1 text-success">
                          <CheckCircle2 className="h-4 w-4" /> Success
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-danger" title={entry.error_message ?? ''}>
                          <XCircle className="h-4 w-4" /> Failed
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
