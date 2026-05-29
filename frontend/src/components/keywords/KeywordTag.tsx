import type { Keyword } from '../../types/keyword';
import { sourceLabel } from '../../utils/labels';

interface Props {
  keyword: Keyword;
  onToggle?: (id: number) => void;
  onRemove?: (id: number) => void;
  active?: boolean;
  confirmDelete?: boolean;
}

export default function KeywordTag({ keyword, onToggle, onRemove, active, confirmDelete }: Props) {
  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs border transition-colors select-none ${
        active
          ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
          : keyword.is_active
            ? 'bg-gray-100 text-gray-700 border-gray-200'
            : 'bg-gray-50 text-gray-400 border-gray-100 line-through'
      }`}
    >
      <span>{keyword.text}</span>
      <span className="text-gray-300">|</span>
      <span className="text-[10px] opacity-60">{sourceLabel(keyword.source)}</span>
      {onToggle && (
        <button
          onClick={() => onToggle(keyword.id)}
          className="ml-0.5 text-gray-400 hover:text-indigo-600"
          title={keyword.is_active ? '停用' : '启用'}
        >
          {keyword.is_active ? '●' : '○'}
        </button>
      )}
      {onRemove && (
        <button
          onClick={() => onRemove(keyword.id)}
          className={confirmDelete ? 'text-red-600 font-bold' : 'text-gray-400 hover:text-red-600'}
          title={confirmDelete ? '再次点击确认删除' : '删除'}
        >
          ×
        </button>
      )}
    </div>
  );
}
