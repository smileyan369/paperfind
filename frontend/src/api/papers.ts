import client from './client';
import type { Paper, PaperDetail, PaperFilterParams, PaperListResponse, PaperStats } from '../types/paper';

export async function fetchPapers(params: PaperFilterParams): Promise<PaperListResponse> {
  const { data } = await client.get('/papers', { params });
  return data;
}

export async function fetchPaperDetail(id: number): Promise<PaperDetail> {
  const { data } = await client.get(`/papers/${id}`);
  return data;
}

export async function toggleStar(id: number, starred: boolean): Promise<Paper> {
  const { data } = await client.patch(`/papers/${id}/star`, { starred });
  return data;
}

export async function deletePaper(id: number): Promise<void> {
  await client.delete(`/papers/${id}`);
}

export async function fetchPaperStats(params?: Record<string, any>): Promise<PaperStats> {
  const { data } = await client.get('/papers/stats', { params });
  return data;
}

export interface DailyDigestItem {
  id?: number;
  title: string;
  url?: string | null;
  source: string;
  date?: string | null;
  summary?: string | null;
}

export async function fetchDailyDigest(limit = 6): Promise<{ items: DailyDigestItem[]; source: string }> {
  const { data } = await client.get('/papers/daily-digest', { params: { limit } });
  return data;
}

export function getExportUrl(params: Record<string, any>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === null || v === undefined || v === '') return;
    if (Array.isArray(v)) {
      v.forEach(item => search.append(k, String(item)));
    } else {
      search.append(k, String(v));
    }
  });
  return `/api/papers/export?${search.toString()}`;
}
