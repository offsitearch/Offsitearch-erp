import { useQuery } from '@tanstack/react-query';
import { X } from 'lucide-react';
import { useState } from 'react';
import { getProject } from '../../../api/projects';
import { Modal } from '../../../components/Modal';
import DatePicker from '../../../components/ui/DatePicker';
import { TASK_PRIORITY_OPTIONS } from '../../../lib/constants';
import { primaryBtnClass, secondaryBtnClass, inputClass, modalLabelClass } from '../../../lib/styles';
import type { TaskPriority } from '../../../lib/types';

export default function CreateTaskModal({
  projects,
  employees,
  onClose,
  onSubmit,
  pending,
  error,
}: {
  projects: { id: number; code: string; name: string }[];
  employees: { id: number; name: string }[];
  onClose: () => void;
  onSubmit: (payload: {
    title: string;
    description?: string;
    project_id: number | null;
    phase_id?: number | null;
    assigned_to: number | null;
    priority: TaskPriority;
    start_date?: string | null;
    due_date: string | null;
    estimated_hours: number | null;
    tags?: string[];
  }) => void;
  pending: boolean;
  error: { response?: { data?: { detail?: string } } } | null;
}) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [projectId, setProjectId] = useState<number | ''>('');
  const [phaseId, setPhaseId] = useState<number | ''>('');
  const [assignee, setAssignee] = useState<number | ''>('');
  const [priority, setPriority] = useState<TaskPriority>('medium');
  const [startDate, setStartDate] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [hours, setHours] = useState('');
  const [tags, setTags] = useState('');

  const phases = useQuery({
    queryKey: ['task-create-phases', projectId],
    queryFn: () => getProject(Number(projectId)),
    enabled: projectId !== '',
    select: (p) => p.phases,
  });

  const selectedProject = projects.find((p) => p.id === projectId) ?? null;
  const phaseOptions = projectId === '' ? [] : phases.data ?? [];

  function submit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      title,
      description: description || undefined,
      project_id: projectId === '' ? null : Number(projectId),
      phase_id: phaseId === '' ? null : Number(phaseId),
      assigned_to: assignee === '' ? null : Number(assignee),
      priority,
      start_date: startDate || null,
      due_date: dueDate || null,
      estimated_hours: hours ? Number(hours) : null,
      tags: tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
    });
  }

  return (
    <Modal onClose={onClose}>
      <div className="p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold tracking-tight text-ink">New Task</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-md p-1 text-muted transition hover:bg-surfaceWarm hover:text-ink">
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-0.5 text-sm text-muted">
          {selectedProject
            ? `Phases shown are from ${selectedProject.code}.`
            : 'Link it to a project to unlock its phases.'}
        </p>
        <form onSubmit={submit} className="mt-4 space-y-4">
          <label className="block">
            <span className={modalLabelClass}>Task title *</span>
            <input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Prepare GFC drawings for Level 2"
              className={`${inputClass} h-10 w-full`}
            />
          </label>
          <label className="block">
            <span className={modalLabelClass}>Description</span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="Scope, references, deliverables…"
              className={`${inputClass} h-auto w-full py-2`}
            />
          </label>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={modalLabelClass}>Project</span>
              <select
                value={projectId}
                onChange={(e) => {
                  setProjectId(e.target.value === '' ? '' : Number(e.target.value));
                  setPhaseId('');
                }}
                className={`${inputClass} h-10 w-full`}
              >
                <option value="">No project</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.code} — {p.name || 'Untitled'}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className={modalLabelClass}>Phase</span>
              <select
                value={phaseId}
                onChange={(e) => setPhaseId(e.target.value === '' ? '' : Number(e.target.value))}
                disabled={projectId === ''}
                className={`${inputClass} h-10 w-full disabled:cursor-not-allowed disabled:bg-surfaceWarm disabled:text-muted`}
              >
                <option value="">
                  {projectId === '' ? 'Select a project first' : 'No phase'}
                </option>
                {phaseOptions.map((ph) => (
                  <option key={ph.id} value={ph.id}>
                    {ph.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={modalLabelClass}>Assignee</span>
              <select
                value={assignee}
                onChange={(e) => setAssignee(e.target.value === '' ? '' : Number(e.target.value))}
                className={`${inputClass} h-10 w-full`}
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
                value={priority}
                onChange={(e) => setPriority(e.target.value as TaskPriority)}
                className={`${inputClass} h-10 w-full`}
              >
                {TASK_PRIORITY_OPTIONS.map((p) => (
                  <option key={p} value={p}>
                    {p.charAt(0).toUpperCase() + p.slice(1)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <label className="block">
              <span className={modalLabelClass}>Start date</span>
              <DatePicker value={startDate} onChange={setStartDate} className="mt-1" />
            </label>
            <label className="block">
              <span className={modalLabelClass}>Due date</span>
              <DatePicker value={dueDate} onChange={setDueDate} className="mt-1" />
            </label>
            <label className="block">
              <span className={modalLabelClass}>Est. hours</span>
              <input
                type="number"
                min="0"
                value={hours}
                onChange={(e) => setHours(e.target.value)}
                placeholder="0"
                className={`${inputClass} h-10 w-full`}
              />
            </label>
          </div>
          <label className="block">
            <span className={modalLabelClass}>Tags</span>
            <input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="Comma separated — e.g. drawings, client review"
              className={`${inputClass} h-10 w-full`}
            />
          </label>
          {error?.response?.data?.detail && (
            <div className="rounded-md border border-danger/30 bg-dangerSoft px-3 py-2.5 text-sm text-danger">
              {error.response.data.detail}
            </div>
          )}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className={secondaryBtnClass}>
              Cancel
            </button>
            <button type="submit" disabled={pending} className={primaryBtnClass}>
              {pending ? 'Creating…' : 'Create Task'}
            </button>
          </div>
        </form>
      </div>
    </Modal>
  );
}
