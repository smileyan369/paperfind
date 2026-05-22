import { useState, useEffect, useCallback } from 'react';
import { fetchCrawlLogs, fetchSchedule, updateSchedule } from '../api/crawl';

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

export function useCrawl() {
  const [logs, setLogs] = useState<CrawlLog[]>([]);
  const [logsTotal, setLogsTotal] = useState(0);
  const [schedule, setSchedule] = useState<{ running: boolean; daily_crawl: { next_run: string | null } } | null>(null);

  const loadLogs = useCallback(async (page = 1) => {
    try {
      const data = await fetchCrawlLogs(page);
      setLogs(data.logs);
      setLogsTotal(data.total);
    } catch { console.error('Failed to load crawl logs'); }
  }, []);

  const loadSchedule = useCallback(async () => {
    try {
      const s = await fetchSchedule();
      setSchedule(s);
    } catch { console.error('Failed to load schedule'); }
  }, []);

  useEffect(() => {
    loadLogs();
    loadSchedule();
  }, [loadLogs, loadSchedule]);

  const changeSchedule = useCallback(async (hour: number, minute: number) => {
    const result = await updateSchedule(hour, minute);
    await loadSchedule();
    return result;
  }, [loadSchedule]);

  return { logs, logsTotal, schedule, changeSchedule, refreshLogs: loadLogs };
}
