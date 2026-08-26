import { formatIndianCurrencyInput } from '../../lib/currencyInput';

/**
 * Money input with a ₹ prefix and live Indian digit grouping (10,000 /
 * 1,00,000) via lib/currencyInput. Holds the FORMATTED string in its value;
 * call-sites convert with parseIndianCurrencyInput() before submitting.
 */
export default function CurrencyInput({
  value,
  onChange,
  placeholder = '0',
  disabled = false,
  required = false,
  compact = false,
  className = '',
}: {
  value: string;
  onChange: (formatted: string) => void;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  compact?: boolean;
  className?: string;
}) {
  return (
    <div className={`relative ${className}`}>
      <span
        aria-hidden="true"
        className={`pointer-events-none absolute top-1/2 -translate-y-1/2 font-medium text-muted ${
          compact ? 'left-2 text-xs' : 'left-3 text-sm'
        }`}
      >
        ₹
      </span>
      <input
        type="text"
        inputMode="numeric"
        required={required}
        disabled={disabled}
        value={value}
        onChange={(e) => onChange(formatIndianCurrencyInput(e.target.value))}
        placeholder={placeholder}
        className={`w-full rounded-md border border-border bg-surface text-ink shadow-card transition placeholder:text-muted/70 hover:border-graphite/40 focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30 disabled:cursor-not-allowed disabled:bg-surfaceWarm/50 disabled:opacity-70 ${
          compact ? 'h-8 pl-6 pr-2 text-xs' : 'h-10 pl-7 pr-3 text-sm'
        }`}
      />
    </div>
  );
}
