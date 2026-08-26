import { api } from './client';
import type {
  ClientCreateInput,
  ClientDetail,
  ClientPage,
  ClientProfile,
  Communication,
  CommunicationInput,
} from '../lib/types';

export interface ClientFilters {
  search?: string;
  client_type?: string;
  page?: number;
  page_size?: number;
}

export async function getClients(filters: ClientFilters = {}): Promise<ClientPage> {
  const { data } = await api.get<ClientPage>('/clients', { params: filters });
  return data;
}

export async function createClient(payload: ClientCreateInput): Promise<ClientDetail> {
  const { data } = await api.post<ClientDetail>('/clients', payload);
  return data;
}

export async function getClientProfile(id: number): Promise<ClientProfile> {
  const { data } = await api.get<ClientProfile>(`/clients/${id}`);
  return data;
}

export async function updateClient(id: number, payload: Partial<ClientCreateInput>): Promise<ClientDetail> {
  const { data } = await api.patch<ClientDetail>(`/clients/${id}`, payload);
  return data;
}

export async function deleteClient(id: number): Promise<void> {
  await api.delete(`/clients/${id}`);
}

export async function getCommunications(clientId: number): Promise<Communication[]> {
  const { data } = await api.get<Communication[]>(`/clients/${clientId}/communications`);
  return data;
}

export async function addCommunication(
  clientId: number,
  payload: CommunicationInput,
): Promise<Communication> {
  const { data } = await api.post<Communication>(`/clients/${clientId}/communications`, payload);
  return data;
}
