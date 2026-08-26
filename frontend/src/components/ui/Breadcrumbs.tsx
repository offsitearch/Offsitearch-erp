import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export type Crumb = { label: string; to?: string };

export default function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-1 text-sm">
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        return (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && <ChevronRight className="h-3.5 w-3.5 text-graphite/50" />}
            {item.to && !isLast ? (
              <Link to={item.to} className="text-graphite transition hover:text-orange">
                {item.label}
              </Link>
            ) : (
              <span className={isLast ? 'font-medium text-ink' : 'text-graphite'}>{item.label}</span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
