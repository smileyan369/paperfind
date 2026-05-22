import type { Paper } from '../../types/paper';
import SciZoneBadge from '../common/SciZoneBadge';
import { sourceLabel } from '../../utils/labels';

interface Props {
  paper: Paper;
  isRead: boolean;
  onToggleStar: (id: number, starred: boolean) => void;
  onViewDetail: (id: number) => void;
  onSummarize: (id: number) => void;
  onKeywordFilter?: (keywordId: number) => void;
  summarizing: boolean;
  highlight?: boolean;
  aiAvailable?: boolean;
}

export default function PaperCard({ paper, isRead, onToggleStar, onViewDetail, onSummarize, onKeywordFilter, summarizing, highlight, aiAvailable = true }: Props) {
  const authorsList = (() => {
    try {
      const arr = JSON.parse(paper.authors);
      if (Array.isArray(arr)) return arr.slice(0, 3).join(', ');
      return paper.authors || '';
    } catch {
      return paper.authors || '';
    }
  })();

  const authorCount = (() => {
    try {
      const arr = JSON.parse(paper.authors);
      return Array.isArray(arr) ? arr.length : 0;
    } catch {
      return 0;
    }
  })();

  return (
    <div className={`rounded-lg border p-4 hover:shadow-md transition-shadow flex flex-col ${
      highlight
        ? 'border-emerald-300 bg-emerald-50/30 shadow-[0_0_12px_rgba(16,185,129,0.15)]'
        : isRead
          ? 'bg-gray-50 border-gray-200 opacity-75'
          : 'bg-white border-gray-200'
    }`}>
      {/* Zone + source + keyword badges */}
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <SciZoneBadge zone={paper.sci_zone} showMissing />
        <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">{sourceLabel(paper.source)}</span>
        {paper.keyword_texts && paper.keyword_texts.length > 0 && (() => {
          const maxShow = 3;
          const shown = paper.keyword_texts.slice(0, maxShow);
          const overflow = paper.keyword_texts.length - maxShow;
          return (
            <>
              {shown.map((kw, i) => {
                const kwId = paper.keyword_ids?.[i];
                return kwId && onKeywordFilter ? (
                  <button
                    key={`${kw}-${kwId}`}
                    onClick={() => onKeywordFilter(kwId)}
                    className="text-xs text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded hover:bg-emerald-100 transition-colors cursor-pointer"
                    title="点击筛选此关键词"
                  >
                    {kw}
                  </button>
                ) : (
                  <span key={`${kw}-${i}`} className="text-xs text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                    {kw}
                  </span>
                );
              })}
              {overflow > 0 && (
                <span className="text-xs text-gray-400" title={paper.keyword_texts.slice(maxShow).join(', ')}>
                  +{overflow}
                </span>
              )}
            </>
          );
        })()}
        {isRead && (
          <span className="text-xs text-gray-400 bg-gray-200 px-1.5 py-0.5 rounded">已读</span>
        )}
        {paper.summary_status === 'completed' ? (
          <button
            onClick={() => onViewDetail(paper.id)}
            className="text-xs text-indigo-500 bg-indigo-50 px-1.5 py-0.5 rounded hover:bg-indigo-100 transition-colors cursor-pointer"
          >
            已总结
          </button>
        ) : paper.summary_status === 'processing' ? (
          <span className="text-xs text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded flex items-center gap-1">
            <span className="inline-block w-2 h-2 border border-amber-400 border-t-amber-600 rounded-full animate-spin" />
            总结中
          </span>
        ) : null}
      </div>

      {/* Title — clickable */}
      <h4
        onClick={() => onViewDetail(paper.id)}
        className={`font-semibold text-sm leading-snug mb-2 line-clamp-2 cursor-pointer hover:text-indigo-600 transition-colors ${isRead ? 'text-gray-500' : 'text-gray-800'}`}
      >
        {paper.title}
      </h4>

      {/* Authors */}
      <p className="text-xs text-gray-500 mb-2 truncate">
        {authorsList}{authorCount > 3 ? ' et al.' : ''}
      </p>

      {/* Abstract preview */}
      {paper.abstract && (
        <p className="text-xs text-gray-400 leading-relaxed mb-3 line-clamp-3 flex-1">
          {paper.abstract}
        </p>
      )}

      {/* Meta */}
      <div className="flex items-center gap-3 text-xs text-gray-400 mb-3">
        {(paper.publication_date || paper.year) && <span>{paper.publication_date || paper.year}</span>}
        <span>引用 {paper.citation_count}</span>
        {paper.journal_name && (
          <span className="truncate max-w-[150px]">{paper.journal_name}</span>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
        <button
          onClick={() => onViewDetail(paper.id)}
          className="text-xs px-2 py-1 rounded-md bg-gray-50 text-gray-600 hover:bg-gray-100 transition-colors"
        >
          详情
        </button>
        <button
          onClick={() => onToggleStar(paper.id, !paper.is_starred)}
          className={`text-xs px-2 py-1 rounded-md transition-colors ${
            paper.is_starred
              ? 'bg-yellow-50 text-yellow-700 hover:bg-yellow-100'
              : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
          }`}
        >
          {paper.is_starred ? '已收藏' : '收藏'}
        </button>
        {paper.url && (
          <a
            href={paper.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-2 py-1 rounded-md bg-gray-50 text-indigo-600 hover:bg-indigo-50 transition-colors"
          >
            原文
          </a>
        )}
        {aiAvailable && (
          <button
            onClick={() => onSummarize(paper.id)}
            disabled={summarizing || paper.summary_status === 'processing'}
            className={`text-xs px-2 py-1 rounded-md transition-colors ml-auto ${
              paper.summary_status === 'completed'
                ? 'bg-green-50 text-green-700'
                : paper.summary_status === 'processing'
                  ? 'bg-amber-50 text-amber-600'
                  : 'bg-indigo-50 text-indigo-600 hover:bg-indigo-100'
            }`}
          >
            {summarizing ? '生成中...'
              : paper.summary_status === 'completed' ? '已总结'
              : paper.summary_status === 'processing' ? '总结中'
              : 'AI 总结'}
          </button>
        )}
        {!aiAvailable && (
          <span className="text-xs text-gray-400 ml-auto">无 AI</span>
        )}
      </div>
    </div>
  );
}
