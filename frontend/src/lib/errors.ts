/**
 * Extract a human-readable error message from an API error response.
 *
 * Axios errors, fetch errors, and plain Error objects are all handled.
 * Falls back to a generic message if nothing more specific is available.
 *
 * @example
 * catch (err) {
 *   toast(extractError(err), 'error');
 * }
 */
export function extractError(err: unknown, fallback = 'Something went wrong'): string {
  if (err && typeof err === 'object') {
    // Axios timeout: no response object arrives, only an error code.
    if ((err as { code?: string }).code === 'ECONNABORTED') {
      return 'The request timed out. Please try again.';
    }
    // Axios-style: err.response.data.detail
    const resp = (err as { response?: { data?: { detail?: string } } }).response;
    if (resp?.data?.detail) return resp.data.detail;
    // Plain Error
    if ('message' in err && typeof (err as Error).message === 'string') {
      return (err as Error).message;
    }
  }
  if (typeof err === 'string') return err;
  return fallback;
}
