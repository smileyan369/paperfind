import client from './client';
import type { Keyword } from '../types/keyword';

export async function fetchKeywords(): Promise<Keyword[]> {
  const { data } = await client.get('/keywords');
  return data;
}

export async function createKeyword(text: string, source = 'all'): Promise<Keyword> {
  const { data } = await client.post('/keywords', { text, source });
  return data;
}

export async function updateKeyword(id: number, updates: Partial<Keyword>): Promise<Keyword> {
  const { data } = await client.put(`/keywords/${id}`, updates);
  return data;
}

export async function deleteKeyword(id: number): Promise<void> {
  await client.delete(`/keywords/${id}`);
}

export async function importKeywords(keywords: string, source = 'all'): Promise<{ added: number; skipped: number }> {
  const { data } = await client.post('/keywords/import', { keywords, source });
  return data;
}
