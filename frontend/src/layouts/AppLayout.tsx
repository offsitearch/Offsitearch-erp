import { useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  BarChart3,
  CalendarCheck,
  CalendarClock,
  CalendarDays,
  CheckSquare,
  Bell,
  ChevronDown,
  FolderKanban,
  HardHat,
  LayoutDashboard,
  LogOut,
  Megaphone,
  Menu,
  Moon,
  Palmtree,
  Settings,
  Sun,
  UserRound,
  Users,
  Wallet,
} from 'lucide-react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BrandLogo } from '../components/BrandLogo';
import { NotificationBadge } from '../components/ui/NotificationBadge';
import { ForceChangePasswordPage } from '../features/auth/ForceChangePasswordPage';
import type { User } from '../lib/types';
import { canAccess, levelLabel } from '../lib/constants';
import { useAuthStore } from '../store/authStore';
import { encodeId } from '../lib/obfuscate';
import { useLogout } from '../hooks/useAuth';
import { useTheme } from '../hooks/useTheme';

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  minLevel: string;
  badge?: boolean;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const TOP_NAV: NavItem[] = [
  { to: '/dashboard', label: 'nav.dashboard', icon: LayoutDashboard, minLevel: 'L6' },
  { to: '/notifications', label: 'nav.notifications', icon: Bell, minLevel: 'L6', badge: true },
];

const NAV_GROUPS: NavGroup[] = [
  {
    label: 'nav.studio',
    items: [
      { to: '/projects', label: 'nav.projects', icon: FolderKanban, minLevel: 'L6' },
      { to: '/tasks', label: 'nav.tasks', icon: CheckSquare, minLevel: 'L6' },
      { to: '/timesheets', label: 'nav.timesheets', icon: CalendarClock, minLevel: 'L6' },
      { to: '/clients', label: 'nav.clients', icon: UserRound, minLevel: 'L3' },
    ],
  },
  {
    label: 'nav.people',
    items: [
      { to: '/employees', label: 'nav.employees', icon: Users, minLevel: 'L3' },
      { to: '/attendance', label: 'nav.attendance', icon: CalendarCheck, minLevel: 'L6' },
      { to: '/leaves', label: 'nav.leaves', icon: Palmtree, minLevel: 'L6' },
    ],
  },
  {
    label: 'nav.studioLife',
    items: [
      { to: '/notices', label: 'nav.notices', icon: Megaphone, minLevel: 'L6' },
      { to: '/meetings', label: 'nav.meetings', icon: CalendarDays, minLevel: 'L6' },
      { to: '/site-visits', label: 'nav.siteVisits', icon: HardHat, minLevel: 'L6' },
    ],
  },
  {
    label: 'nav.administration',
    items: [
      // Finance & reports expose financial data: executive-only (L0/L1).
      { to: '/finance', label: 'nav.finance', icon: Wallet, minLevel: 'L1' },
      { to: '/reports', label: 'nav.reports', icon: BarChart3, minLevel: 'L1' },
      { to: '/settings', label: 'nav.settings', icon: Settings, minLevel: 'L2' },
    ],
  },
];

