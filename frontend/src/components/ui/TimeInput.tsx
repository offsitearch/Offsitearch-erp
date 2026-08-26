import { useRef } from 'react';
import { Clock } from 'lucide-react';

/**
 * Time input styled to the app's design system (wraps the native time picker
 * behind a consistent trigger icon). Contract mirrors <input type="time">:
 * value is "HH:mm" ("" = empty).
 */
export default function TimeInput({
  value,
  onChange,
  disabled = false,
  required = false,
  compact = false,
  className = '',
}: {
  value: string;
  onChange: (time: string) => void;
  disabled?: boolean;
  required?: boolean;
  compact?: boolean;
  className?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  const openPicker = () => {
    inputRef.current?.showPicker?.();
  };

  return (
    <div className={`relative ${className}`}>
      <input
        ref={inputRef}
        type="time"
        value={value}
        required={required}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className={`w-full rounded-md border border-border bg-surface pr-9 text-ink transition focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30 disabled:cursor-not-allowed disabled:opacity-60 [&::-webkit-calendar-picker-indicator]:hidden ${
          compact ? 'h-8 px-2 text-xs' : 'h-10 px-3 text-sm'
        }`}
      />
      <button
        type="button"
        tabIndex={-1}
        onClick={openPicker}
        aria-label="Open time picker"
        className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-muted transition hover:text-navy"
      >
        <Clock className="h-4 w-4" />
      </button>
    </div>
  );
}
