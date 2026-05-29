import { useEffect, useState, useCallback } from 'react';
import { fetchKeywordHistory, saveKeywordHistory } from '../api/config';

const STORAGE_KEY = 'keyword_history';
const MAX_HISTORY = 15;

export interface HistoryEntry {
  text: string;
  addedAt: string;
}

function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveHistory(entries: HistoryEntry[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(0, MAX_HISTORY)));
}

export function useKeywordHistory() {
  const [history, setHistory] = useState<HistoryEntry[]>(loadHistory);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const remote = await fetchKeywordHistory();
        if (cancelled) return;
        const normalized = remote.map(item => ({ text: item.text, addedAt: item.added_at }));
        if (normalized.length > 0) {
          setHistory(normalized);
          saveHistory(normalized);
        } else {
          const local = loadHistory();
          if (local.length > 0) {
            await saveKeywordHistory(local.map(item => ({ text: item.text, added_at: item.addedAt })));
          }
        }
      } catch {
        // Keep localStorage as a fallback when the backend is not ready.
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const persist = useCallback((entries: HistoryEntry[]) => {
    saveHistory(entries);
    saveKeywordHistory(entries.map(item => ({ text: item.text, added_at: item.addedAt }))).catch(() => {});
  }, []);

  const addToHistory = useCallback((text: string) => {
    setHistory(prev => {
      const next = prev.filter(e => e.text !== text);
      next.unshift({ text, addedAt: new Date().toISOString() });
      const trimmed = next.slice(0, MAX_HISTORY);
      persist(trimmed);
      return trimmed;
    });
  }, [persist]);

  const removeFromHistory = useCallback((text: string) => {
    setHistory(prev => {
      const next = prev.filter(e => e.text !== text);
      persist(next);
      return next;
    });
  }, [persist]);

  const clearHistory = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    saveKeywordHistory([]).catch(() => {});
    setHistory([]);
  }, []);

  return { history, addToHistory, removeFromHistory, clearHistory };
}
