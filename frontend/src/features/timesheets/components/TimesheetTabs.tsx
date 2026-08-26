import { ClipboardCheck, History } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { canAccess } from '../../../lib/constants';

interface Tab {
  to: string;
  label: string;
  icon: typeof History;
  minLevel: string;
}

const TABS: Tab[] = [
  { to: '/timesheets', label: 'My Timesheet', icon: History, minLevel: 'L6' },
  { to: '/timesheets/approvals', label: 'Approvals', icon: ClipboardCheck, minLevel: 'L3' },
];

export function TimesheetTabs({ level }: { level: string | null | undefined }) {
  const visible = TABS.filter((tab) => canAccess(level, tab.minLevel));
  return (
    <nav aria-label="Timesheet sections" className="flex flex-wrap items-center gap-1 border-b border-border">
      {visible.map((tab) => {
        const Icon = tab.icon;
        return (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.to === '/timesheets'}
            className={({ isActive }) =>
              `inline-flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition ${
                isActive
                  ? 'border-orange text-ink'
                  : 'border-transparent text-muted hover:border-border hover:text-ink'
              }`
            }
          >
            <Icon className="h-4 w-4" />
            {tab.label}
          </NavLink>
        );
      })}
    </nav>
  );
}