function initials(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

function ThemeToggle({ className = '' }: { className?: string }) {
  const { theme, setTheme } = useTheme();

  function cycle() {
    if (theme === 'light') setTheme('dark');
    else if (theme === 'dark') setTheme('system');
    else setTheme('light');
  }

  const label =
    theme === 'light' ? 'Switch to dark mode' : theme === 'dark' ? 'Switch to system theme' : 'Switch to light mode';

  return (
    <button
      onClick={cycle}
      title={`${label} (current: ${theme})`}
      aria-label={label}
      className={`rounded-md p-2 text-muted transition hover:bg-surfaceWarm hover:text-ink ${className}`}
    >
      {theme === 'dark' ? (
        <Sun className="h-4 w-4" />
      ) : theme === 'light' ? (
        <Moon className="h-4 w-4" />
      ) : (
        <>
          <span className="dark:hidden"><Moon className="h-4 w-4" /></span>
          <span className="hidden dark:inline"><Sun className="h-4 w-4" /></span>
        </>
      )}
    </button>
  );
}

function SidebarContent({
  user,
  onNavigate,
  onLogout,
}: {
  user: User | null;
  onNavigate: () => void;
  onLogout: () => void;
}) {
  const { t } = useTranslation();
  const location = useLocation();
  const [profileOpen, setProfileOpen] = useState(false);
  const [hoveredGroup, setHoveredGroup] = useState<string | null>(null);
  const isAdmin = !!user && canAccess(user.org_level_code, 'L2');
  const isLead = !!user && canAccess(user.org_level_code, 'L3');
  const pathname = location.pathname;

  const activeInGroup = (group: NavGroup) =>
    group.items.some((item) => pathname === item.to || pathname.startsWith(`${item.to}/`));

  const itemClass = ({ isActive }: { isActive: boolean }) =>
    `group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition ${
      isActive
        ? 'bg-orange text-white shadow-card'
        : 'text-graphite hover:bg-orange/10 hover:text-ink'
    }`;

  const navItemChildren = (item: NavItem, isActive: boolean) => (
    <>
      <item.icon
        className={`h-4 w-4 shrink-0 transition-transform group-hover:translate-x-0.5 ${
          isActive ? 'text-white' : 'text-muted group-hover:text-orange'
        }`}
      />
      <span className="flex-1 truncate">{t(item.label)}</span>
      {item.badge && <NotificationBadge tone={isActive ? 'light' : 'orange'} />}
    </>
  );

  const closeMenu = () => {
    setProfileOpen(false);
    onNavigate();
  };

  return (
    <>
      <span
        className="pointer-events-none absolute inset-x-0 top-0 z-10 h-[3px] bg-gradient-to-r from-orange/90 via-orange to-orangeDark"
        aria-hidden="true"
      />
      <div className="arch-grid-paper pointer-events-none absolute inset-0" aria-hidden="true" />

      <div className="relative z-10 flex min-h-0 flex-1 flex-col">
        <div className="flex items-center justify-between px-4 pb-3 pt-4">
          <BrandLogo />
          <ThemeToggle />
        </div>
        <div className="mx-3 border-t border-border" />

        <nav className="scrollbar-none min-h-0 flex-1 overflow-y-auto px-3 pb-4">
          <div className="space-y-0.5 pt-2">
            {TOP_NAV.map((item) => (
              <NavLink key={item.to} to={item.to} className={itemClass} onClick={closeMenu}>
                {({ isActive }) => navItemChildren(item, isActive)}
              </NavLink>
            ))}
          </div>

          {NAV_GROUPS.map((group) => {
            const items = group.items.filter((item) => canAccess(user?.org_level_code, item.minLevel));
            if (items.length === 0) return null;
            const open = activeInGroup(group) || hoveredGroup === group.label;
            return (
              <div
                key={group.label}
                className="mt-4 border-t border-border pt-3"
                onMouseEnter={() => setHoveredGroup(group.label)}
                onMouseLeave={() => setHoveredGroup(null)}
              >
                <div className="flex w-full items-center justify-between rounded-md px-3 py-1.5 text-left transition hover:bg-orange/5">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
                    {t(group.label)}
                  </span>
                  <ChevronDown
                    className={`h-3.5 w-3.5 text-muted transition-transform duration-200 ${
                      open ? 'rotate-180' : ''
                    }`}
                  />
                </div>
                {open && (
                  <div className="space-y-0.5 pt-0.5">
                    {items.map((item) => (
                      <NavLink key={item.to} to={item.to} className={itemClass} onClick={closeMenu}>
                        {({ isActive }) => navItemChildren(item, isActive)}
                      </NavLink>
                    ))}
                  </div>
                )}
              </div>
            );
          })}

        </nav>

        <div className="relative px-3 pb-3 pt-1">
          {profileOpen && (
            <div className="absolute bottom-full left-3 right-3 mb-2 overflow-hidden rounded-lg border border-border bg-surface shadow-overlay">
              {(isAdmin || isLead) && (
                <NavLink
                  to={`/employees/${encodeId(user?.id ?? 0)}`}
                  onClick={closeMenu}
                  className="flex w-full items-center gap-2.5 px-3 py-2.5 text-sm text-graphite transition hover:bg-orange/10 hover:text-ink"
                >
                  <UserRound className="h-4 w-4" />
                  {t('nav.profile')}
                </NavLink>
              )}
              {isAdmin && (
                <NavLink
                  to="/settings"
                  onClick={closeMenu}
                  className="flex w-full items-center gap-2.5 px-3 py-2.5 text-sm text-graphite transition hover:bg-orange/10 hover:text-ink"
                >
                  <Settings className="h-4 w-4" />
                  {t('nav.account')}
                </NavLink>
              )}
              <button
                onClick={() => {
                  setProfileOpen(false);
                  onLogout();
                }}
                className="flex w-full items-center gap-2.5 border-t border-border px-3 py-2.5 text-left text-sm text-graphite transition hover:bg-orange/10 hover:text-ink"
              >
                <LogOut className="h-4 w-4" />
                {t('nav.signOut')}
              </button>
            </div>
          )}

          <button
            onClick={() => setProfileOpen((v) => !v)}
            className="flex w-full items-center gap-3 rounded-xl border border-border bg-surfaceWarm p-2 text-left transition hover:border-orange/30 hover:bg-surface"
          >
            <div className="relative h-10 w-10 shrink-0">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-orange text-xs font-bold text-white">
                {user ? initials(user.name) : '?'}
              </div>
              <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-success ring-2 ring-surfaceWarm" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-ink">{user?.name}</p>
              <p className="truncate text-[11px] text-graphite">{user ? [user.designation, levelLabel(user.org_level_code)].filter(Boolean).join(' · ') : ''}</p>
            </div>
            <ChevronDown
              className={`h-4 w-4 shrink-0 text-muted transition-transform duration-200 ${
                profileOpen ? 'rotate-180' : ''
              }`}
            />
          </button>
        </div>
      </div>
    </>
  );
}

export function AppLayout() {
  const user = useAuthStore((s) => s.user);
  const logout = useLogout();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  function handleLogout() {
    logout.mutate(undefined, { onSettled: () => navigate('/login', { replace: true }) });
  }

  // Accounts on a temporary password (first login / executive reset) are
  // locked to the change-password screen; the backend enforces this too.
  if (user?.must_change_password) {
    return <ForceChangePasswordPage />;
  }

  const sidebarProps = {
    user,
    onLogout: handleLogout,
  };

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col overflow-hidden border-r border-border bg-surface text-ink shadow-card lg:flex">
        <SidebarContent {...sidebarProps} onNavigate={() => undefined} />
      </aside>

      <div
        className={`fixed inset-0 z-50 lg:hidden ${mobileOpen ? '' : 'pointer-events-none'}`}
        aria-hidden={!mobileOpen}
      >
        <div
          className={`absolute inset-0 bg-navy/50 transition-opacity duration-200 ${
            mobileOpen ? 'opacity-100' : 'opacity-0'
          }`}
          onClick={() => setMobileOpen(false)}
        />
        <aside
          className={`absolute inset-y-0 left-0 flex w-64 max-w-[85vw] flex-col overflow-hidden border-r border-border bg-surface text-ink shadow-overlay transition-transform duration-200 ${
            mobileOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          <SidebarContent
            {...sidebarProps}
            onNavigate={() => setMobileOpen(false)}
          />
        </aside>
      </div>

      <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-surface px-4 lg:hidden">
        <button
          onClick={() => setMobileOpen(true)}
          aria-label="Open menu"
          className="rounded-md p-2 text-muted transition hover:bg-surfaceWarm hover:text-ink"
        >
          <Menu className="h-5 w-5" />
        </button>
        <BrandLogo />
        <div className="ml-auto flex items-center gap-1">
          <ThemeToggle />
          <NavLink
            to="/notifications"
            aria-label="Notifications"
            className="relative rounded-md p-2 text-muted transition hover:bg-surfaceWarm hover:text-ink"
          >
            <Bell className="h-5 w-5" />
            <span className="absolute -right-0.5 -top-0.5">
              <NotificationBadge />
            </span>
          </NavLink>
        </div>
      </header>

      <main className="min-w-0 flex-1 lg:ml-64">
        <div className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
