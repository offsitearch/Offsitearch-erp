import { api } from './client';
import type {
  ChangePasswordInput,
  HolidayFull,
  HolidayInput,
  RegeneratedCredentials,
  Setting,
  SettingInput,
  TokenResponse,
  User,
  UserAdmin,
  UserAdminCreateOut,
  UserBrief,
  UserCreateInput,
  UserUpdateInput,
} from '../lib/types';

/** Fetches settings, optionally filtered by group. */
export async function getSettings(group?: string): Promise<Setting[]> {
  const { data } = await api.get<Setting[]>('/settings', { params: group ? { group } : undefined });
  return data;
}

/** Creates or updates multiple settings at once. */
export async function upsertSettings(payload: SettingInput[]): Promise<Setting[]> {
  const { data } = await api.put<Setting[]>('/settings', payload);
  return data;
}

/** Deletes a setting by group and key. */
export async function deleteSetting(group: string, key: string): Promise<void> {
  await api.delete(`/settings/${group}/${key}`);
}

/** Fetches all company holidays. */
export async function getHolidays(): Promise<HolidayFull[]> {
  const { data } = await api.get<HolidayFull[]>('/holidays');
  return data;
}

/** Creates a new holiday. */
export async function createHoliday(payload: HolidayInput): Promise<HolidayFull> {
  const { data } = await api.post<HolidayFull>('/holidays', payload);
  return data;
}

/** Updates an existing holiday. */
export async function updateHoliday(id: number, payload: Partial<HolidayInput>): Promise<HolidayFull> {
  const { data } = await api.patch<HolidayFull>(`/holidays/${id}`, payload);
  return data;
}

/** Deletes a holiday by ID. */
export async function deleteHoliday(id: number): Promise<void> {
  await api.delete(`/holidays/${id}`);
}

/** Fetches a list of users with optional filters. */
export async function getUsers(params: { department_id?: number; active_only?: boolean } = {}): Promise<UserBrief[]> {
  const { data } = await api.get<UserBrief[]>('/users', { params });
  return data;
}

/** Creates a new user account. */
export async function createUser(payload: UserCreateInput): Promise<UserAdminCreateOut> {
  const { data } = await api.post<UserAdminCreateOut>('/users', payload);
  return data;
}

/** Updates a user account by ID. */
export async function updateUser(id: number, payload: UserUpdateInput): Promise<UserAdmin> {
  const { data } = await api.patch<UserAdmin>(`/users/${id}`, payload);
  return data;
}

/** Changes the current user's password; returns a fresh token pair. */
export async function changePassword(payload: ChangePasswordInput): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/auth/change-password', payload);
  return data;
}

/** Issues a new one-time password for a user (executives only). */
export async function regeneratePassword(id: number): Promise<RegeneratedCredentials> {
  const { data } = await api.post<RegeneratedCredentials>(`/users/${id}/regenerate-password`);
  return data;
}

export type { User, UserBrief };
