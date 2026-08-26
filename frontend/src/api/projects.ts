import { api } from './client';
import type {
  PhaseTemplate,
  ProjectCreateInput,
  ProjectDetail,
  ProjectPage,
  ProjectPhase,
  ProjectTeamMember,
  TimelineData,
} from '../lib/types';

export interface ProjectFilters {
  search?: string;
  project_type?: string;
  status?: string;
  client_id?: number;
  lead_id?: number;
  page?: number;
  page_size?: number;
}

/** Fetches a paginated, filterable list of projects. */
export async function getProjects(filters: ProjectFilters = {}): Promise<ProjectPage> {
  const { data } = await api.get<ProjectPage>('/projects', { params: filters });
  return data;
}

/** Unscoped id/name list of active projects — safe for any user's pickers. */
export async function getProjectOptions(): Promise<{ id: number; name: string }[]> {
  const { data } = await api.get<{ id: number; name: string }[]>('/projects/options');
  return data;
}

/** Fetches a single project's full details by ID. */
export async function getProject(id: number): Promise<ProjectDetail> {
  const { data } = await api.get<ProjectDetail>(`/projects/${id}`);
  return data;
}

/** Creates a new project. */
export async function createProject(payload: ProjectCreateInput): Promise<ProjectDetail> {
  const { data } = await api.post<ProjectDetail>('/projects', payload);
  return data;
}

/** Updates an existing project. */
export async function updateProject(id: number, payload: Partial<ProjectCreateInput>): Promise<ProjectDetail> {
  const { data } = await api.patch<ProjectDetail>(`/projects/${id}`, payload);
  return data;
}

/** Fetches the timeline/Gantt data for a project. */
export async function getProjectTimeline(id: number): Promise<TimelineData> {
  const { data } = await api.get<TimelineData>(`/projects/${id}/timeline`);
  return data;
}

/** Fetches available phase templates. */
export async function getPhaseTemplates(): Promise<PhaseTemplate[]> {
  const { data } = await api.get<PhaseTemplate[]>('/projects/templates');
  return data;
}

/** Adds a team member to a project. */
export async function addTeamMember(
  projectId: number,
  userId: number,
  role?: string | null,
): Promise<ProjectTeamMember> {
  const { data } = await api.post<ProjectTeamMember>(`/projects/${projectId}/team`, {
    user_id: userId,
    role,
  });
  return data;
}

/** Removes a team member from a project. */
export async function removeTeamMember(projectId: number, userId: number): Promise<void> {
  await api.delete(`/projects/${projectId}/team/${userId}`);
}

/** Deletes a project by ID. */
export async function deleteProject(id: number): Promise<void> {
  await api.delete(`/projects/${id}`);
}

/** Updates a project phase's details. */
export async function updatePhase(
  projectId: number,
  phaseId: number,
  payload: { name?: string; status?: string; completion_pct?: number | string; start_date?: string | null; end_date?: string | null; studio_fee?: number | null },
): Promise<ProjectPhase> {
  const { data } = await api.patch<ProjectPhase>(`/projects/${projectId}/phases/${phaseId}`, payload);
  return data;
}

/** Adds a new phase to a project. */
export async function addPhase(
  projectId: number,
  payload: { name: string; start_date?: string | null; end_date?: string | null; status?: string; completion_pct?: number; studio_fee?: number | null },
): Promise<ProjectPhase> {
  const { data } = await api.post<ProjectPhase>(`/projects/${projectId}/phases`, payload);
  return data;
}

/** Deletes a project phase. */
export async function deletePhase(projectId: number, phaseId: number): Promise<void> {
  await api.delete(`/projects/${projectId}/phases/${phaseId}`);
}
