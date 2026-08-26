import { CalendarDays, ClipboardList, History, UserCheck } from 'lucide-react';
import { lazy, Suspense, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { canAccess } from '../../lib/constants';
import { Skeleton } from '../../components/ui/Skeleton';
import { useTranslation } from 'react-i18next';

const MyAttendancePage = lazy(() => import('./MyAttendancePage'));
const TodayAttendancePage = lazy(() => import('./TodayAttendancePage'));
const AttendanceCalendarPage = lazy(() => import('./AttendanceCalendarPage'));
const BulkAttendancePage = lazy(() => import('./BulkAttendancePage'));

interface Tab {
  key: string;
  label: string;
  icon: typeof History;
  minLevel: string;
}

const TABS: Tab[] = [
  { key: 'my', label: 'attendance.myAttendance', icon: UserCheck, minLevel: 'L6' },
  { key: 'today', label: 'attendance.today', icon: History, minLevel: 'L3' },
  { key: 'calendar', label: 'attendance.calendar', icon: CalendarDays, minLevel: 'L3' },
  { key: 'bulk', label: 'attendance.bulkEntry', icon: ClipboardList, minLevel: 'L2' },
];

function TabSkeleton() {
  return (
    <div className="space-y-4 p-1">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

export default function AttendancePage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const [searchParams, setSearchParams] = useSearchParams();

  const visibleTabs = useMemo(
    () => TABS.filter((tab) => canAccess(user?.org_level_code, tab.minLevel)),
    [user?.org_level_code],
  );

  const activeKey = searchParams.get('tab') || 'my';
  const activeTab = visibleTabs.find((tab) => tab.key === activeKey) || visibleTabs[0];

  const setTab = (key: string) => {
    setSearchParams({ tab: key }, { replace: true });
  };

  return (
    <div className="space-y-0">
      <nav aria-label="Attendance sections" className="flex flex-wrap items-center gap-1 border-b border-border">
        {visibleTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab.key === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setTab(tab.key)}
              className={`inline-flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition ${
                isActive
                  ? 'border-orange text-ink'
                  : 'border-transparent text-muted hover:border-border hover:text-ink'
              }`}
            >
              <Icon className="h-4 w-4" />
              {t(tab.label)}
            </button>
          );
        })}
      </nav>

      <div className="pt-4">
        <Suspense fallback={<TabSkeleton />}>
          {activeTab.key === 'my' && <MyAttendancePage />}
          {activeTab.key === 'today' && <TodayAttendancePage />}
          {activeTab.key === 'calendar' && <AttendanceCalendarPage />}
          {activeTab.key === 'bulk' && <BulkAttendancePage />}
        </Suspense>
      </div>
    </div>
  );
}
