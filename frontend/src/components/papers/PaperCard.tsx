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

export default function PaperCard({
  paper,
  isRead,
  onToggleStar,
  onViewDetail,
  onSummarize,
  onKeywordFilter,
  summarizing,
  highlight,
  aiAvailable = true,
}: Props) {
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
    <article
      className={`premium-card paper-card-interactive rounded-2xl p-4 flex flex-col min-h-[260px] soft-appear ${
        highlight ? 'ring-2 ring-emerald-300' : ''
      } ${isRead ? 'opacity-72' : ''}`}
    >
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <SciZoneBadge zone={paper.sci_zone} showMissing />
        <span className="text-xs text-slate-500 bg-slate-100/80 px-2 py-1 rounded-full">{sourceLabel(paper.source)}</span>
        {paper.keyword_texts?.slice(0, 3).map((kw, i) => {
          const kwId = paper.keyword_ids?.[i];
          return kwId && onKeywordFilter ? (
            <button
              key={`${kw}-${kwId}`}
              onClick={() => onKeywordFilter(kwId)}
              className="text-xs text-teal-700 bg-teal-50 px-2 py-1 rounded-full hover:bg-teal-100 transition-colors"
              title="按这个关键词筛选"
            >
              {kw}
            </button>
          ) : (
            <span key={`${kw}-${i}`} className="text-xs text-teal-700 bg-teal-50 px-2 py-1 rounded-full">{kw}</span>
          );
        })}
        {isRead && <span className="text-xs text-slate-400 bg-slate-100 px-2 py-1 rounded-full">已读</span>}
        {paper.summary_status === 'completed' && (
          <button
            onClick={() => onViewDetail(paper.id)}
            className="text-xs text-indigo-700 bg-indigo-50 px-2 py-1 rounded-full hover:bg-indigo-100 transition-colors"
          >
            已导读
          </button>
        )}
        {paper.summary_status === 'processing' && (
          <span className="text-xs text-amber-700 bg-amber-50 px-2 py-1 rounded-full flex items-center gap-1">
            <span className="inline-block w-2 h-2 border border-amber-400 border-t-amber-700 rounded-full animate-spin" />
            导读中
          </span>
        )}
      </div>

      <h4
        onClick={() => onViewDetail(paper.id)}
        className={`font-semibold text-[15px] leading-snug mb-2 line-clamp-2 cursor-pointer hover:text-indigo-700 transition-colors ${
          isRead ? 'text-slate-500' : 'text-slate-950'
        }`}
      >
        {paper.title}
      </h4>

      <p className="text-xs text-slate-500 mb-2 truncate">
        {authorsList}{authorCount > 3 ? ' et al.' : ''}
      </p>

      {paper.abstract && (
        <p className="text-xs text-slate-500/85 leading-relaxed mb-3 line-clamp-3 flex-1">
          {paper.abstract}
        </p>
      )}

      <div className="flex items-center gap-3 text-xs text-slate-400 mb-3">
        {(paper.publication_date || paper.year) && <span>{paper.publication_date || paper.year}</span>}
        <span>引用 {paper.citation_count}</span>
        {paper.journal_name && <span className="truncate max-w-[150px]">{paper.journal_name}</span>}
      </div>

      <div className="flex items-center gap-2 pt-3 border-t border-slate-100">
        <button onClick={() => onViewDetail(paper.id)} className="text-xs px-2.5 py-1.5 rounded-lg bg-white text-slate-600 border border-slate-100 hover:bg-slate-50 transition-colors">
          详情
        </button>
        <button
          onClick={() => onToggleStar(paper.id, !paper.is_starred)}
          className={`text-xs px-2.5 py-1.5 rounded-lg border transition-colors ${
            paper.is_starred
              ? 'bg-amber-50 text-amber-700 border-amber-100'
              : 'bg-white text-slate-500 border-slate-100 hover:bg-slate-50'
          }`}
        >
          {paper.is_starred ? '已收藏' : '收藏'}
        </button>
        {paper.url && (
          <a href={paper.url} target="_blank" rel="noopener noreferrer" className="text-xs px-2.5 py-1.5 rounded-lg bg-white text-indigo-700 border border-indigo-100 hover:bg-indigo-50 transition-colors">
            原文
          </a>
        )}
        {aiAvailable ? (
          <button
            onClick={() => onSummarize(paper.id)}
            disabled={summarizing || paper.summary_status === 'processing'}
            className={`text-xs px-2.5 py-1.5 rounded-lg transition-colors ml-auto ${
              paper.summary_status === 'completed'
                ? 'bg-emerald-50 text-emerald-700'
                : paper.summary_status === 'processing'
                  ? 'bg-amber-50 text-amber-700'
                  : 'premium-button text-white disabled:opacity-60'
            }`}
          >
            {summarizing ? '生成中'
              : paper.summary_status === 'completed' ? '已导读'
              : paper.summary_status === 'processing' ? '导读中'
              : 'AI 导读'}
          </button>
        ) : (
          <span className="text-xs text-slate-400 ml-auto">无 AI</span>
        )}
      </div>
    </article>
  );
}
