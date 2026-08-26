import { IndianRupee, Receipt, Wallet, FileText, ClipboardList } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { canAccess } from '../../../lib/constants';

interface Tab {
  to: string;
  label: string;
  icon: typeof Wallet;
  minLevel?: string;
}

const TABS: Tab[] = [
  // Financial sections are executive-only (L0/L1) per the financial access policy.
  { to: '/finance/overview', label: 'Overview', icon: Wallet, minLevel: 'L1' },
  { to: '/finance/invoices', label: 'Invoices', icon: FileText, minLevel: 'L1' },
  { to: '/finance/expenses', label: 'Expenses', icon: Receipt, minLevel: 'L1' },
  { to: '/finance/my-expenses', label: 'My Expenses', icon: ClipboardList },
  { to: '/finance/payroll', label: 'Payroll', icon: IndianRupee, minLevel: 'L1' },
];

export function FinanceTabs({ level }: { level: string | null | undefined }) {
  const visible = TABS.filter((tab) => !tab.minLevel || canAccess(level, tab.minLevel));
  return (
    <nav aria-label="Finance sections" className="flex flex-wrap items-center gap-1 border-b border-border">
      {visible.map((tab) => {
        const Icon = tab.icon;
        return (
          <NavLink
            key={tab.to}
            to={tab.to}
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
