import { useCallback, useState } from 'react';

/**
 * Copy text to clipboard and track the "copied" state.
 *
 * Returns `{ copied, copy }` — call `copy(text)` to write to clipboard.
 * The `copied` flag auto-resets after 2 seconds.
 *
 * @example
 * const { copied, copy } = useCopyToClipboard();
 * <button onClick={() => copy(email)}>
 *   {copied ? 'Copied!' : 'Copy'}
 * </button>
 */
export function useCopyToClipboard(resetMs = 2000) {
  const [copied, setCopied] = useState(false);

  const copy = useCallback(
    (text: string) => {
      navigator.clipboard.writeText(text).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), resetMs);
      });
    },
    [resetMs],
  );

  return { copied, copy };
}
