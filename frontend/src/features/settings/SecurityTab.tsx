import { useMutation } from '@tanstack/react-query';
import { Loader2, Lock, Save } from 'lucide-react';
import { useState } from 'react';
import { changePassword } from '../../api/settings';
import { useToast } from '../../components/Toast';
import { useAuthStore } from '../../store/authStore';
import { inputClass, primaryBtnClass } from '../../lib/styles';

export function SecurityTab() {
  const { toast } = useToast();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const mutation = useMutation({
    mutationFn: () =>
      changePassword({ current_password: currentPassword, new_password: newPassword }),
    onSuccess: (tokens) => {
      // Password events invalidate old sessions; adopt the fresh token pair.
      setAuth(tokens);
      toast('Password changed successfully', 'success');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    },
    onError: (err) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast(detail ?? 'Failed to change password', 'error');
    },
  });

  const isValid =
    currentPassword.length > 0 &&
    newPassword.length >= 6 &&
    newPassword === confirmPassword &&
    newPassword !== currentPassword;

  return (
    <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy/10 text-navy">
          <Lock className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-base font-bold text-ink">Change Password</h2>
          <p className="text-sm text-muted">Update your account password.</p>
        </div>
      </div>
      <div className="mt-5 space-y-4">
        <label className="mb-1 block text-xs font-medium text-muted">
          Current password
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className={`${inputClass} mt-1`}
            autoComplete="current-password"
          />
        </label>
        <label className="mb-1 block text-xs font-medium text-muted">
          New password (min 6 characters)
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            minLength={6}
            className={`${inputClass} mt-1`}
            autoComplete="new-password"
          />
        </label>
        <label className="mb-1 block text-xs font-medium text-muted">
          Confirm new password
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            minLength={6}
            className={`${inputClass} mt-1`}
            autoComplete="new-password"
          />
        </label>
        {newPassword.length > 0 && newPassword !== confirmPassword && (
          <p className="text-xs font-medium text-danger">Passwords do not match</p>
        )}
        {newPassword.length > 0 && newPassword === currentPassword && (
          <p className="text-xs font-medium text-warning">New password must differ from current</p>
        )}
      </div>
      <div className="mt-5 flex justify-end border-t border-border pt-4">
        <button
          onClick={() => mutation.mutate()}
          disabled={!isValid || mutation.isPending}
          className={primaryBtnClass}
        >
          {mutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          Change password
        </button>
      </div>
    </div>
  );
}
