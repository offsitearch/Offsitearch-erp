import { useState, useCallback } from 'react';

/**
 * Manage a delete confirmation dialog's open/close state.
 *
 * Returns `{ open, confirmDelete, cancelDelete, target }` where
 * `target` holds the item queued for deletion (or null).
 *
 * @example
 * const { open, confirmDelete, cancelDelete, target } = useDeleteConfirmation();
 * <button onClick={() => confirmDelete(item)}>Delete</button>
 * {open && <ConfirmDialog onConfirm={() => doDelete(target)} onCancel={cancelDelete} />}
 */
export function useDeleteConfirmation<T = unknown>() {
  const [target, setTarget] = useState<T | null>(null);

  const confirmDelete = useCallback((item: T) => setTarget(item), []);
  const cancelDelete = useCallback(() => setTarget(null), []);

  return { open: target !== null, target, confirmDelete, cancelDelete };
}
