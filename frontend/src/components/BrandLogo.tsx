/**
 * OFFSITE brand mark — "Skyline Bars".
 *
 * Five prefab modules standing side by side (off-site construction),
 * with one tall azure accent among the royal bars. The bars are drawn
 * with `currentColor` so the mark inherits its context — white on the
 * navy tile and watermarks — while the accent is a fixed brand blue.
 *
 * This component is the single source for the mark everywhere it
 * appears: sidebar tile, header, hero watermark, and favicon.
 */

export function OffsiteMark({
  className,
  mono = false,
  accent = '#C9964A',
}: {
  className?: string;
  mono?: boolean;
  /** Hex override for the tall accent bar (defaults to legacy orange). */
  accent?: string;
}) {
  const resolved = mono ? 'currentColor' : accent;
  return (
    <svg viewBox="0 0 40 40" fill="none" aria-hidden="true" className={className}>
      <rect x="2" y="24" width="6" height="14" rx="2" fill="currentColor" />
      <rect x="9.5" y="16" width="6" height="22" rx="2" fill="currentColor" />
      <rect x="17" y="20" width="6" height="18" rx="2" fill="currentColor" />
      <rect x="24.5" y="8" width="6" height="30" rx="2" fill={resolved} />
      <rect x="32" y="26" width="6" height="12" rx="2" fill="currentColor" />
    </svg>
  );
}

interface BrandLogoProps {
  /** Text color treatment. `light` is for dark surfaces (navy sidebar). */
  tone?: 'light' | 'dark';
  /** Show the "Studio ERP" subtitle. */
  showSubtitle?: boolean;
  /** Render the lockup inside a solid orange block (white mark + title). */
  block?: boolean;
  /** Hex override for the mark's tall accent bar (defaults to legacy orange). */
  accent?: string;
}

export function BrandLogo({ tone = 'dark', showSubtitle = true, block = false, accent }: BrandLogoProps) {
  const text = tone === 'light' ? 'text-white' : 'text-ink';
  const sub = tone === 'light' ? 'text-white/60' : 'text-muted';

  if (block) {
    return (
      <div className="flex items-center gap-3 rounded-lg bg-orange px-3.5 py-3 shadow-card">
        <OffsiteMark mono className="h-6 w-6 shrink-0 text-white" />
        <span className="flex flex-col">
          <span className="text-base font-semibold leading-tight tracking-tight text-white">OFFSITE</span>
          {showSubtitle && (
            <span className="mt-0.5 text-[10px] font-semibold uppercase leading-none tracking-[0.18em] text-white/75">
              Studio ERP
            </span>
          )}
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <span
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
          tone === 'light' ? 'bg-white/10 text-white' : 'bg-navy text-white'
        }`}
      >
        <OffsiteMark className="h-5 w-5" {...(accent ? { accent } : {})} />
      </span>
      <span className="flex flex-col">
        <span className={`text-base font-semibold leading-tight tracking-tight ${text}`}>OFFSITE</span>
        {showSubtitle && (
          <span className={`mt-0.5 text-[10px] font-semibold uppercase leading-none tracking-[0.18em] ${sub}`}>
            Studio ERP
          </span>
        )}
      </span>
    </div>
  );
}
