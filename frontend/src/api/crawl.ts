import type { Paper } from '../types/paper';
import client, { apiUrl } from './client';

interface CrawlLog {
  id: number;
  started_at: string;
  finished_at: string | null;
  status: string;
  source: string;
  papers_found: number;
  papers_new: number;
  papers_updated: number;
  error_message: string | null;
  trigger_type: string;
}

export interface CrawlEvent {
  type: 'paper_new' | 'complete' | 'error' | 'timeout' | 'status' | 'progress';
  paper?: Paper;
  papers_found?: number;
  papers_new?: number;
  papers_updated?: number;
  message?: string;
  progress?: number;
  running?: boolean;
  source?: string;
  unreachable_sources?: { source: string; reason: string }[];
  unsupported_sources?: string[];
}

export async function triggerCrawl(source = 'all', keywordIds?: number[]): Promise<{ crawl_log_id: number; message: string }> {
  const { data } = await client.post('/crawl', { source, keyword_ids: keywordIds || null });
  return data;
}

export async function streamCrawl(
  source: string,
  keywordIds: number[] | undefined,
  onEvent: (event: CrawlEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const resp = await fetch(apiUrl('/crawl/stream'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, keyword_ids: keywordIds || null }),
    signal,
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || 'Crawl failed');
  }

  const reader = resp.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event: CrawlEvent = JSON.parse(line.slice(6));
            onEvent(event);
            if (event.type === 'complete' || event.type === 'error') {
              return;
            }
          } catch { /* skip malformed JSON */ }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export interface CrawlStatus {
  running: boolean;
  source: string;
  papers_new: number;
  papers_found: number;
  message: string;
  progress: number;
}

export async function fetchCrawlStatus(): Promise<CrawlStatus> {
  const { data } = await client.get('/crawl/status');
  return data;
}

export async function fetchCrawlLogs(page = 1, pageSize = 20): Promise<{ total: number; logs: CrawlLog[] }> {
  const { data } = await client.get('/crawl/logs', { params: { page, page_size: pageSize } });
  return data;
}

export async function fetchSchedule(): Promise<{ running: boolean; daily_crawl: { next_run: string | null } }> {
  const { data } = await client.get('/crawl/schedule');
  return data;
}

export async function updateSchedule(hour: number, minute: number): Promise<{ message: string; next_run: string | null }> {
  const { data } = await client.put('/crawl/schedule', null, { params: { hour, minute } });
  return data;
}
