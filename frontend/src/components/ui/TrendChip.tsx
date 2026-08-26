import { TrendingDown, TrendingUp } from 'lucide-react';

export function TrendChip({
  current,
  previous,
  label,
}: {
  current: number;
  previous: number | undefined;
  label: string;
}) {
  if (previous === undefined) return null;
  if (previous === 0 && current === 0) return null;
  const up = current >= previous;
  const pct = previous === 0 ? 100 : ((current - previous) / previous) * 100;
  const Icon = up ? TrendingUp : TrendingDown;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${
        up ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'
      }`}
    >
      <Icon className="h-3 w-3" />
      {previous === 0 && current > 0 ? 'new' : `${Math.abs(pct).toFixed(1)}%`}
      <span className="opacity-70">{label}</span>
    </span>
  );
}
