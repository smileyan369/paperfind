import type { FilterState, SciZone, PaperSource } from '../../types/filters';
import { sourceLabel } from '../../utils/labels';

interface Props {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  onReset?: (filters: FilterState) => void;
  activeKeywordIds?: number[];
}

const ZONES: SciZone[] = ['Q1', 'Q2', 'Q3', 'Q4'];
const ZONE_COLORS: Record<string, string> = {
  Q1: 'text-green-700 bg-green-50 border-green-300',
  Q2: 'text-blue-700 bg-blue-50 border-blue-300',
  Q3: 'text-yellow-700 bg-yellow-50 border-yellow-300',
  Q4: 'text-red-700 bg-red-50 border-red-300',
};

const SOURCES: PaperSource[] = ['arxiv', 'crossref', 'semantic_scholar', 'dblp', 'google_scholar', 'jnu_library', 'ieee', 'acm'];

export default function FilterPanel({ filters, onChange, onReset, activeKeywordIds }: Props) {
  const toggleZone = (z: SciZone) => {
    const zones = filters.sciZones.includes(z)
      ? filters.sciZones.filter(x => x !== z)
      : [...filters.sciZones, z];
    onChange({ ...filters, sciZones: zones });
  };

  const toggleSource = (s: PaperSource) => {
    const sources = filters.sources.includes(s)
      ? filters.sources.filter(x => x !== s)
      : [...filters.sources, s];
    onChange({ ...filters, sources });
  };

  return (
    <aside className="w-64 shrink-0">
      <div className="bg-white rounded-lg border p-4 space-y-5 sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-800">筛选</h3>
          {activeKeywordIds && activeKeywordIds.length > 0 && (
            <span className="text-xs text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
              {activeKeywordIds.length} 个关键词
            </span>
          )}
        </div>

        {/* Search */}
        <div>
          <label className="text-xs text-gray-500 mb-1 block">搜索</label>
          <div className="relative">
            <input
              type="text"
              placeholder="标题/摘要..."
              value={filters.searchQuery}
              onChange={e => onChange({ ...filters, searchQuery: e.target.value })}
              className="w-full pl-2 pr-7 py-1.5 text-sm border rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-400"
            />
            {filters.searchQuery && (
              <button
                onClick={() => onChange({ ...filters, searchQuery: '' })}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 text-gray-300 hover:text-gray-500"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* SCI Zone */}
        <div>
          <label className="text-xs text-gray-500 mb-2 block">SCI 分区</label>
          <div className="flex gap-1.5 flex-wrap">
            {ZONES.map(z => (
              <button
                key={z}
                onClick={() => toggleZone(z)}
                className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                  filters.sciZones.includes(z)
                    ? ZONE_COLORS[z]
                    : 'bg-gray-50 text-gray-400 border-gray-200'
                }`}
              >
                {z}
              </button>
            ))}
          </div>
        </div>

        {/* Source */}
        <div>
          <label className="text-xs text-gray-500 mb-2 block">来源</label>
          <div className="flex gap-1 flex-wrap">
            {SOURCES.map(s => (
              <button
                key={s}
                onClick={() => toggleSource(s)}
                className={`px-2 py-0.5 rounded text-xs transition-colors border ${
                  filters.sources.includes(s)
                    ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                    : 'bg-gray-50 text-gray-400 border-gray-200'
                }`}
              >
                {sourceLabel(s)}
              </button>
            ))}
          </div>
        </div>

        {/* Date Range */}
        <div>
          <label className="text-xs text-gray-500 mb-1 block">日期范围</label>
          <div className="space-y-1.5">
            <input
              type="date"
              value={filters.dateFrom || ''}
              onChange={e => onChange({ ...filters, dateFrom: e.target.value || null })}
              className="w-full px-2 py-1 text-xs border rounded-md"
            />
            <input
              type="date"
              value={filters.dateTo || ''}
              onChange={e => onChange({ ...filters, dateTo: e.target.value || null })}
              className="w-full px-2 py-1 text-xs border rounded-md"
            />
          </div>
        </div>

        {/* Min Citations */}
        <div>
          <label className="text-xs text-gray-500 mb-1 block">最低引用数</label>
          <input
            type="number"
            min={0}
            value={filters.citationsMin ?? ''}
            onChange={e => onChange({ ...filters, citationsMin: e.target.value ? Number(e.target.value) : null })}
            className="w-full px-2 py-1.5 text-sm border rounded-md"
          />
        </div>

        {/* Sort */}
        <div>
          <label className="text-xs text-gray-500 mb-1 block">排序</label>
          <select
            value={`${filters.sortBy}|${filters.sortOrder}`}
            onChange={e => {
              const [sortBy, sortOrder] = e.target.value.split('|') as [string, string];
              onChange({ ...filters, sortBy: sortBy as FilterState['sortBy'], sortOrder: sortOrder as FilterState['sortOrder'] });
            }}
            className="w-full px-2 py-1.5 text-sm border rounded-md"
          >
            <option value="sci_zone|asc">分区 (一区优先)</option>
            <option value="sci_zone|desc">分区 (四区优先)</option>
            <option value="publication_date|desc">日期 (最新)</option>
            <option value="publication_date|asc">日期 (最早)</option>
            <option value="citation_count|desc">引用量 (高→低)</option>
            <option value="citation_count|asc">引用量 (低→高)</option>
            <option value="title|asc">标题 (A-Z)</option>
          </select>
        </div>

        {/* Has Summary */}
        <div>
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={filters.hasSummary === true}
              onChange={e => onChange({ ...filters, hasSummary: e.target.checked ? true : null })}
              className="rounded"
            />
            只显示有 AI 摘要的
          </label>
        </div>

        {/* Starred */}
        <div>
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={filters.starred === true}
              onChange={e => onChange({ ...filters, starred: e.target.checked ? true : null })}
              className="rounded"
            />
            只显示已收藏的
          </label>
        </div>

        {/* Reset */}
        <button
          onClick={() => {
            const reset: FilterState = {
              sciZones: [],
              sources: [],
              keywordIds: activeKeywordIds ?? [],
              dateFrom: null,
              dateTo: null,
              citationsMin: null,
              searchQuery: '',
              hasSummary: null,
              starred: null,
              sortBy: 'sci_zone',
              sortOrder: 'asc',
            };
            if (onReset) {
              onReset(reset);
            } else {
              onChange(reset);
            }
          }}
          className="w-full text-xs py-1.5 rounded-md bg-gray-100 text-gray-500 hover:bg-gray-200 transition-colors"
        >
          重置筛选
        </button>
      </div>
    </aside>
  );
}
