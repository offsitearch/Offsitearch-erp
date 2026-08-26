import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, KeyRound, Loader2 } from 'lucide-react';
import { changePassword } from '../../api/settings';
import { Button } from '../../components/ui/Button';
import { useAuthStore } from '../../store/authStore';
import { inputClass } from '../../lib/styles';

/**
 * Full-screen gate shown when the account carries a temporary password
 * (first login or an executive reset). The user cannot proceed until they
 * set their own password; the backend enforces the same rule.
 */
export function ForceChangePasswordPage() {
  const { t } = useTranslation();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const canSubmit =
    currentPassword.length > 0 &&
    newPassword.length >= 6 &&
    newPassword === confirmPassword &&
    newPassword !== currentPassword &&
    !pending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setPending(true);
    setError(null);
    try {
      const tokens = await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setAuth(tokens);
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? t('auth.changePasswordError'));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-4">
      <div className="w-full max-w-md rounded-lg border border-border bg-surface p-8 shadow-card">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-orange/10 text-orange">
            <KeyRound className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-ink">{t('auth.forceChangeTitle')}</h1>
            <p className="text-sm text-muted">{t('auth.forceChangeSubtitle')}</p>
          </div>
        </div>

        {error && (
          <div role="alert" className="mb-4 flex items-start gap-2 rounded-md bg-dangerSoft px-3 py-2 text-sm text-danger">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <label className="block text-sm font-medium text-ink">
            {t('auth.currentPassword')}
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
              className={`${inputClass} mt-1`}
            />
          </label>
          <label className="block text-sm font-medium text-ink">
            {t('auth.newPassword')}
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              minLength={6}
              className={`${inputClass} mt-1`}
            />
          </label>
          <label className="block text-sm font-medium text-ink">
            {t('auth.confirmNewPassword')}
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              minLength={6}
              className={`${inputClass} mt-1`}
            />
          </label>
          {newPassword.length > 0 && confirmPassword.length > 0 && newPassword !== confirmPassword && (
            <p className="text-xs font-medium text-danger">{t('auth.passwordsMismatch')}</p>
          )}
          <Button type="submit" size="lg" loading={pending} disabled={!canSubmit} className="w-full">
            {pending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {t('auth.saveNewPassword')}
          </Button>
        </form>
      </div>
    </div>
  );
}
