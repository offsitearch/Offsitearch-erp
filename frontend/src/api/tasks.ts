import { api } from './client';
import type {
  Task,
  TaskBoardData,
  TaskCreateInput,
  TaskPage,
  TaskUpdateInput,
} from '../lib/types';

export interface TaskFilters {
  search?: string;
  project_id?: number;
  assignee?: number;
  status?: string;
  page?: number;
  page_size?: number;
}

export async function getTaskBoard(projectId?: number): Promise<TaskBoardData> {
  const { data } = await api.get<TaskBoardData>('/tasks/board', {
    params: projectId ? { project_id: projectId } : {},
  });
  return data;
}

export async function getTasks(filters: TaskFilters = {}): Promise<TaskPage> {
  const { data } = await api.get<TaskPage>('/tasks', { params: filters });
  return data;
}

export async function getTask(id: number): Promise<Task> {
  const { data } = await api.get<Task>(`/tasks/${id}`);
  return data;
}

export async function createTask(payload: TaskCreateInput): Promise<Task> {
  const { data } = await api.post<Task>('/tasks', payload);
  return data;
}

export async function updateTask(id: number, payload: TaskUpdateInput): Promise<Task> {
  const { data } = await api.patch<Task>(`/tasks/${id}`, payload);
  return data;
}

export async function deleteTask(id: number): Promise<void> {
  await api.delete(`/tasks/${id}`);
}

export async function addChecklistItem(taskId: number, text: string): Promise<void> {
  await api.post(`/tasks/${taskId}/checklist`, { text });
}

export async function toggleChecklistItem(taskId: number, itemId: number): Promise<void> {
  await api.patch(`/tasks/${taskId}/checklist/${itemId}`);
}
