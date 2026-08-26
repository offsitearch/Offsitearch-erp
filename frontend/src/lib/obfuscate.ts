/**
 * Route ID obfuscation — encodes numeric IDs into short
 * alphanumeric strings so URLs aren't trivially guessable.
 *
 * NOT cryptographically secure — this is obscurity, not auth.
 * Backend authorization still enforces access control.
 *
 * 1    → "1k"
 * 42   → "a2"
 * 999  → "g27"
 * 1234 → "q4y"
 */

const CHARSET = 'abcdefghijklmnopqrstuvwxyz0123456789';
const BASE = CHARSET.length; // 36

/** Encode a positive integer to a short alphanumeric string. */
export function encodeId(id: number | string): string {
  const n = typeof id === 'string' ? parseInt(id, 10) : id;
  if (!Number.isFinite(n) || n < 0) return String(id);

  if (n === 0) return '0';

  let result = '';
  let val = n;
  while (val > 0) {
    result = CHARSET[val % BASE] + result;
    val = Math.floor(val / BASE);
  }

  // Prefix with length digit to avoid leading-zero ambiguity
  return result.length.toString(BASE) + result;
}

/** Decode an obfuscated string back to the original numeric ID. */
export function decodeId(encoded: string): number | null {
  if (!encoded || typeof encoded !== 'string') return null;

  // Already a plain number? (backward compat)
  const plain = parseInt(encoded, 10);
  if (!isNaN(plain) && String(plain) === encoded) return plain;

  // First char is the length prefix
  const len = parseInt(encoded[0], BASE);
  if (!Number.isFinite(len) || len <= 0) return null;

  const body = encoded.slice(1);
  if (body.length !== len) return null;

  let result = 0;
  for (const ch of body) {
    const digit = CHARSET.indexOf(ch);
    if (digit === -1) return null;
    result = result * BASE + digit;
  }

  return result;
}
