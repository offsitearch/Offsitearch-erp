import type { ReactNode } from 'react';

/**
 * Standard page header with title, subtitle, and optional action button.
 *
 * Used at the top of every feature page for consistent layout.
 *
 * @example
 * <PageHeader title="Projects" subtitle="Manage studio projects">
 *   <button className={primaryBtnClass}>New Project</button>
 * </PageHeader>
 */
export function PageHeader({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 className="text-xl font-bold text-ink sm:text-2xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  );
}
