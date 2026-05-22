import { useCallback } from 'react';
import KeywordManager from '../components/keywords/KeywordManager';
import ErrorMessage from '../components/common/ErrorMessage';
import { useKeywords } from '../hooks/useKeywords';
import { useGlobalCrawl } from '../contexts/CrawlContext';
import { useKeywordHistory } from '../hooks/useKeywordHistory';

export default function KeywordsPage() {
  const { keywords, loading, error, add, update, remove } = useKeywords();
  const { startCrawl } = useGlobalCrawl();
  const { history, addToHistory, removeFromHistory, clearHistory } = useKeywordHistory();

  const handleAdd = useCallback(async (text: string, source: string): Promise<void> => {
    const kw = await add(text, source);
    addToHistory(text);
    await startCrawl(source, [kw.id]);
  }, [add, addToHistory, startCrawl]);

  const handleReAdd = useCallback(async (text: string) => {
    handleAdd(text, 'all');
  }, [handleAdd]);

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="mb-6">
        <h2 className="text-lg font-bold text-gray-800">关键词管理</h2>
        <p className="text-sm text-gray-500 mt-1">
          添加关键词后将自动后台检索该关键词的论文，首页默认显示所有已启用关键词的论文。
        </p>
        <p className="text-xs text-amber-600 mt-1">
          注：关键词检索区分中英文，推荐用英文作为关键词
        </p>
      </div>

      {error && <ErrorMessage message={error} />}

      <div className="space-y-4">
        <div className="bg-white rounded-lg border p-6">
          <KeywordManager
            keywords={keywords}
            loading={loading}
            onAdd={handleAdd}
            onToggle={(id, updates) => update(id, updates)}
            onRemove={remove}
          />
        </div>

        {history.length > 0 && (
          <div className="bg-white rounded-lg border p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700">搜索历史 ({history.length})</h3>
              <button
                onClick={clearHistory}
                className="text-xs text-gray-400 hover:text-red-500 transition-colors"
              >
                清空
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {history.map(entry => (
                <div key={entry.text} className="inline-flex items-center gap-1">
                  <button
                    onClick={() => handleReAdd(entry.text)}
                    className="text-xs px-2.5 py-1 rounded-full bg-gray-100 text-gray-600 hover:bg-emerald-50 hover:text-emerald-600 border border-gray-200 hover:border-emerald-200 transition-colors"
                    title={`添加于 ${new Date(entry.addedAt).toLocaleDateString('zh-CN')}`}
                  >
                    {entry.text}
                  </button>
                  <button
                    onClick={() => removeFromHistory(entry.text)}
                    className="text-gray-300 hover:text-red-500 text-xs"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
