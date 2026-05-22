import { useState, useCallback, useEffect, useRef } from 'react';
import FilterPanel from '../components/filters/FilterPanel';
import PaperCardGrid from '../components/papers/PaperCardGrid';
import PaperDetailModal from '../components/papers/PaperDetailModal';
import PaperListPagination from '../components/papers/PaperListPagination';
import PaperCardSkeleton from '../components/papers/PaperCardSkeleton';
import BackToTop from '../components/common/BackToTop';
import SummaryProgressBar from '../components/common/SummaryProgressBar';
import ErrorMessage from '../components/common/ErrorMessage';
import EmptyState from '../components/common/EmptyState';
import CrawlButton from '../components/crawl/CrawlButton';
import SortRefreshNotice, { isSortNoticeDismissed } from '../components/crawl/SortRefreshNotice';
import { usePapers } from '../hooks/usePapers';
import { useReadPapers } from '../hooks/useReadPapers';
import { useKeywords } from '../hooks/useKeywords';
import { useGlobalCrawl } from '../contexts/CrawlContext';
import { getExportUrl } from '../api/papers';
import client from '../api/client';
import { toFilterParams } from '../hooks/usePapers';
import { useAppConfig } from '../contexts/ConfigContext';
import type { FilterState } from '../types/filters';

const BASE_FILTERS: FilterState = {
  sciZones: [],
  sources: [],
  keywordIds: [],
  dateFrom: null,
  dateTo: null,
  citationsMin: null,
  searchQuery: '',
  hasSummary: null,
  starred: null,
  sortBy: 'sci_zone',
  sortOrder: 'asc',
};

