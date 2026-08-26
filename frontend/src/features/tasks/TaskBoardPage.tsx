import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  CalendarDays,
  CheckCircle2,
  Clock,
  Plus,
} from 'lucide-react';
import { useState } from 'react';
import { getProjects } from '../../api/projects';
import { getEmployees } from '../../api/employees';
import { LogoLoader } from '../../components/LogoLoader';
import { createTask, getTaskBoard } from '../../api/tasks';
import {
  canAccess,
  taskPriorityMeta,
  taskStatusMeta,
} from '../../lib/constants';
import { useAuthStore } from '../../store/authStore';
import { toISODate } from '../../lib/date';
import type { Task } from '../../lib/types';
import CreateTaskModal from './components/CreateTaskModal';
import TaskDetailModal from './components/TaskDetailModal';
import { useTranslation } from 'react-i18next';
import { inputClass, primaryBtnClass } from '../../lib/styles';

export default function TaskBoardPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const level = user?.org_level_code;
  const canManage = canAccess(level, 'L3');
  const [projectId, setProjectId] = useState<number | ''>('');
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<Task | null>(null);

  const projects = useQuery({
    queryKey: ['projects-options'],
    queryFn: () => getProjects({ page_size: 100 }),
  });

  const employees = useQuery({
    queryKey: ['employees-options'],
    queryFn: () => getEmployees({ active_only: true, page_size: 100 }),
  });

  const createMutation = useMutation({
    mutationFn: createTask,
  });

  const board = useQuery({
    queryKey: ['task-board', projectId],
    queryFn: () => getTaskBoard(projectId === '' ? undefined : Number(projectId)),
  });

  const canEdit = (task: Task) =>
    canManage || task.assigned_to === user?.id;

  const canManageTask = (task: Task) =>
    canAccess(level, 'L2') ||
    (canAccess(level, 'L3') &&
      (task.project_id == null ||
        projects.data?.items.find((p) => p.id === task.project_id)?.project_lead_id === user?.id));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">{t('tasks.taskBoard')}</h1>
          <p className="mt-1 text-sm text-muted">
            {t('tasks.kanbanBoard')} — click a card to advance it. Create tasks, manage checklists.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={projectId}
            onChange={(e) => setProjectId(e.target.value === '' ? '' : Number(e.target.value))}
            className={`${inputClass} max-w-64`}
          >
            <option value="">All projects</option>
            {projects.data?.items.map((p) => (
              <option key={p.id} value={p.id}>
                {p.project_code} · {p.name}
              </option>
            ))}
          </select>
          {canManage && (
            <button onClick={() => setShowCreate(true)} className={primaryBtnClass}>
              <Plus className="h-4 w-4" />
              New Task
            </button>
          )}
        </div>
      </div>

      {board.isPending ? (
        <LogoLoader />
      ) : (
        <div className="overflow-x-auto">
          <div className="grid min-w-[1024px] grid-cols-5 gap-4">
          {board.data?.columns.map((col) => {
            const meta = taskStatusMeta(col.status);
            return (
              <div key={col.status} className="rounded-lg border border-border bg-surfaceWarm">
                <div className="flex items-center justify-between border-b border-border px-3 py-2">
                  <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink">
                    <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
                    {meta.label}
                  </span>
                  <span className="rounded-full bg-graphite/10 px-2 py-0.5 text-xs font-medium text-muted">
                    {col.tasks.length}
                  </span>
                </div>
                <div className="space-y-2 p-3">
                  {col.tasks.length === 0 && (
                    <p className="py-4 text-center text-xs text-muted">Empty</p>
                  )}
                  {col.tasks.map((task) => {
                    const pmeta = taskPriorityMeta(task.priority);
                    const isOverdue =
                      task.due_date &&
                      task.status !== 'done' &&
                      toISODate(new Date()) > String(task.due_date).slice(0, 10);
                    return (
                      <button
                        key={task.id}
                        onClick={() => setSelected(task)}
                        className={`w-full rounded-lg border border-border bg-surface p-3 text-left shadow-card transition hover:border-orange/40 hover:shadow-overlay focus:outline-none focus-visible:ring-2 focus-visible:ring-navy/40 ${
                          task.priority === 'urgent' ? 'border-l-4 border-l-danger' : ''
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-medium leading-snug text-ink">{task.title}</p>
                          <div className="flex shrink-0 items-center gap-1.5">
                            {task.priority === 'urgent' && (
                              <span className={`h-2 w-2 rounded-full ${pmeta.dot}`} title="Urgent" />
                            )}
                            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${pmeta.badge}`}>
                              {pmeta.label}
                            </span>
                          </div>
                        </div>
                        {task.project_name && (
                          <p className="mt-1 text-xs text-muted">{task.project_name}</p>
                        )}
                        <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-muted">
                          {task.due_date && (
                            <span
                              className={`inline-flex items-center gap-1 ${
                                isOverdue ? 'font-medium text-danger' : ''
                              }`}
                            >
                              <CalendarDays className="h-3 w-3" />
                              {task.due_date}
                              {isOverdue && ' · overdue'}
                            </span>
                          )}
                          {task.estimated_hours && (
                            <span className="inline-flex items-center gap-1">
                              <Clock className="h-3 w-3" /> {task.estimated_hours}h
                            </span>
                          )}
                          {task.checklist.length > 0 && (
                            <span className="inline-flex items-center gap-1">
                              <CheckCircle2 className="h-3 w-3" />
                              {task.checklist.filter((c) => c.is_done).length}/{task.checklist.length}
                            </span>
                          )}
                          {task.assignee_name && <span>· {task.assignee_name}</span>}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
          </div>
        </div>
      )}

      {showCreate && (
        <CreateTaskModal
          projects={(projects.data?.items ?? []).map((p) => ({ id: p.id, code: p.project_code, name: p.name }))}
          employees={(employees.data?.items ?? []).map((e) => ({ id: e.id, name: e.name }))}
          onClose={() => setShowCreate(false)}
          onSubmit={(payload) =>
            createMutation.mutate(payload, {
              onSuccess: () => {
                setShowCreate(false);
                queryClient.invalidateQueries({ queryKey: ['task-board', projectId] });
              },
            })
          }
          pending={createMutation.isPending}
          error={createMutation.error as { response?: { data?: { detail?: string } } } | null}
        />
      )}

      {selected && (
        <TaskDetailModal
          taskId={selected.id}
          canEdit={canEdit(selected)}
          canReassign={canManageTask(selected)}
          canDelete={canManageTask(selected)}
          employees={(employees.data?.items ?? []).map((e) => ({ id: e.id, name: e.name }))}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
