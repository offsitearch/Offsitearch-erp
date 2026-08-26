import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';

export function SectionCard({
  title,
  icon: Icon,
  action,
  children,
  delay,
}: {
  title: string;
  icon: LucideIcon;
  action?: ReactNode;
  children: ReactNode;
  delay?: string;
}) {
  return (
    <section
      className="animate-rise rounded-lg border border-border bg-surface p-5 shadow-card"
      style={delay ? { animationDelay: delay } : undefined}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-navy" />
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
        </div>
        {action}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}
