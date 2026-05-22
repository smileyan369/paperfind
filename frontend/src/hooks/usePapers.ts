import { useState, useEffect, useCallback, useRef } from 'react';
import type { Paper, PaperDetail, PaperFilterParams, PaperStats } from '../types/paper';
import type { FilterState } from '../types/filters';
import { fetchPapers, fetchPaperDetail, toggleStar, fetchPaperStats } from '../api/papers';
import { summarizePaper } from '../api/summary';

export function toFilterParams(filters: FilterState, page: number): PaperFilterParams {
  const params: PaperFilterParams = {
    page,
    page_size: 24,
    sort_by: filters.sortBy,
    sort_order: filters.sortOrder,
  };
  if (filters.sciZones.length > 0) params['sci_zone[]'] = filters.sciZones;
  if (filters.sources.length > 0) params['source[]'] = filters.sources;
  if (filters.keywordIds.length > 0) params['keyword_id[]'] = filters.keywordIds;
  if (filters.dateFrom) params.date_from = filters.dateFrom;
  if (filters.dateTo) params.date_to = filters.dateTo;
  if (filters.citationsMin !== null) params.citations_min = filters.citationsMin;
  if (filters.searchQuery) params.q = filters.searchQuery;
  if (filters.hasSummary !== null) params.has_summary = filters.hasSummary;
  if (filters.starred !== null) params.starred = filters.starred;
  return params;
}

export function usePapers(filters: FilterState) {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<PaperStats | null>(null);
  const [summarizingId, setSummarizingId] = useState<number | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const statsVersionRef = useRef(0);
  const papersVersionRef = useRef(0);

  const loadPapers = useCallback(async (p: number, f: FilterState) => {
    setLoading(true);
    setError(null);
    const version = ++papersVersionRef.current;
    try {
      const res = await fetchPapers(toFilterParams(f, p));
      if (version !== papersVersionRef.current) return;
      setPapers(res.papers);
      setTotal(res.total);
      setPage(res.page);
    } catch (err: any) {
      if (version !== papersVersionRef.current) return;
      setError(err?.message || '加载论文失败');
    } finally {
      if (version === papersVersionRef.current) setLoading(false);
    }
  }, []);

  const loadStats = useCallback(async (f?: FilterState) => {
    try {
      const version = ++statsVersionRef.current;
      const params = f ? toFilterParams(f, 1) : undefined;
      const s = await fetchPaperStats(params);
      if (version !== statsVersionRef.current) return;
      setStats(s);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    loadStats(filters);
  }, [filters, loadStats]);

  const prevFiltersRef = useRef<FilterState | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const prev = prevFiltersRef.current;
    // Immediate fetch for sort/dropdown changes, 300ms debounce for text search
    const searchQueryChanged = prev && prev.searchQuery !== filters.searchQuery;
    prevFiltersRef.current = { ...filters };

    if (!searchQueryChanged) {
      loadPapers(1, filters);
    } else {
      debounceRef.current = setTimeout(() => {
        loadPapers(1, filters);
      }, 300);
    }
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [filters, loadPapers]);

  const goToPage = useCallback((p: number) => {
    loadPapers(p, filters);
    loadStats(filters);
  }, [filters, loadPapers, loadStats]);

  const handleToggleStar = useCallback(async (id: number, starred: boolean) => {
    try {
      await toggleStar(id, starred);
      setPapers(prev => prev.map(p => p.id === id ? { ...p, is_starred: starred } : p));
    } catch { console.error('Failed to toggle star for paper', id); }
  }, []);

  const handleSummarize = useCallback(async (id: number) => {
    setSummarizingId(id);
    try {
      await summarizePaper(id);
      setPapers(prev => prev.map(p => p.id === id ? { ...p, has_summary: true, summary_status: 'completed' } : p));
    } catch { console.error('Failed to summarize paper', id); }
    finally { setSummarizingId(null); }
  }, []);

  const getDetail = useCallback(async (id: number): Promise<PaperDetail | null> => {
    try {
      return await fetchPaperDetail(id);
    } catch { return null; }
  }, []);

  const updatePaperLocally = useCallback((id: number, updates: Partial<Paper>) => {
    setPapers(prev => prev.map(p => p.id === id ? { ...p, ...updates } : p));
  }, []);

  const refresh = useCallback(() => {
    loadPapers(page, filters);
    loadStats(filters);
  }, [filters, loadPapers, loadStats, page]);

  return {
    papers, total, page, loading, error, stats,
    summarizingId, goToPage, handleToggleStar, handleSummarize, getDetail,
    refresh,
    updatePaperLocally,
  };
}
