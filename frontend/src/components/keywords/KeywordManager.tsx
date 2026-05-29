import { useState } from 'react';
import type { Keyword } from '../../types/keyword';
import KeywordTag from './KeywordTag';

interface Props {
  keywords: Keyword[];
  loading: boolean;
  onAdd: (text: string, source: string) => Promise<unknown>;
  onToggle: (id: number, updates: Partial<Keyword>) => Promise<unknown>;
  onRemove: (id: number) => Promise<unknown>;
}

export default function KeywordManager({ keywords, loading, onAdd, onToggle, onRemove }: Props) {
  const [input, setInput] = useState('');
  const [source, setSource] = useState('all');
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const handleRemove = (id: number) => {
    if (confirmDeleteId === id) {
      onRemove(id);
      setConfirmDeleteId(null);
    } else {
      setConfirmDeleteId(id);
      setTimeout(() => setConfirmDeleteId(null), 3000);
    }
  };

  const handleAdd = async () => {
    const text = input.trim();
    if (!text) return;
    setAdding(true);
    setAddError(null);
    try {
      await onAdd(text, source);
      setInput('');
    } catch (err: any) {
      setAddError(err?.response?.data?.detail || err?.message || '添加失败');
    } finally {
      setAdding(false);
    }
  };

  const active = keywords.filter(k => k.is_active);
  const inactive = keywords.filter(k => !k.is_active);

  return (
    <div className="space-y-6">
      {/* Single Add */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleAdd()}
          placeholder="输入关键词..."
          className="flex-1 px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-400"
        />
        <select
          value={source}
          onChange={e => setSource(e.target.value)}
          className="px-3 py-2 text-sm border rounded-lg bg-white"
        >
          <option value="all">全部来源</option>
          <option value="arxiv">arXiv</option>
          <option value="crossref">Crossref</option>
          <option value="openalex">OpenAlex</option>
          <option value="pubmed">PubMed</option>
          <option value="europe_pmc">Europe PMC</option>
          <option value="semantic_scholar">Semantic Scholar</option>
          <option value="dblp">DBLP</option>
          <option value="google_scholar">Google Scholar</option>
          <option value="jnu_library">暨大图书馆</option>
        </select>
        <button
          onClick={handleAdd}
          disabled={adding || !input.trim()}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          {adding ? '添加中...' : '添加'}
        </button>
      </div>
      {addError && (
        <p className="text-xs text-red-500">{addError}</p>
      )}

      {/* Keyword List */}
      {loading ? (
        <p className="text-sm text-gray-400">加载中...</p>
      ) : (
        <div className="space-y-4">
          {active.length > 0 && (
            <div>
              <h4 className="text-xs text-gray-500 mb-2">已启用 ({active.length})</h4>
              <div className="flex flex-wrap gap-2">
                {active.map(k => (
                  <KeywordTag
                    key={k.id}
                    keyword={k}
                    onToggle={id => onToggle(id, { is_active: false })}
                    onRemove={handleRemove}
                    confirmDelete={confirmDeleteId === k.id}
                  />
                ))}
              </div>
            </div>
          )}
          {inactive.length > 0 && (
            <div>
              <h4 className="text-xs text-gray-500 mb-2">已停用 ({inactive.length})</h4>
              <div className="flex flex-wrap gap-2">
                {inactive.map(k => (
                  <KeywordTag
                    key={k.id}
                    keyword={k}
                    onToggle={id => onToggle(id, { is_active: true })}
                    onRemove={handleRemove}
                    confirmDelete={confirmDeleteId === k.id}
                  />
                ))}
              </div>
            </div>
          )}
          {keywords.length === 0 && (
            <p className="text-sm text-gray-400">暂无关键词，请添加</p>
          )}
        </div>
      )}
    </div>
  );
}
