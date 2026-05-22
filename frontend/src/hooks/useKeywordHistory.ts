import { useState, useCallback } from 'react';

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

  const addToHistory = useCallback((text: string) => {
    setHistory(prev => {
      const next = prev.filter(e => e.text !== text);
      next.unshift({ text, addedAt: new Date().toISOString() });
      const trimmed = next.slice(0, MAX_HISTORY);
      saveHistory(trimmed);
      return trimmed;
    });
  }, []);

  const removeFromHistory = useCallback((text: string) => {
    setHistory(prev => {
      const next = prev.filter(e => e.text !== text);
      saveHistory(next);
      return next;
    });
  }, []);

  const clearHistory = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setHistory([]);
  }, []);

  return { history, addToHistory, removeFromHistory, clearHistory };
}
