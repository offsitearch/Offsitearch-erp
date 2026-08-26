import { UPLOAD_TIMEOUT_MS, api } from './client';
import type { SiteVisit, SiteVisitInput, SiteVisitPhoto, SiteVisitStatus } from '../lib/types';

/** Fetches a filtered list of site visits. */
export async function getSiteVisits(params: { project_id?: number; status?: SiteVisitStatus } = {}): Promise<SiteVisit[]> {
  const { data } = await api.get<{ items: SiteVisit[] }>('/site-visits', { params });
  return data.items ?? [];
}

/** Creates a new site visit record. */
export async function createSiteVisit(payload: SiteVisitInput): Promise<SiteVisit> {
  const { data } = await api.post<SiteVisit>('/site-visits', payload);
  return data;
}

/** Updates an existing site visit record. */
export async function updateSiteVisit(id: number, payload: Partial<SiteVisitInput>): Promise<SiteVisit> {
  const { data } = await api.patch<SiteVisit>(`/site-visits/${id}`, payload);
  return data;
}

/** Deletes a site visit by ID. */
export async function deleteSiteVisit(id: number): Promise<void> {
  await api.delete(`/site-visits/${id}`);
}

/** Uploads a photo for a site visit. */
export async function uploadSiteVisitPhoto(
  id: number,
  file: File,
  caption?: string,
): Promise<SiteVisitPhoto> {
  const form = new FormData();
  form.append('file', file);
  if (caption) form.append('caption', caption);
  const { data } = await api.post<SiteVisitPhoto>(
    `/site-visits/${id}/photos`,
    form,
    { timeout: UPLOAD_TIMEOUT_MS },
  );
  return data;
}

/** Fetches a site visit photo as a blob. */
export async function getSiteVisitPhoto(visitId: number, photoId: number): Promise<Blob> {
  const { data } = await api.get<Blob>(`/site-visits/${visitId}/photos/${photoId}`, {
    responseType: 'blob',
  });
  return data;
}

/** Deletes a photo from a site visit. */
export async function deleteSiteVisitPhoto(visitId: number, photoId: number): Promise<void> {
  await api.delete(`/site-visits/${visitId}/photos/${photoId}`);
}

/** Returns the URL for downloading a site visit report. */
export function siteVisitReportUrl(id: number): string {
  const base = api.defaults.baseURL || '/api/v1';
  return `${base}/site-visits/${id}/report`;
}
