import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, Circle, Pencil, Tag, Trash2, X } from 'lucide-react';
import { useState } from 'react';
import { addChecklistItem, deleteTask, getTask, toggleChecklistItem, updateTask } from '../../../api/tasks';
import { Modal } from '../../../components/Modal';
import { taskPriorityMeta, taskStatusMeta } from '../../../lib/constants';
import type { TaskStatus } from '../../../lib/types';
import EditTaskForm from './EditTaskForm';

const FLOW: TaskStatus[] = ['todo', 'in_progress', 'review', 'done'];

const secondaryBtnClass =
  'inline-flex h-9 items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 text-sm font-medium text-ink transition hover:bg-surfaceWarm focus:outline-none focus-visible:ring-2 focus-visible:ring-navy/40';

export default function TaskDetailModal({
  taskId,
  canEdit,
  canReassign,
  canDelete,
  employees,
  onClose,
}: {
  taskId: number;
  canEdit: boolean;
  canReassign: boolean;
  canDelete: boolean;
  employees: { id: number; name: string }[];
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [newItem, setNewItem] = useState('');
  const [edit, setEdit] = useState(false);

  const task = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => getTask(taskId),
  });

  const advanceMutation = useMutation({
    mutationFn: (status: TaskStatus) => updateTask(taskId, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task-board'] });
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
    },
  });

  const editMutation = useMutation({
    mutationFn: (payload: Parameters<typeof updateTask>[1]) => updateTask(taskId, payload),
    onSuccess: () => {
      setEdit(false);
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      queryClient.invalidateQueries({ queryKey: ['task-board'] });
    },
  });

  const addItemMutation = useMutation({
    mutationFn: (text: string) => addChecklistItem(taskId, text),
    onSuccess: () => {
      setNewItem('');
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
    },
  });

  const toggleItemMutation = useMutation({
    mutationFn: (itemId: number) => toggleChecklistItem(taskId, itemId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['task', taskId] }),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteTask(taskId),
    onSuccess: () => {
      onClose();
      queryClient.invalidateQueries({ queryKey: ['task-board'] });
    },
  });

  const data = task.data;
  const nextStatus =
    data && data.status !== 'blocked'
      ? FLOW[FLOW.indexOf(data.status) + 1]
      : data?.status === 'blocked'
        ? 'in_progress'
        : undefined;

  return (
    <Modal onClose={onClose}>
      <div className="flex max-h-[85vh] w-full flex-col overflow-hidden rounded-xl border border-border bg-surface shadow-overlay">
        <div className="flex items-start justify-between gap-3 border-b border-border px-6 py-4">
          <div>
            <div className="flex items-center gap-2">
              <span
                className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${taskPriorityMeta(data?.priority ?? 'medium').badge}`}
              >
                {taskPriorityMeta(data?.priority ?? 'medium').label}
              </span>
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${taskStatusMeta(data?.status ?? 'todo').badge}`}>
                {taskStatusMeta(data?.status ?? 'todo').label}
              </span>
            </div>
            <h2 className="mt-2 text-lg font-semibold tracking-tight text-ink">{data?.title ?? '…'}</h2>
          </div>
          <button onClick={onClose} aria-label="Close" className="rounded-md p-1 text-muted transition hover:bg-surfaceWarm hover:text-ink">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto px-6 py-4">
          {edit && data ? (
            <EditTaskForm
              task={data}
              employees={employees}
              canReassign={canReassign}
              pending={editMutation.isPending}
              error={editMutation.error as { response?: { data?: { detail?: string } } } | null}
              onCancel={() => setEdit(false)}
              onSubmit={(payload) => editMutation.mutate(payload)}
            />
          ) : (
            <>
              {data?.description && (
                <p className="whitespace-pre-wrap text-sm text-muted">{data.description}</p>
              )}

              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="rounded-md bg-graphite/5 px-3 py-2">
                  <p className="text-xs text-muted">Project</p>
                  <p className="font-medium text-ink">{data?.project_name ?? '—'}</p>
                </div>
                <div className="rounded-md bg-graphite/5 px-3 py-2">
                  <p className="text-xs text-muted">Assignee</p>
                  <p className="font-medium text-ink">{data?.assignee_name ?? 'Unassigned'}</p>
                </div>
                <div className="rounded-md bg-graphite/5 px-3 py-2">
                  <p className="text-xs text-muted">Due date</p>
                  <p className="font-medium text-ink">{data?.due_date ?? '—'}</p>
                </div>
                <div className="rounded-md bg-graphite/5 px-3 py-2">
                  <p className="text-xs text-muted">Est. / actual</p>
                  <p className="font-medium text-ink">
                    {data?.estimated_hours ?? '0'}h / {data?.actual_hours ?? '0'}h
                  </p>
                </div>
              </div>

              {data?.tags && data.tags.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5">
                  <Tag className="h-3.5 w-3.5 text-muted" />
                  {data.tags.map((tag) => (
                    <span key={tag} className="rounded-full bg-graphite/10 px-2 py-0.5 text-xs font-medium text-muted">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </>
          )}

          <div>
            <h3 className="text-sm font-semibold text-ink">Checklist</h3>
            <div className="mt-2 space-y-1.5">
              {data?.checklist.map((item) => (
                <div key={item.id} className="flex items-center gap-2 rounded-md border border-border px-3 py-2">
                  <button
                    disabled={!canEdit}
                    onClick={() => toggleItemMutation.mutate(item.id)}
                    className="text-muted transition hover:text-orange disabled:cursor-default"
                  >
                    {item.is_done ? (
                      <CheckCircle2 className="h-4 w-4 text-success" />
                    ) : (
                      <Circle className="h-4 w-4" />
                    )}
                  </button>
                  <span
                    className={`text-sm ${item.is_done ? 'text-muted line-through' : 'text-ink'}`}
                  >
                    {item.text}
                  </span>
                </div>
              ))}
              {data?.checklist.length === 0 && (
                <p className="text-sm text-muted">No checklist items yet.</p>
              )}
            </div>
            {canEdit && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (newItem.trim()) addItemMutation.mutate(newItem.trim());
                }}
                className="mt-2 flex gap-2"
              >
                <input
                  value={newItem}
                  onChange={(e) => setNewItem(e.target.value)}
                  placeholder="Add a checklist item…"
                  className="h-9 flex-1 rounded-md border border-border bg-surface px-3 text-sm text-ink transition focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/30"
                />
                <button
                  type="submit"
                  disabled={!newItem.trim()}
                  className="rounded-md bg-graphite/10 px-3 text-sm font-medium text-ink transition hover:bg-graphite/20 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Add
                </button>
              </form>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between gap-2 border-t border-border px-6 py-3">
          <div className="flex items-center gap-2">
            {canEdit && !edit && (
              <>
                {nextStatus && (
                  <button
                    onClick={() => advanceMutation.mutate(nextStatus)}
                    disabled={advanceMutation.isPending}
                    className="rounded-md bg-orange px-3 py-2 text-sm font-medium text-white transition hover:bg-orangeDark disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Move to {taskStatusMeta(nextStatus).label} →
                  </button>
                )}
                <button
                  onClick={() => setEdit(true)}
                  disabled={!data}
                  className={secondaryBtnClass}
                >
                  <Pencil className="h-3.5 w-3.5" />
                  Edit
                </button>
              </>
            )}
            {canDelete && !edit && (
              <button
                onClick={() => deleteMutation.mutate()}
                title="Delete task"
                className="rounded-md border border-danger/30 bg-surface p-2 text-danger transition hover:bg-dangerSoft"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>
          <button onClick={onClose} className={secondaryBtnClass}>
            Close
          </button>
        </div>
      </div>
    </Modal>
  );
}
