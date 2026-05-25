import { createContext, useContext, useState, useCallback, useRef, useEffect, type ReactNode } from 'react';
import type { Paper } from '../types/paper';
import { streamCrawl, fetchCrawlStatus, type CrawlEvent } from '../api/crawl';

interface UnreachableInfo {
  source: string;
  reason: string;
}

interface CrawlState {
  crawling: boolean;
  crawlMessage: string | null;
  crawlProgress: number;
  crawlVersion: number;
  newPapers: Paper[];
  unreachableSources: UnreachableInfo[];
  startCrawl: (source?: string, keywordIds?: number[]) => Promise<void>;
  clearNewPapers: () => void;
  clearUnreachable: () => void;
}

const CrawlContext = createContext<CrawlState | null>(null);

export function CrawlProvider({ children }: { children: ReactNode }) {
  const [crawling, setCrawling] = useState(false);
  const [crawlMessage, setCrawlMessage] = useState<string | null>(null);
  const [crawlProgress, setCrawlProgress] = useState(0);
  const [crawlVersion, setCrawlVersion] = useState(0);
  const [newPapers, setNewPapers] = useState<Paper[]>([]);
  const [unreachableSources, setUnreachableSources] = useState<UnreachableInfo[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearNewPapers = useCallback(() => setNewPapers([]), []);
  const clearUnreachable = useCallback(() => setUnreachableSources([]), []);

  const startCrawl = useCallback(async (source = 'all', keywordIds?: number[]) => {
    // Cancel any in-progress stream subscription
    if (abortRef.current) {
      abortRef.current.abort();
    }
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    const controller = new AbortController();
    abortRef.current = controller;

    setCrawling(true);
    setCrawlProgress(0);
    setCrawlMessage('正在检索...');
    setNewPapers([]);
    setUnreachableSources([]);

    try {
      await streamCrawl(source, keywordIds, (event: CrawlEvent) => {
        if (event.type === 'paper_new' && event.paper) {
          if (typeof event.progress === 'number') setCrawlProgress(event.progress);
          setNewPapers(prev => {
            const next = [...prev, event.paper!];
            setCrawlMessage(`正在检索... (已找到 ${next.length} 篇)`);
            return next;
          });
        } else if (event.type === 'complete') {
          setCrawlProgress(100);
          setCrawlVersion(v => v + 1);
          const newCount = event.papers_new ?? 0;
          if (event.unreachable_sources && event.unreachable_sources.length > 0) {
            setUnreachableSources(event.unreachable_sources);
          }
          if (newCount > 0) {
            setCrawlMessage(`检索完成：新增 ${newCount} 篇`);
          } else {
            setCrawlMessage(event.message || '检索完成，未发现新论文');
          }
          setCrawling(false);
        } else if (event.type === 'status' || event.type === 'progress') {
          if (typeof event.progress === 'number') setCrawlProgress(event.progress);
          if (event.message) setCrawlMessage(event.message);
        } else if (event.type === 'error') {
          if (typeof event.progress === 'number') setCrawlProgress(event.progress);
          setCrawlMessage('检索失败');
          setCrawling(false);
        }
      }, controller.signal);
    } catch {
      if (!controller.signal.aborted) {
        setCrawlMessage('检索失败');
        setCrawling(false);
      }
    }

    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      if (!controller.signal.aborted) {
        setCrawlMessage(null);
      }
    }, 8000);
  }, []);

  // On mount: check if a crawl is already running and reconnect
  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const status = await fetchCrawlStatus();
        if (!status.running || cancelled) return;

        setCrawling(true);
        setCrawlMessage(status.message);
        setCrawlProgress(status.progress ?? 0);
        setNewPapers([]);
        setUnreachableSources([]);

        const controller = new AbortController();
        abortRef.current = controller;

        await streamCrawl('all', undefined, (event: CrawlEvent) => {
          if (cancelled) return;
          if (event.type === 'paper_new' && event.paper) {
            if (typeof event.progress === 'number') setCrawlProgress(event.progress);
            setNewPapers(prev => {
              const next = [...prev, event.paper!];
              setCrawlMessage(`正在检索... (已找到 ${next.length} 篇)`);
              return next;
            });
          } else if (event.type === 'complete') {
            setCrawlProgress(100);
            setCrawlVersion(v => v + 1);
            const newCount = event.papers_new ?? 0;
            if (event.unreachable_sources && event.unreachable_sources.length > 0) {
              setUnreachableSources(event.unreachable_sources);
            }
            setCrawlMessage(newCount > 0 ? `检索完成：新增 ${newCount} 篇` : (event.message || '检索完成'));
            setCrawling(false);
          } else if (event.type === 'status' || event.type === 'progress') {
            if (typeof event.progress === 'number') setCrawlProgress(event.progress);
            if (event.message) setCrawlMessage(event.message);
          } else if (event.type === 'error') {
            if (typeof event.progress === 'number') setCrawlProgress(event.progress);
            setCrawlMessage(event.message || '检索失败');
            setCrawling(false);
          }
        }, controller.signal);
      } catch {
        if (!cancelled) setCrawling(false);
      }
    })();

    return () => { cancelled = true; };
  }, []);

  return (
    <CrawlContext.Provider value={{ crawling, crawlMessage, crawlProgress, crawlVersion, newPapers, unreachableSources, startCrawl, clearNewPapers, clearUnreachable }}>
      {children}
    </CrawlContext.Provider>
  );
}

export function useGlobalCrawl() {
  const ctx = useContext(CrawlContext);
  if (!ctx) throw new Error('useGlobalCrawl must be used within CrawlProvider');
  return ctx;
}
