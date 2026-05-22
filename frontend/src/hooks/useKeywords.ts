import { useState, useEffect, useCallback } from 'react';
import type { Keyword } from '../types/keyword';
import { fetchKeywords, createKeyword, updateKeyword, deleteKeyword } from '../api/keywords';

export function useKeywords() {
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchKeywords();
      setKeywords(data);
    } catch (err: any) {
      setError(err?.message || '加载关键词失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const add = useCallback(async (text: string, source = 'all') => {
    const kw = await createKeyword(text, source);
    setKeywords(prev => [...prev, kw]);
    return kw;
  }, []);

  const update = useCallback(async (id: number, updates: Partial<Keyword>) => {
    const kw = await updateKeyword(id, updates);
    setKeywords(prev => prev.map(k => k.id === id ? kw : k));
    return kw;
  }, []);

  const remove = useCallback(async (id: number) => {
    await deleteKeyword(id);
    setKeywords(prev => prev.filter(k => k.id !== id));
  }, []);

  return { keywords, loading, error, add, update, remove, refresh: load };
}