export default function HomePage() {
  const { keywords } = useKeywords();
  const { config } = useAppConfig();
  const aiAvailable = !!config?.ai_available;
  const activeKeywordIds = keywords.filter(k => k.is_active).map(k => k.id);
  const prevActiveIds = useRef<number[]>(activeKeywordIds);

  const [filters, setFilters] = useState<FilterState>({
    ...BASE_FILTERS,
    keywordIds: activeKeywordIds,
  });

  // When active keywords change, update the baseline keywordIds
  useEffect(() => {
    const newIds = activeKeywordIds;
    const oldIds = prevActiveIds.current;
    const changed = newIds.length !== oldIds.length || !newIds.every(id => oldIds.includes(id));
    if (changed) {
      prevActiveIds.current = newIds;
      setFilters(prev => ({ ...prev, keywordIds: newIds }));
    }
  }, [activeKeywordIds.join(',')]);

  const { papers, total, page, loading, error, stats, summarizingId, goToPage, handleToggleStar, handleSummarize, refresh, updatePaperLocally } = usePapers(filters);
  const { crawling, startCrawl, crawlVersion, clearNewPapers, unreachableSources, clearUnreachable } = useGlobalCrawl();
  const { isRead, markRead } = useReadPapers();
  const [detailId, setDetailId] = useState<number | null>(null);
  const gridRef = useRef<HTMLDivElement>(null);
  const highlightIds = useRef<Set<number>>(new Set()).current;
  const [showSortNotice, setShowSortNotice] = useState(false);

  // Scroll to top when page changes or filters trigger a reload
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [page]);

  // Scroll to top when filters change (loading transitions from false→true with existing papers)
  const prevLoadingRef = useRef(loading);
  useEffect(() => {
    if (loading && !prevLoadingRef.current && papers.length > 0) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    prevLoadingRef.current = loading;
  }, [loading, papers.length]);

  // Auto-refresh papers when a crawl completes (crawlVersion increments)
  const prevCrawlVersion = useRef(crawlVersion);
  useEffect(() => {
    if (crawlVersion !== prevCrawlVersion.current) {
      prevCrawlVersion.current = crawlVersion;
      clearNewPapers();
      goToPage(1);
      // Show sort-notice if not permanently dismissed
      if (!isSortNoticeDismissed()) {
        setShowSortNotice(true);
      }
    }
  }, [crawlVersion, clearNewPapers, goToPage]);

  // Auto-clear unreachable sources after 15s
  useEffect(() => {
    if (unreachableSources.length === 0) return;
    const timer = setTimeout(() => clearUnreachable(), 15000);
    return () => clearTimeout(timer);
  }, [unreachableSources, clearUnreachable]);

  // Poll for background summary progress every 10s, refresh list when new summaries complete
  const lastSummarizedRef = useRef(0);
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const { data: progress } = await client.get('/summary/progress');
        if (progress.total_summarized !== lastSummarizedRef.current) {
          lastSummarizedRef.current = progress.total_summarized;
          refresh();
        }
      } catch { /* ignore polling errors */ }
    }, 10_000);
    return () => clearInterval(interval);
  }, [refresh]);

  // Initialize lastSummarizedRef when stats first load
  useEffect(() => {
    if (stats && stats.with_summary > 0 && lastSummarizedRef.current === 0) {
      lastSummarizedRef.current = stats.with_summary;
    }
  }, [stats]);

  const onViewDetail = useCallback((id: number) => {
    markRead(id);
    setDetailId(id);
  }, [markRead]);
  const onCloseDetail = useCallback(() => setDetailId(null), []);

  const handleReset = useCallback((newFilters: FilterState) => {
    setFilters({ ...newFilters, keywordIds: activeKeywordIds });
  }, [activeKeywordIds]);

  const onKeywordFilter = useCallback((keywordId: number) => {
    setFilters(prev => ({
      ...prev,
      keywordIds: prev.keywordIds.includes(keywordId)
        ? prev.keywordIds.filter(id => id !== keywordId)
        : [keywordId],
    }));
  }, []);
  const onSummaryDone = useCallback((paperId: number) => {
    updatePaperLocally(paperId, { has_summary: true, summary_status: 'completed' });
  }, [updatePaperLocally]);
  const onSummarize = useCallback(async (id: number) => {
    await handleSummarize(id);
    onSummaryDone(id);
  }, [handleSummarize, onSummaryDone]);

  return (
    <div className="flex gap-6 p-6 max-w-7xl mx-auto">
      <FilterPanel filters={filters} onChange={setFilters} onReset={handleReset} activeKeywordIds={activeKeywordIds} />

      <div className="flex-1 min-w-0">
        {/* Stats Bar */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3 text-sm text-gray-500 flex-wrap">
            {stats?.by_zone && (
              <>
                {stats.by_zone.Q1 && <span className="text-green-600 font-medium">· Q1: {stats.by_zone.Q1}</span>}
                {stats.by_zone.Q2 && <span className="text-blue-600 font-medium">· Q2: {stats.by_zone.Q2}</span>}
                {stats.by_zone.Q3 && <span className="text-yellow-600 font-medium">· Q3: {stats.by_zone.Q3}</span>}
                {stats.by_zone.Q4 && <span className="text-red-600 font-medium">· Q4: {stats.by_zone.Q4}</span>}
              </>
            )}
            {loading && <span className="text-indigo-500">加载中...</span>}
          </div>
          <div className="flex items-center gap-2">
            {unreachableSources.length > 0 && (
              <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-1.5 flex items-center gap-1.5">
                <span>⚠️ 不可达: {unreachableSources.map(s => s.source).join(', ')}</span>
                <button onClick={clearUnreachable} className="text-amber-400 hover:text-amber-600 ml-1">&times;</button>
              </div>
            )}
            <a
              href={getExportUrl(toFilterParams(filters, 1))}
              className="text-xs px-3 py-1.5 rounded-md bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
              download
            >
              导出 CSV
            </a>
            <CrawlButton crawling={crawling} onClick={() => startCrawl()} />
          </div>
        </div>

        <SummaryProgressBar />

        {/* Content */}
        {error ? (
          <ErrorMessage message={error} />
        ) : (loading || crawling) && papers.length === 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => <PaperCardSkeleton key={i} />)}
          </div>
        ) : papers.length === 0 ? (
          activeKeywordIds.length === 0 ? (
            <EmptyState
              icon="🔍"
              title="尚未添加关键词"
              description="请先添加关键词并触发爬取来收集论文"
            />
          ) : stats && stats.total > 0 ? (
            <EmptyState
              icon="🔎"
              title="筛选结果为空"
              description="当前筛选条件下没有匹配的论文，请尝试调整筛选条件"
              action={
                <button
                  onClick={() => setFilters({ ...BASE_FILTERS, keywordIds: activeKeywordIds })}
                  className="text-sm px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                >
                  重置筛选
                </button>
              }
            />
          ) : (
            <EmptyState
              icon="📄"
              title="暂无论文"
              description="已添加关键词但还没有论文数据，请点击「立即爬取」"
            />
          )
        ) : (
          <>
            <div ref={gridRef}>
              <PaperCardGrid
              papers={papers}
              isRead={isRead}
              onToggleStar={handleToggleStar}
              onViewDetail={onViewDetail}
              onSummarize={onSummarize}
              onKeywordFilter={onKeywordFilter}
              summarizingId={summarizingId}
              highlightIds={highlightIds}
              aiAvailable={aiAvailable}
            />
            </div>
            <PaperListPagination
              page={page}
              total={total}
              onChange={goToPage}
            />
          </>
        )}

        {/* Detail Modal */}
        <PaperDetailModal
          paperId={detailId}
          onClose={onCloseDetail}
          onSummaryDone={onSummaryDone}
          aiAvailable={aiAvailable}
          key={detailId}
        />

        <SortRefreshNotice visible={showSortNotice} onClose={() => setShowSortNotice(false)} />
        <BackToTop />
      </div>
    </div>
  );
}
