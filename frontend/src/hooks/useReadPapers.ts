import { useState, useCallback } from 'react';

const STORAGE_KEY = 'read_paper_ids';

function loadReadIds(): Set<number> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    return new Set(JSON.parse(raw) as number[]);
  } catch {
    return new Set();
  }
}

function saveReadIds(ids: Set<number>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...ids]));
}

export function useReadPapers() {
  const [readIds, setReadIds] = useState<Set<number>>(loadReadIds);

  const markRead = useCallback((id: number) => {
    setReadIds(prev => {
      if (prev.has(id)) return prev;
      const next = new Set(prev);
      next.add(id);
      saveReadIds(next);
      return next;
    });
  }, []);

  const isRead = useCallback((id: number) => readIds.has(id), [readIds]);

  const unreadCount = (total: number) => total - readIds.size;

  const clearRead = useCallback(() => {
    setReadIds(new Set());
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return { readIds, markRead, isRead, unreadCount, clearRead };
}
