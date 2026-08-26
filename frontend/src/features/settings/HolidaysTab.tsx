import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CalendarDays, Loader2, Pencil, Plus, Trash2, X } from 'lucide-react';
import { useState } from 'react';
import { createHoliday, deleteHoliday, getHolidays, updateHoliday } from '../../api/settings';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { EmptyState } from '../../components/ui/EmptyState';
import { Skeleton } from '../../components/ui/Skeleton';
import DatePicker from '../../components/ui/DatePicker';
import { useToast } from '../../components/Toast';
import { formatDate } from '../../lib/date';
import { inputClass, selectClass, primaryBtnClass, secondaryBtnClass, modalLabelClass } from '../../lib/styles';
import type { HolidayFull, HolidayInput } from '../../lib/types';

export function HolidaysTab() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const holidays = useQuery({ queryKey: ['holidays'], queryFn: getHolidays });
  const [modal, setModal] = useState<{ editing?: HolidayFull } | null>(null);
  const [deleting, setDeleting] = useState<HolidayFull | null>(null);

  const remove = useMutation({
    mutationFn: () => deleteHoliday(deleting!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['holidays'] });
      toast('Holiday deleted', 'success');
      setDeleting(null);
    },
    onError: () => toast('Failed to delete holiday', 'error'),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted">
          Office holidays. Recurring holidays repeat every year.
        </p>
        <button onClick={() => setModal({})} className={primaryBtnClass}>
          <Plus className="h-4 w-4" /> Add Holiday
        </button>
      </div>

      {holidays.isPending ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-12 w-full rounded-xl" />
          ))}
        </div>
      ) : (holidays.data ?? []).length === 0 ? (
        <EmptyState icon={CalendarDays} title="No holidays" text="Add your first office holiday." />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border bg-surface shadow-card">
          <table className="w-full min-w-[600px] text-left text-sm">
            <thead>
              <tr className="border-b border-border bg-surfaceWarm text-xs uppercase tracking-wide text-muted">
                <th className="px-4 py-3 font-semibold">Name</th>
                <th className="px-4 py-3 font-semibold">Date</th>
                <th className="px-4 py-3 font-semibold">Recurring</th>
                <th className="px-4 py-3 font-semibold">Applies to</th>
                <th className="px-4 py-3 text-right font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {(holidays.data ?? []).map((h) => (
                <tr key={h.id} className="border-b border-border last:border-0 hover:bg-surfaceWarm">
                  <td className="px-4 py-2.5 font-medium text-ink">{h.name}</td>
                  <td className="px-4 py-2.5 text-ink">{formatDate(h.date)}</td>
                  <td className="px-4 py-2.5">
                    {h.is_recurring ? (
                      <span className="rounded-full bg-successSoft px-2 py-0.5 text-xs font-medium text-success">
                        Every year
                      </span>
                    ) : (
                      <span className="text-muted">Once</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 capitalize text-ink">{h.applicable_to}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex justify-end gap-1">
                      <button
                        onClick={() => setModal({ editing: h })}
                        className="rounded-lg p-1.5 text-muted transition hover:bg-surfaceWarm hover:text-ink"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setDeleting(h)}
                        className="rounded-lg p-1.5 text-muted transition hover:bg-dangerSoft hover:text-danger"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal && (
        <HolidayModal
          holiday={modal.editing}
          onClose={() => setModal(null)}
        />
      )}
      {deleting && (
        <ConfirmDialog
          title="Delete holiday?"
          message={`"${deleting.name}" will be removed.`}
          confirmLabel="Delete"
          pending={remove.isPending}
          onConfirm={() => remove.mutate()}
          onClose={() => setDeleting(null)}
        />
      )}
    </div>
  );
}

function HolidayModal({ holiday, onClose }: { holiday?: HolidayFull; onClose: () => void }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<HolidayInput>({
    name: holiday?.name ?? '',
    date: holiday?.date ?? '',
    is_recurring: holiday?.is_recurring ?? false,
    applicable_to: holiday?.applicable_to ?? 'all',
  });

  const save = useMutation({
    mutationFn: () => (holiday ? updateHoliday(holiday.id, form) : createHoliday(form)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['holidays'] });
      toast(holiday ? 'Holiday updated' : 'Holiday added', 'success');
      onClose();
    },
    onError: () => toast('Failed to save holiday', 'error'),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    save.mutate();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
      <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-xl bg-surface p-6 shadow-overlay">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-ink">{holiday ? 'Edit holiday' : 'Add holiday'}</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-lg p-1 text-muted hover:bg-surfaceWarm">
            <X className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={submit} className="mt-4 space-y-3">
          <label className={modalLabelClass}>
            Name *
            <input
              required
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
              className={`${inputClass} mt-1`}
            />
          </label>
          <label className={modalLabelClass}>
            Date *
            <DatePicker
              value={form.date}
              onChange={(v) => setForm((p) => ({ ...p, date: v }))}
              className="mt-1"
            />
          </label>
          <label className={modalLabelClass}>
            Applies to
            <select
              value={form.applicable_to}
              onChange={(e) => setForm((p) => ({ ...p, applicable_to: e.target.value }))}
              className={`${selectClass} mt-1`}
            >
              <option value="all">All employees</option>
              <option value="field">Field staff</option>
              <option value="office">Office staff</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              checked={form.is_recurring}
              onChange={(e) => setForm((p) => ({ ...p, is_recurring: e.target.checked }))}
              className="rounded border-border"
            />
            Recurs every year
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className={secondaryBtnClass}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={save.isPending || !form.name || !form.date}
              className={primaryBtnClass}
            >
              {save.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {holiday ? 'Save changes' : 'Add holiday'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export { CalendarDays };
