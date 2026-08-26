export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-graphite/10 ${className}`} />;
}
