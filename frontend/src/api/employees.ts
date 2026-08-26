import { UPLOAD_TIMEOUT_MS, api } from './client';
import type {
  AttendanceSummary,
  Department,
  EmployeeCreateOut,
  EmployeeDocument,
  EmployeePage,
  EmployeeProfile,
  LeaveRecord,
  OrgChartNode,
  OrgLevel,
  SalaryRecord,
} from '../lib/types';

export interface CreateEmployeeInput {
  name: string;
  contact_email?: string;
  employee_id?: string;
  phone?: string;
  department_id?: number | null;
  org_level_id?: number | null;
  designation?: string;
  reporting_to_id?: number | null;
  date_of_joining?: string;
  gender?: string;
  employment_type?: string;
}

export interface UpdateEmployeeInput {
  name?: string;
  contact_email?: string;
  employee_id?: string;
  phone?: string;
  department_id?: number | null;
  /** Send 0 to clear the level, a level id to set it; omit to leave unchanged. */
  org_level_id?: number | null;
  designation?: string;
  reporting_to_id?: number | null;
  date_of_joining?: string;
  date_of_birth?: string;
  gender?: string;
  blood_group?: string;
  address?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  skills?: string[];
  employment_type?: string;
  is_active?: boolean;
}

export interface SalaryInput {
  ctc_annual?: string;
  basic?: string;
  hra?: string;
  special_allowance?: string;
  pf_deduction?: string;
  bank_name?: string;
  account_number?: string;
  ifsc_code?: string;
  effective_from?: string;
}

/** Fetches a paginated, filterable list of employees. */
export async function getEmployees(params: {
  search?: string;
  department_id?: number;
  skill?: string;
  active_only?: boolean;
  inactive_only?: boolean;
  page?: number;
  page_size?: number;
}): Promise<EmployeePage> {
  const { data } = await api.get<EmployeePage>('/employees', { params });
  return data;
}

/** Returns a list of all unique employee skills. */
export async function getEmployeeSkills(): Promise<string[]> {
  const { data } = await api.get<string[]>('/employees/skills');
  return data;
}

/** Fetches a single employee's full profile by ID. */
export async function getEmployee(id: number): Promise<EmployeeProfile> {
  const { data } = await api.get<EmployeeProfile>(`/employees/${id}`);
  return data;
}

/** Creates a new employee record. */
export async function createEmployee(payload: CreateEmployeeInput): Promise<EmployeeCreateOut> {
  const { data } = await api.post<EmployeeCreateOut>('/employees', payload);
  return data;
}

/** Updates an existing employee's details. */
export async function updateEmployee(
  id: number,
  payload: UpdateEmployeeInput,
): Promise<EmployeeProfile> {
  const { data } = await api.patch<EmployeeProfile>(`/employees/${id}`, payload);
  return data;
}

/** Soft-deactivates an employee by ID. */
export async function deactivateEmployee(id: number): Promise<void> {
  await api.delete(`/employees/${id}`);
}

/** Permanently deletes an employee and all personal data (L0 only, irreversible). */
export async function purgeEmployee(id: number): Promise<Record<string, unknown>> {
  const { data } = await api.post(`/employees/${id}/purge`);
  return data as Record<string, unknown>;
}

/** Fetches the organization chart hierarchy. */
export async function getOrgChart(): Promise<OrgChartNode[]> {
  const { data } = await api.get<OrgChartNode[]>('/employees/org-chart');
  return data;
}

/** Fetches the organizational seniority levels (L1–L6), ordered by rank. */
export async function getOrgLevels(): Promise<OrgLevel[]> {
  const { data } = await api.get<OrgLevel[]>('/org-levels');
  return data;
}

/** Suggested designations grouped by org level code, e.g. { L3: ['Project Manager', …] }. */
export async function getDesignationCatalog(): Promise<Record<string, string[]>> {
  const { data } = await api.get<Record<string, string[]>>('/employees/designations');
  return data;
}

/** Suggested designations grouped by department name. */
export async function getDepartmentDesignations(): Promise<Record<string, string[]>> {
  const { data } = await api.get<Record<string, string[]>>('/employees/department-designations');
  return data;
}

/** Fetches an employee's attendance summary for a given month and year. */
export async function getEmployeeAttendanceSummary(
  id: number,
  month?: number,
  year?: number,
): Promise<AttendanceSummary> {
  const { data } = await api.get<AttendanceSummary>(`/employees/${id}/attendance-summary`, {
    params: { month, year },
  });
  return data;
}

/** Fetches salary details for an employee. */
export async function getEmployeeSalary(id: number): Promise<SalaryRecord> {
  const { data } = await api.get<SalaryRecord>(`/employees/${id}/salary`);
  return data;
}

/** Creates or updates salary details for an employee. */
export async function saveEmployeeSalary(id: number, payload: SalaryInput): Promise<SalaryRecord> {
  const { data } = await api.put<SalaryRecord>(`/employees/${id}/salary`, payload);
  return data;
}

/** Fetches all documents uploaded for an employee. */
export async function getEmployeeDocuments(id: number): Promise<EmployeeDocument[]> {
  const { data } = await api.get<{ items: EmployeeDocument[] }>(`/employees/${id}/documents`);
  return data.items ?? [];
}

/** Uploads a document file for an employee. */
export async function uploadEmployeeDocument(
  id: number,
  file: File,
  docType: string,
): Promise<EmployeeDocument> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<EmployeeDocument>(`/employees/${id}/documents`, form, {
    params: { doc_type: docType },
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: UPLOAD_TIMEOUT_MS,
  });
  return data;
}

/** Downloads an employee document as a blob. */
export async function downloadEmployeeDocument(id: number, docId: number): Promise<void> {
  const response = await api.get(`/employees/${id}/documents/${docId}/download`, {
    responseType: 'blob',
  });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
}

/** Deletes a specific document from an employee's records. */
export async function deleteEmployeeDocument(userId: number, docId: number): Promise<void> {
  await api.delete(`/employees/${userId}/documents/${docId}`);
}

/** Fetches all leave records for an employee. */
export async function getEmployeeLeaves(id: number): Promise<LeaveRecord[]> {
  const { data } = await api.get<{ items: LeaveRecord[] }>(`/employees/${id}/leaves`);
  return data.items ?? [];
}

/** Fetches all departments. */
export async function getDepartments(): Promise<Department[]> {
  const { data } = await api.get<Department[]>('/departments');
  return data;
}

/** Creates a new department. */
export async function createDepartment(payload: {
  name: string;
  head_id?: number | null;
  description?: string;
}): Promise<Department> {
  const { data } = await api.post<Department>('/departments', payload);
  return data;
}

/** Updates an existing department. */
export async function updateDepartment(
  id: number,
  payload: { name?: string; head_id?: number | null; description?: string; is_active?: boolean },
): Promise<Department> {
  const { data } = await api.patch<Department>(`/departments/${id}`, payload);
  return data;
}

/** Deletes a department by ID. */
export async function deleteDepartment(id: number): Promise<void> {
  await api.delete(`/departments/${id}`);
}
