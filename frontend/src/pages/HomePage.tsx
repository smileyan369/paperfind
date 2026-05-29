import { useState, useCallback, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
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
import { usePapers } from '../hooks/usePapers';
import { useReadPapers } from '../hooks/useReadPapers';
import { useKeywords } from '../hooks/useKeywords';
import { useGlobalCrawl } from '../contexts/CrawlContext';
import { fetchDailyDigest, getExportUrl, type DailyDigestItem } from '../api/papers';
import { createKeyword, suggestKeywords } from '../api/keywords';
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

const AI_QUERY_EXAMPLES = [
  '人体行为预测的最新方法',
  '网络安全大模型检测',
  '医学影像报告生成',
  '多模态大模型可解释性',
];

export default function HomePage() {
  const { keywords, refresh: refreshKeywords } = useKeywords();
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
  const { crawling, startCrawl, stopCrawl, crawlVersion, clearNewPapers, unreachableSources, clearUnreachable } = useGlobalCrawl();
  const { isRead, markRead } = useReadPapers();
  const [detailId, setDetailId] = useState<number | null>(null);
  const [aiQuery, setAiQuery] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [suggestSource, setSuggestSource] = useState('');
  const [suggesting, setSuggesting] = useState(false);
  const [suggestMessage, setSuggestMessage] = useState('');
  const [suggestError, setSuggestError] = useState('');
  const [digestItems, setDigestItems] = useState<DailyDigestItem[]>([]);
  const [digestSource, setDigestSource] = useState('');
  const gridRef = useRef<HTMLDivElement>(null);
  const highlightIds = useRef<Set<number>>(new Set()).current;

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

  useEffect(() => {
    let cancelled = false;
    fetchDailyDigest(5)
      .then(data => {
        if (cancelled) return;
        setDigestItems(data.items || []);
        setDigestSource(data.source || '');
      })
      .catch(() => {
        if (!cancelled) {
          setDigestItems([]);
          setDigestSource('');
        }
      });
    return () => { cancelled = true; };
  }, [crawlVersion]);

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
      keywordIds: prev.keywordIds.length === 1 && prev.keywordIds[0] === keywordId
        ? activeKeywordIds
        : [keywordId],
    }));
  }, [activeKeywordIds]);
  const onSummaryDone = useCallback((paperId: number) => {
    updatePaperLocally(paperId, { has_summary: true, summary_status: 'completed' });
  }, [updatePaperLocally]);
  const onSummarize = useCallback(async (id: number) => {
    await handleSummarize(id);
    onSummaryDone(id);
  }, [handleSummarize, onSummaryDone]);

  const handleSuggest = useCallback(async () => {
    const query = aiQuery.trim();
    if (!query) return;
    setSuggesting(true);
    setSuggestMessage('');
    setSuggestError('');
    try {
      const result = await suggestKeywords(query, 8);
      setSuggestions(result.suggestions);
      setSuggestSource(result.source);
      setSuggestMessage(result.suggestions.length > 0
        ? `已生成 ${result.suggestions.length} 个检索词，可直接加入并检索。`
        : '没有生成可用检索词，请换一种说法再试。'
      );
    } catch {
      setSuggestError('生成失败，请检查后端服务或 API 配置。');
    } finally {
      setSuggesting(false);
    }
  }, [aiQuery]);

  const addSuggestedKeyword = useCallback(async (text: string) => {
    try {
      await createKeyword(text, 'all');
    } catch {
      // Already exists or temporarily unavailable; refresh keeps the UI truthful.
    }
    await refreshKeywords();
  }, [refreshKeywords]);

  const runGeneratedSearch = useCallback(async () => {
    const planned = suggestions.map(item => item.trim()).filter(Boolean);
    if (planned.length === 0) {
      await handleSuggest();
      return;
    }

    setSuggesting(true);
    setSuggestMessage('');
    setSuggestError('');
    try {
      const existingByText = new Map(keywords.map(item => [item.text.toLowerCase(), item.id]));
      const ids: number[] = [];
      for (const text of planned) {
        const existingId = existingByText.get(text.toLowerCase());
        if (existingId) {
          ids.push(existingId);
          continue;
        }
        try {
          const created = await createKeyword(text, 'all');
          ids.push(created.id);
          existingByText.set(text.toLowerCase(), created.id);
        } catch {
          const duplicate = keywords.find(item => item.text.toLowerCase() === text.toLowerCase());
          if (duplicate) ids.push(duplicate.id);
        }
      }

      await refreshKeywords();
      if (ids.length === 0) {
        setSuggestError('没有成功加入关键词，请稍后重试。');
        return;
      }

      setFilters(prev => ({ ...prev, keywordIds: ids }));
      setSuggestMessage(`已加入 ${ids.length} 个关键词，正在开始检索。`);
      await startCrawl('all', ids);
    } catch {
      setSuggestError('加入关键词或开始检索失败，请稍后重试。');
    } finally {
      setSuggesting(false);
    }
  }, [handleSuggest, keywords, refreshKeywords, startCrawl, suggestions]);

  const profileTerms = (config?.research_profile || '')
    .split(/[,，;；\n]/)
    .map(item => item.trim())
    .filter(Boolean)
    .slice(0, 3);
  const totalZones = stats?.by_zone ? Object.values(stats.by_zone).reduce((a, b) => a + b, 0) : 0;

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <section className="glass-panel rounded-2xl p-5 soft-appear">
        <div className="flex items-start justify-between gap-6">
          <div className="min-w-0">
            <div className="text-xs font-semibold uppercase tracking-[0.22em] text-indigo-500 mb-2">Local Research Agent</div>
            <h1 className="text-2xl font-bold text-slate-950">科研论文工作台</h1>
            <p className="text-sm text-slate-500 mt-1">聚合多源检索、AI 导读、收藏管理和本地数据沉淀。</p>
          </div>
          <div className="grid grid-cols-3 gap-3 shrink-0">
            <div className="premium-card rounded-xl px-4 py-3 min-w-28">
              <div className="text-xs text-slate-500">论文总量</div>
              <div className="text-xl font-bold text-slate-900">{stats?.total ?? '-'}</div>
            </div>
            <div className="premium-card rounded-xl px-4 py-3 min-w-28">
              <div className="text-xs text-slate-500">AI 导读</div>
              <div className="text-xl font-bold text-indigo-700">{stats?.with_summary ?? '-'}</div>
            </div>
            <div className="premium-card rounded-xl px-4 py-3 min-w-28">
              <div className="text-xs text-slate-500">分区论文</div>
              <div className="text-xl font-bold text-cyan-700">{totalZones || '-'}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-[1.35fr_0.65fr] gap-4 items-stretch">
        <div className="premium-card rounded-2xl p-4 h-full flex flex-col">
          <div className="flex items-center justify-between gap-3 mb-3">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">AI 自然语言检索</h2>
              <p className="text-xs text-slate-500 mt-0.5">用一句话描述方向，生成可直接追踪的检索词。</p>
            </div>
            <span className="text-[11px] px-2 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100">
              {suggestSource === 'ai' ? 'AI 规划' : '本地规划'}
            </span>
          </div>
          <div className="flex gap-3 items-stretch flex-1">
            <textarea
              value={aiQuery}
              onChange={e => {
                setAiQuery(e.target.value);
                setSuggestions([]);
                setSuggestMessage('');
                setSuggestError('');
              }}
              onKeyDown={e => {
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                  e.preventDefault();
                  handleSuggest();
                }
              }}
              rows={5}
              placeholder="例如：我想追踪医学影像报告生成里的多模态大模型和临床可解释性"
              className="flex-1 min-h-[150px] px-4 py-3 text-sm rounded-xl border border-slate-200 bg-white/80 focus:outline-none focus:ring-2 focus:ring-indigo-200 resize-none"
            />
            <button
              onClick={suggestions.length > 0 ? runGeneratedSearch : handleSuggest}
              disabled={suggesting || !aiQuery.trim()}
              className="premium-button text-white text-sm font-medium rounded-xl px-5 min-w-[96px] disabled:opacity-50"
            >
              {suggesting ? '处理中' : suggestions.length > 0 ? '加入并检索' : '生成'}
            </button>
          </div>
          {(suggestMessage || suggestError) && (
            <div className={`mt-3 text-xs ${suggestError ? 'text-red-500' : 'text-indigo-600'}`}>
              {suggestError || suggestMessage}
            </div>
          )}
          {suggestions.length > 0 && (
            <div className="mt-4">
              <div className="text-[11px] font-medium text-slate-400 mb-2">待加入检索词</div>
              <div className="flex flex-wrap gap-2">
                {suggestions.map(item => (
                  <button
                    key={item}
                    onClick={() => addSuggestedKeyword(item)}
                    className="text-xs px-2.5 py-1.5 rounded-full bg-white text-slate-700 border border-indigo-100 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
                    title="只加入这个关键词"
                  >
                    + {item}
                  </button>
                ))}
              </div>
            </div>
          )}
          {suggestions.length === 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {AI_QUERY_EXAMPLES.map(item => (
                <button
                  key={item}
                  onClick={() => setAiQuery(item)}
                  className="text-xs px-2.5 py-1.5 rounded-full bg-indigo-50/70 text-slate-600 border border-indigo-100 hover:bg-indigo-100 hover:text-indigo-700 transition-colors"
                >
                  {item}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="premium-card rounded-2xl p-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-slate-900">科研速递</h2>
            {digestSource && <span className="text-[10px] px-2 py-1 rounded-full bg-slate-100 text-slate-500">{digestSource}</span>}
          </div>
          <Link to="/settings" className="text-xs text-slate-500 mt-1 block hover:text-indigo-700 transition-colors">
            {profileTerms.length > 0 ? `围绕档案：${profileTerms.join(' / ')}` : '点击填写研究档案，优先展示与你方向相关的速递。'}
          </Link>
          <div className="mt-4 space-y-2">
            {digestItems.length > 0 ? digestItems.map((item, index) => (
              <button
                key={`${item.title}-${index}`}
                onClick={() => item.id ? onViewDetail(item.id) : item.url ? window.open(item.url, '_blank', 'noopener,noreferrer') : undefined}
                className="w-full text-left text-sm rounded-xl px-2 py-1.5 hover:bg-indigo-50/70 transition-colors"
              >
                <div className="text-slate-700 line-clamp-1">{item.title}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">{item.date || item.source}</div>
              </button>
            )) : (
              <div className="text-sm text-slate-400">爬取后会在这里显示最新研究方向</div>
            )}
          </div>
        </div>
      </section>

      <div className="flex gap-6">
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
            <CrawlButton crawling={crawling} onClick={() => startCrawl()} onCancel={stopCrawl} />
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

        <BackToTop />
      </div>
      </div>
    </div>
  );
}
