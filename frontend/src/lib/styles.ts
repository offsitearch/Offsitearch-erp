/**
 * Shared Tailwind CSS class strings.
 *
 * Centralises the most-repeated UI patterns so individual feature
 * pages import them instead of re-declaring identical strings.
 *
 * Usage:
 *   import { inputClass, primaryBtnClass } from '../../lib/styles';
 */

/* ── Inputs ───────────────────────────────────────────────────── */

/**
 * Standard text / number / date input. Sizing stays fixed (h-10, no width) so
 * call-sites can compose widths freely; visuals are the modern baseline:
 * soft card shadow, hover border lift, brand focus ring, muted placeholder.
 */
export const inputClass =
  'h-10 rounded-md border border-border bg-surface px-3 text-sm text-ink shadow-card transition placeholder:text-muted/70 hover:border-graphite/40 focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30 disabled:cursor-not-allowed disabled:bg-surfaceWarm/50 disabled:opacity-70';

/**
 * Standard select dropdown — same visual as inputClass plus a custom chevron
 * (.select-chevron in styles/index.css strips the native arrow and paints a
 * brand-styled one; the popup itself stays native for accessibility).
 */
export const selectClass = `${inputClass} select-chevron`;

/** Compact text input (smaller height) */
export const smallInputClass =
  'h-8 rounded-md border border-border bg-surface px-2 text-sm text-ink shadow-card transition placeholder:text-muted/70 hover:border-graphite/40 focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30 disabled:cursor-not-allowed disabled:bg-surfaceWarm/50 disabled:opacity-70';

/** Compact select — smallInputClass + chevron */
export const smallSelectClass = `${smallInputClass} select-chevron`;

/* ── Labels ───────────────────────────────────────────────────── */

/** Form label wrapping a field */
export const labelClass = 'mb-1 block text-xs font-medium text-muted';

/** Label inside a modal form */
export const modalLabelClass = labelClass;

/** Field wrapper inside a modal */
export const modalFieldClass = labelClass;

/* ── Buttons ──────────────────────────────────────────────────── */

/** Primary action button (orange) */
export const primaryBtnClass =
  'inline-flex h-10 items-center justify-center gap-2 rounded-md bg-orange px-4 text-sm font-medium text-white transition hover:bg-orangeDark focus:outline-none focus:ring-2 focus:ring-orange/40 disabled:cursor-not-allowed disabled:opacity-60';

/** Secondary / outline button */
export const secondaryBtnClass =
  'inline-flex h-10 items-center justify-center gap-2 rounded-md border border-border bg-surface px-4 text-sm font-medium text-ink transition hover:bg-surfaceWarm focus:outline-none focus-visible:ring-2 focus-visible:ring-navy/40';

/** Danger / destructive button */
export const dangerBtnClass =
  'inline-flex h-10 items-center justify-center gap-2 rounded-md bg-danger px-4 text-sm font-medium text-white transition hover:bg-dangerDark focus:outline-none focus:ring-2 focus:ring-danger/40 disabled:cursor-not-allowed disabled:opacity-60';

/** Small / compact button */
export const smallBtnClass =
  'inline-flex h-8 items-center justify-center gap-1.5 rounded-md px-3 text-xs font-medium transition focus:outline-none disabled:opacity-60';

/** Page navigation button (pagination) */
export const pageBtnClass =
  'inline-flex h-8 min-w-[2rem] items-center justify-center rounded-md border border-border bg-surface text-xs font-medium text-ink transition hover:bg-surfaceWarm disabled:opacity-40';
