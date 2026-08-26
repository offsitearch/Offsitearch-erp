import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  AlertCircle,
  ArrowRight,
  CalendarCheck,
  Eye,
  EyeOff,
  FileText,
  FolderKanban,
  Hash,
  Lock,
} from 'lucide-react';
import { useLogin } from '../../hooks/useAuth';
import { useAuthStore } from '../../store/authStore';
import { LoginFormError } from '../../components/LoginFormError';
import { BrandLogo, OffsiteMark } from '../../components/BrandLogo';
import { Button } from '../../components/ui/Button';

const REMEMBER_USERID_KEY = 'offsite-remember-userid';
const USERID_RE = /^\d{6}$/;

const inputClass =
  'h-10 w-full rounded-md border border-lavender bg-surface pl-10 text-sm text-ink placeholder:text-muted outline-none transition focus:ring-2 focus:ring-azure/20 dark:border-border';

export default function LoginPage() {
  const { t } = useTranslation();
  const [userId, setUserId] = useState(() => localStorage.getItem(REMEMBER_USERID_KEY) ?? '');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(() => Boolean(localStorage.getItem(REMEMBER_USERID_KEY)));
  const [showPassword, setShowPassword] = useState(false);
  const [userIdError, setUserIdError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const accessToken = useAuthStore((s) => s.accessToken);
  const login = useLogin();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? '/dashboard';

  if (accessToken) {
    return <Navigate to={from} replace />;
  }

  function validate(): boolean {
    const value = userId.trim();
    let valid = true;

    if (!value) {
      setUserIdError(t('auth.userIdRequired'));
      valid = false;
    } else if (!USERID_RE.test(value)) {
      setUserIdError(t('auth.userIdInvalid'));
      valid = false;
    } else {
      setUserIdError(null);
    }

    if (!password) {
      setPasswordError(t('auth.passwordRequired'));
      valid = false;
    } else {
      setPasswordError(null);
    }

    return valid;
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    if (!validate()) return;

    if (remember) {
      localStorage.setItem(REMEMBER_USERID_KEY, userId.trim());
    } else {
      localStorage.removeItem(REMEMBER_USERID_KEY);
    }

    login.mutate(
      { userId: userId.trim(), password },
      {
        onSuccess: () => navigate(from, { replace: true }),
        onError: () => setFormError(t('auth.loginError')),
      },
    );
  }

  return (
    <div className="min-h-screen bg-haze dark:bg-paper lg:grid lg:grid-cols-2">
      <aside className="relative hidden overflow-hidden bg-royal lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div className="arch-grid-light pointer-events-none absolute inset-0" aria-hidden="true" />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-24 -right-24 h-96 w-96 rounded-full bg-periwinkle/20 blur-3xl"
        />
        <OffsiteMark
          accent="#C9964A"
          className="pointer-events-none absolute -bottom-12 -right-12 h-64 w-64 text-sky/[0.08]"
          aria-hidden="true"
        />

        <div className="relative z-10">
          <BrandLogo tone="light" accent="#C9964A" />
        </div>

        <div className="relative z-10 max-w-md">
          <div className="mb-6 h-px w-12 bg-sky" aria-hidden="true" />
          <h1 className="text-display font-semibold tracking-tight text-white">
            {t('auth.sidebarTagline')}
          </h1>
          <p className="mt-4 text-sm leading-6 text-white/70">
            {t('auth.sidebarDescription')}
          </p>

          <ul className="mt-8 space-y-2.5">
            {[
              { icon: FolderKanban, label: t('auth.featureProjects') },
              { icon: CalendarCheck, label: t('auth.featureAttendance') },
              { icon: FileText, label: t('auth.featureDocuments') },
            ].map((item) => (
              <li
                key={item.label}
                className="flex items-center gap-3 rounded-md border border-white/10 bg-white/5 px-3.5 py-2.5"
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white/10 text-sky">
                  <item.icon className="h-4 w-4" />
                </span>
                <span className="text-sm text-white/80">{item.label}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="relative z-10 flex items-center gap-3 text-xs text-white/50">
          <OffsiteMark className="h-4 w-4" />
          {t('auth.internalWorkspace')}
        </div>
      </aside>

      <main className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-12 sm:px-6 lg:px-12">
        <div className="arch-grid-paper pointer-events-none absolute inset-0" aria-hidden="true" />
        <div className="relative z-10 w-full max-w-md">
          <div className="mb-10 lg:hidden">
            <BrandLogo />
          </div>

          <div className="rounded-lg border border-lavender bg-surface p-8 shadow-card dark:border-border">
            <span className="mb-5 flex items-center gap-3" aria-hidden="true">
              <OffsiteMark accent="#C9964A" className="h-5 w-5 text-royal dark:text-white" />
              <span className="h-px w-10 bg-azure" />
            </span>

            <h2 className="text-2xl font-bold leading-9 tracking-tight text-royal dark:text-ink">
              {t('auth.loginTitle')}
            </h2>
            <p className="mt-1 text-sm text-muted">{t('auth.loginSubtitle')}</p>

            {formError && (
              <div className="mt-5">
                <LoginFormError message={formError} />
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate className="mt-6 space-y-5">
              <div>
                <label htmlFor="userId" className="mb-1.5 block text-sm font-medium text-royal dark:text-ink">
                  {t('auth.userId')}
                </label>
                <div className="relative">
                  <Hash className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
                  <input
                    id="userId"
                    name="userId"
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    autoComplete="username"
                    value={userId}
                    onChange={(e) => {
                      setUserId(e.target.value.replace(/\D/g, ''));
                      if (userIdError) setUserIdError(null);
                      if (formError) setFormError(null);
                    }}
                    placeholder={t('auth.enterUserId')}
                    aria-invalid={Boolean(userIdError)}
                    aria-describedby={userIdError ? 'userid-error' : undefined}
                    className={`${inputClass} ${userIdError ? 'border-danger/60 focus:border-danger/60' : 'focus:border-azure'}`}
                  />
                </div>
                {userIdError && (
                  <p id="userid-error" role="alert" className="mt-1.5 flex items-center gap-1.5 text-xs font-medium text-danger">
                    <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                    {userIdError}
                  </p>
                )}
              </div>

              <div>
                <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-royal dark:text-ink">
                  {t('auth.password')}
                </label>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (passwordError) setPasswordError(null);
                      if (formError) setFormError(null);
                    }}
                    placeholder={t('auth.enterPassword')}
                    aria-invalid={Boolean(passwordError)}
                    aria-describedby={passwordError ? 'password-error' : undefined}
                    className={`${inputClass} pr-10 ${passwordError ? 'border-danger/60 focus:border-danger/60' : 'focus:border-azure'}`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? t('auth.hidePassword') : t('auth.showPassword')}
                    className="absolute right-2 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded text-muted transition hover:text-ink"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {passwordError && (
                  <p id="password-error" role="alert" className="mt-1.5 flex items-center gap-1.5 text-xs font-medium text-danger">
                    <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                    {passwordError}
                  </p>
                )}
              </div>

              <div className="flex items-center justify-between">
                <label className="flex cursor-pointer select-none items-center gap-2 text-sm text-graphite">
                  <input
                    type="checkbox"
                    checked={remember}
                    onChange={(e) => setRemember(e.target.checked)}
                    className="h-4 w-4 rounded border-lavender accent-azure dark:border-border"
                  />
                  {t('auth.rememberMe')}
                </label>
              </div>

              <Button
                type="submit"
                variant="primary"
                size="lg"
                loading={login.isPending}
                rightIcon={<ArrowRight className="h-4 w-4" />}
                className="w-full"
              >
                {login.isPending ? t('auth.signingIn') : t('auth.signIn')}
              </Button>
            </form>
          </div>

          <p className="mt-6 text-center text-xs text-muted">
            {t('auth.accessManaged')}
          </p>
        </div>
      </main>
    </div>
  );
}
