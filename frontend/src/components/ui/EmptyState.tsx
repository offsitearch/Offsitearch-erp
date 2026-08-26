import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';

export function EmptyState({
  icon: Icon,
  title,
  text,
  action,
  dashed = true,
}: {
  icon: LucideIcon;
  title: string;
  text?: string;
  action?: ReactNode;
  dashed?: boolean;
}) {
  return (
    <div
      className={`flex flex-col items-center gap-2 px-4 py-8 text-center ${
        dashed ? 'rounded-md border border-dashed border-border' : ''
      }`}
    >
      <Icon className="h-8 w-8 text-muted" />
      <p className="text-sm font-medium text-ink">{title}</p>
      {text && <p className="max-w-64 text-xs text-muted">{text}</p>}
      {action}
    </div>
  );
}
