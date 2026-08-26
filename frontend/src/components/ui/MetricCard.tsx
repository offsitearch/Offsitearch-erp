import type { LucideIcon } from 'lucide-react';
import { ArrowUpRight } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Skeleton } from './Skeleton';

export function MetricCard({
  label,
  value,
  context,
  trend,
  icon: Icon,
  pending,
  failed,
  to,
}: {
  label: string;
  value: string | number | undefined;
  context?: string;
  trend?: ReactNode;
  icon: LucideIcon;
  pending: boolean;
  failed: boolean;
  to?: string;
}) {
  const inner = (
    <>
      <span aria-hidden className="absolute inset-x-0 top-0 h-0.5 bg-orange opacity-0 transition group-hover:opacity-100" />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          {pending ? (
            <Skeleton className="h-8 w-20" />
          ) : (
            <p className="text-3xl font-semibold tracking-tight text-ink">
              {failed || value === undefined ? '—' : value}
            </p>
          )}
          <p className="mt-1 text-xs font-semibold uppercase tracking-wider text-muted">{label}</p>
          {context && <p className="mt-0.5 text-xs text-muted">{context}</p>}
          {trend && <div className="mt-1.5">{trend}</div>}
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className="flex h-10 w-10 items-center justify-center rounded-md bg-navy/10 text-navy transition group-hover:bg-orange/10 group-hover:text-orange">
            <Icon className="h-5 w-5" />
          </span>
          <ArrowUpRight className="h-4 w-4 text-muted opacity-0 transition group-hover:opacity-100 group-hover:text-orange" />
        </div>
      </div>
    </>
  );

  const classes =
    'group relative flex flex-col overflow-hidden rounded-lg border border-border bg-surface p-5 shadow-card transition duration-200 hover:-translate-y-0.5 hover:border-navy/25 hover:shadow-overlay';

  return to ? (
    <Link to={to} className={classes}>
      {inner}
    </Link>
  ) : (
    <div className={classes}>{inner}</div>
  );
}
