import { Building2, Network, Users } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { canAccess } from '../../../lib/constants';

interface Tab {
  to: string;
  label: string;
  icon: typeof Users;
  minLevel: string;
  end?: boolean;
}

const TABS: Tab[] = [
  { to: '/employees', label: 'Directory', icon: Users, minLevel: 'L6', end: true },
  { to: '/employees/org-chart', label: 'Org Chart', icon: Network, minLevel: 'L6' },
  { to: '/departments', label: 'Departments', icon: Building2, minLevel: 'L2' },
];

export function EmployeeTabs({ level }: { level: string | null | undefined }) {
  const visible = TABS.filter((tab) => canAccess(level, tab.minLevel));
  return (
    <nav aria-label="Employees sections" className="flex flex-wrap items-center gap-1 border-b border-border">
      {visible.map((tab) => {
        const Icon = tab.icon;
        return (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
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
