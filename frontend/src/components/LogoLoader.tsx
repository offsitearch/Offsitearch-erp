export function LogoLoader({ className = '' }: { className?: string }) {
  return (
    <div className={`flex min-h-[40vh] flex-col items-center justify-center ${className}`} role="status" aria-label="Loading">
      <svg viewBox="0 0 40 40" fill="none" className="h-12 w-12" aria-hidden="true">
        <rect x="2" y="24" width="6" height="14" rx="2" fill="currentColor" className="text-navy animate-loader-bar" style={{ animationDelay: '0ms' }} />
        <rect x="9.5" y="16" width="6" height="22" rx="2" fill="currentColor" className="text-navy animate-loader-bar" style={{ animationDelay: '100ms' }} />
        <rect x="17" y="20" width="6" height="18" rx="2" fill="currentColor" className="text-navy animate-loader-bar" style={{ animationDelay: '200ms' }} />
        <rect x="24.5" y="8" width="6" height="30" rx="2" fill="#C9964A" className="animate-loader-bar" style={{ animationDelay: '300ms' }} />
        <rect x="32" y="26" width="6" height="12" rx="2" fill="currentColor" className="text-navy animate-loader-bar" style={{ animationDelay: '400ms' }} />
      </svg>
    </div>
  );
}
