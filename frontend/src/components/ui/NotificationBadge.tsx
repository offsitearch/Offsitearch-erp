import { useUnreadCount } from '../../hooks/useUnreadCount';

export function NotificationBadge({ tone = 'orange' }: { tone?: 'orange' | 'light' }) {
  const { data } = useUnreadCount();
  if (!data || data <= 0) return null;
  return (
    <span
      className={`inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[11px] font-semibold tabular-nums ${
        tone === 'orange' ? 'bg-orange text-white' : 'bg-white/25 text-white'
      }`}
    >
      {data > 99 ? '99+' : data}
    </span>
  );
}
