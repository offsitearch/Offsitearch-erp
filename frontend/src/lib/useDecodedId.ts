import { useParams } from 'react-router-dom';
import { decodeId } from './obfuscate';

/**
 * Extract an obfuscated ID from URL params and decode it.
 * Returns `null` if the param is missing or can't be decoded.
 *
 * @example
 * const userId = useDecodedId('id');
 * // URL /employees/e3x7k9 → userId = 1
 */
export function useDecodedId(param = 'id'): number | null {
  const params = useParams<Record<string, string | undefined>>();
  const raw = params[param];
  if (raw == null) return null;
  return decodeId(raw);
}

/**
 * Like useDecodedId but asserts the value is present.
 * Use only inside routes where the param is guaranteed by the router.
 */
export function useDecodedIdRequired(param = 'id'): number {
  const id = useDecodedId(param);
  if (id == null) throw new Error(`Missing required param: ${param}`);
  return id;
}
