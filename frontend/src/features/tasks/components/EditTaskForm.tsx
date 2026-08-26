import { useState } from 'react';
import { TASK_PRIORITY_OPTIONS } from '../../../lib/constants';
import type { Task } from '../../../lib/types';
import { updateTask } from '../../../api/tasks';
import { primaryBtnClass, secondaryBtnClass, modalFieldClass, modalLabelClass } from '../../../lib/styles';
import DatePicker from '../../../components/ui/DatePicker';

export default function EditTaskForm({
  task,
  employees,
  canReassign,
  pending,
  error,
  onCancel,
  onSubmit,
}: {
  task: Task;
  employees: { id: number; name: string }[];
  canReassign: boolean;
  pending: boolean;
  error: { response?: { data?: { detail?: string } } } | null;
  onCancel: () => void;
  onSubmit: (payload: Parameters<typeof updateTask>[1]) => void;
}) {
  const [form, setForm] = useState({
    title: task.title,
    description: task.description ?? '',
    assigned_to: task.assigned_to ?? '',
    priority: task.priority,
    start_date: task.start_date ?? '',
    due_date: task.due_date ?? '',
    estimated_hours: task.estimated_hours ?? '',
    actual_hours: task.actual_hours ?? '',
    tags: (task.tags ?? []).join(', '),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      title: form.title,
      description: form.description || undefined,
      assigned_to: form.assigned_to === '' ? null : Number(form.assigned_to),
      priority: form.priority,
      start_date: form.start_date || null,
      due_date: form.due_date || null,
      estimated_hours: form.estimated_hours === '' ? null : Number(form.estimated_hours),
      actual_hours: form.actual_hours === '' ? null : Number(form.actual_hours),
      tags: form.tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
    });
  }

  const set = (key: keyof typeof form, value: string) => setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <form onSubmit={submit} className="space-y-4">
      <input
        required
        value={form.title}
        onChange={(e) => set('title', e.target.value)}
        placeholder="Task title"
        className={modalFieldClass}
      />
      <textarea
        value={form.description}
        onChange={(e) => set('description', e.target.value)}
        placeholder="Description"
        rows={3}
        className={`${modalFieldClass} h-auto py-2`}
      />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className="block">
          <span className={modalLabelClass}>Assignee</span>
          <select
            value={form.assigned_to}
            onChange={(e) => set('assigned_to', e.target.value)}
            disabled={!canReassign}
            className={`${modalFieldClass} disabled:cursor-not-allowed disabled:opacity-60`}
          >
            <option value="">Unassigned</option>
            {employees.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className={modalLabelClass}>Priority</span>
          <select
            value={form.priority}
            onChange={(e) => set('priority', e.target.value)}
            className={modalFieldClass}
          >
            {TASK_PRIORITY_OPTIONS.map((p) => (
              <option key={p} value={p}>
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className="block">
          <span className={modalLabelClass}>Start date</span>
          <DatePicker value={form.start_date} onChange={(v) => set('start_date', v)} className="mt-1" />
        </label>
        <label className="block">
          <span className={modalLabelClass}>Due date</span>
          <DatePicker value={form.due_date} onChange={(v) => set('due_date', v)} className="mt-1" />
        </label>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className="block">
          <span className={modalLabelClass}>Est. hours</span>
          <input
            type="number"
            min="0"
            value={form.estimated_hours}
            onChange={(e) => set('estimated_hours', e.target.value)}
            className={modalFieldClass}
          />
        </label>
        <label className="block">
          <span className={modalLabelClass}>Actual hours</span>
          <input
            type="number"
            min="0"
            value={form.actual_hours}
            onChange={(e) => set('actual_hours', e.target.value)}
            className={modalFieldClass}
          />
        </label>
      </div>
      <input
        value={form.tags}
        onChange={(e) => set('tags', e.target.value)}
        placeholder="Tags, comma separated"
        className={modalFieldClass}
      />
      {error?.response?.data?.detail && (
        <div className="rounded-md border border-danger/30 bg-dangerSoft px-3 py-2.5 text-sm text-danger">
          {error.response.data.detail}
        </div>
      )}
      <div className="flex justify-end gap-2 pt-1">
        <button type="button" onClick={onCancel} className={secondaryBtnClass}>
          Cancel
        </button>
        <button type="submit" disabled={pending} className={primaryBtnClass}>
          {pending ? 'Saving…' : 'Save changes'}
        </button>
      </div>
    </form>
  );
}
