import { useEffect, useState, useRef } from 'react';
import type { PaperDetail } from '../../types/paper';
import { fetchPaperDetail } from '../../api/papers';
import { apiUrl } from '../../api/client';
import SciZoneBadge from '../common/SciZoneBadge';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorMessage from '../common/ErrorMessage';
import { sourceLabel } from '../../utils/labels';

interface Props {
  paperId: number | null;
  onClose: () => void;
  onSummaryDone?: (paperId: number) => void;
  aiAvailable?: boolean;
}

export default function PaperDetailModal({ paperId, onClose, onSummaryDone, aiAvailable = true }: Props) {
  const [paper, setPaper] = useState<PaperDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Streaming AI summary state
  const [streamingText, setStreamingText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [streamElapsed, setStreamElapsed] = useState(0);
  const [streamPhase, setStreamPhase] = useState<'connecting' | 'generating' | 'done'>('connecting');
  const abortRef = useRef<AbortController | null>(null);
  const elapsedTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (paperId === null) return;
    setLoading(true);
    setError(null);
    setPaper(null);
    setStreamingText('');
    setIsStreaming(false);
    setStreamError(null);
    setStreamElapsed(0);
    setStreamPhase('connecting');
    if (abortRef.current) { abortRef.current.abort(); }
    if (elapsedTimerRef.current) { clearInterval(elapsedTimerRef.current); }
    fetchPaperDetail(paperId)
      .then(p => { setPaper(p); })
      .catch(err => setError(err?.message || '加载论文详情失败'))
      .finally(() => setLoading(false));
  }, [paperId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  const handleStreamSummarize = async (id: number) => {
    setIsStreaming(true);
    setStreamingText('');
    setStreamError(null);
    setStreamElapsed(0);
    setStreamPhase('connecting');
    const startTime = Date.now();
    const abort = new AbortController();
    abortRef.current = abort;

    // Elapsed time counter (updates every 100ms for smooth display)
    const timer = setInterval(() => {
      setStreamElapsed(Math.floor((Date.now() - startTime) / 100) / 10);
    }, 100);
    elapsedTimerRef.current = timer;

    try {
      const res = await fetch(apiUrl(`/summary/${id}/stream`), { signal: abort.signal });
      if (!res.ok) {
        setStreamError(res.status === 503 ? '无 AI：请先在设置中配置 API Key' : `请求失败 (${res.status})`);
        setIsStreaming(false);
        clearInterval(timer);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) { setIsStreaming(false); clearInterval(timer); return; }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Parse SSE events
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === 'chunk') {
                if (streamPhase !== 'generating') setStreamPhase('generating');
                setStreamingText(prev => prev + data.text);
              } else if (data.type === 'status') {
                // Capture source info from status messages
                if (data.source_type) {
                  setPaper(prev => prev ? {
                    ...prev,
                    source_type: data.source_type,
                    source_chars: data.source_chars || prev.source_chars,
                  } : prev);
                }
              } else if (data.type === 'done') {
                setIsStreaming(false);
                setStreamPhase('done');
                clearInterval(timer);
                if (data.summary) {
                  setPaper(prev => prev ? {
                    ...prev,
                    summary_cn: data.summary,
                    summary_status: 'completed',
                    source_type: data.source_type || prev.source_type,
                    source_chars: data.source_chars || prev.source_chars,
                  } : prev);
                } else {
                  fetchPaperDetail(id).then(p => {
                    if (p) setPaper(p);
                    if (p?.summary_status === 'completed' && p.summary_cn) onSummaryDone?.(id);
                  });
                  continue;
                }
                onSummaryDone?.(id);
              } else if (data.type === 'error') {
                setStreamError(data.message);
                setIsStreaming(false);
                clearInterval(timer);
              }
            } catch { /* skip parse errors */ }
          }
        }
      }
    } catch (e: any) {
      if (e?.name !== 'AbortError') {
        setStreamError(e?.message || '流式请求失败');
      }
      setIsStreaming(false);
      clearInterval(timer);
    }
  };

  if (!paperId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto m-4"
        onClick={e => e.stopPropagation()}
      >
        {loading ? (
          <LoadingSpinner />
        ) : error ? (
          <div className="p-6"><ErrorMessage message={error} /></div>
        ) : paper ? (
          <div className="p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 flex-wrap">
                <SciZoneBadge zone={paper.sci_zone} />
                <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">{sourceLabel(paper.source)}</span>
                {paper.keyword_texts && paper.keyword_texts.length > 0 && paper.keyword_texts.map((kw) => (
                  <span key={kw} className="text-xs text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                    {kw}
                  </span>
                ))}
              </div>
              <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>

            <h3 className="text-lg font-bold text-gray-800 mb-2">{paper.title}</h3>

            <p className="text-sm text-gray-500 mb-4">
              {(() => { try { return (JSON.parse(paper.authors) as string[]).join(', '); } catch { return paper.authors; } })()}
            </p>

            <div className="flex gap-4 text-xs text-gray-400 mb-4">
              {(paper.publication_date || paper.year) && <span>日期: {paper.publication_date || paper.year}</span>}
              <span>引用: {paper.citation_count}</span>
              {paper.journal_name && <span>期刊: {paper.journal_name}</span>}
              {paper.doi && <span>DOI: {paper.doi}</span>}
            </div>

            {/* Original Abstract */}
            {paper.abstract ? (
              <div className="mb-4">
                <h4 className="font-semibold text-sm text-gray-700 mb-1">原始摘要</h4>
                <p className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3">{paper.abstract}</p>
              </div>
            ) : !paper.summary_cn && !streamingText && (
              <div className="mb-4">
                <p className="text-sm text-gray-400 bg-gray-50 rounded-lg p-3 text-center">
                  该论文暂无摘要，可点击下方 AI 导读生成中文导读
                </p>
              </div>
            )}

            {/* Streaming AI Summary */}
            {isStreaming && (
              <div className="mb-4">
                <h4 className="font-semibold text-sm text-indigo-700 mb-1 flex items-center gap-2">
                  {streamPhase === 'connecting' ? '正在连接 AI 服务...' : 'AI 正在生成中'}
                  <span className="inline-block w-2.5 h-2.5 border-2 border-indigo-400 border-t-indigo-600 rounded-full animate-spin" />
                  <span className="text-xs text-gray-400 font-normal ml-auto">
                    {streamElapsed.toFixed(1)}s
                    {streamPhase === 'generating' && streamingText.length > 0 && (
                      <span> · 已生成 {streamingText.length} 字</span>
                    )}
                  </span>
                </h4>
                <div className="text-sm text-gray-700 bg-indigo-50 rounded-lg p-3 whitespace-pre-wrap min-h-[3rem]">
                  {streamingText || (
                    <span className="text-gray-400 italic">等待模型响应...</span>
                  )}
                  {streamPhase === 'generating' && (
                    <span className="inline-block w-2 h-4 bg-indigo-400 animate-pulse ml-0.5 align-middle" />
                  )}
                </div>
              </div>
            )}

            {/* Completed AI Summary */}
            {!isStreaming && paper.summary_status === 'completed' && paper.summary_cn && (
              <div className="mb-4">
                <h4 className="font-semibold text-sm text-indigo-700 mb-1">AI 中文导读</h4>
                <div className="text-sm text-gray-700 bg-indigo-50 rounded-lg p-3 whitespace-pre-wrap">
                  {paper.summary_cn}
                </div>
                {(paper.model_used || paper.source_type) && (
                  <p className="text-xs text-gray-400 mt-1 flex items-center gap-2 flex-wrap">
                    {paper.source_type && (
                      <span className={`px-1.5 py-0.5 rounded-full ${
                        paper.source_type === 'pdf' ? 'bg-red-50 text-red-600' :
                        paper.source_type === 'html' ? 'bg-blue-50 text-blue-600' :
                        paper.source_type === 'abstract' ? 'bg-amber-50 text-amber-600' :
                        'bg-gray-100 text-gray-500'
                      }`}>
                        {paper.source_type === 'pdf' ? '基于 PDF 全文' :
                         paper.source_type === 'html' ? '基于网页正文' :
                         paper.source_type === 'abstract' ? '基于摘要' :
                         paper.source_type === 'metadata' ? '基于元信息' :
                         paper.source_type}
                        {paper.source_chars > 0 && ` (${paper.source_chars} 字)`}
                      </span>
                    )}
                    {paper.model_used && <span>模型: {paper.model_used}</span>}
                    {paper.summary_generated_at && (() => {
                      try { return ` · ${new Date(paper.summary_generated_at).toLocaleDateString('zh-CN')}`; }
                      catch { return ''; }
                    })()}
                  </p>
                )}
              </div>
            )}

            {/* Processing state (background queue, not streaming) */}
            {!isStreaming && paper.summary_status === 'processing' && (
              <div className="mb-4">
                <div className="text-sm text-amber-600 bg-amber-50 rounded-lg p-3 flex items-center gap-2">
                  <span className="inline-block w-3 h-3 border border-amber-400 border-t-amber-600 rounded-full animate-spin" />
                  正在生成 AI 导读...
                </div>
              </div>
            )}

            {/* Stream error */}
            {streamError && (
              <div className="mb-4">
                <p className="text-sm text-red-600 bg-red-50 rounded-lg p-3">{streamError}</p>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2 pt-3 border-t">
              {paper.url && (
                <a href={paper.url} target="_blank" rel="noopener noreferrer"
                   className="text-sm px-3 py-1.5 rounded-md bg-gray-100 text-indigo-600 hover:bg-indigo-50">
                  查看原文
                </a>
              )}
              {paper.pdf_url && (
                <a href={paper.pdf_url} target="_blank" rel="noopener noreferrer"
                   className="text-sm px-3 py-1.5 rounded-md bg-gray-100 text-red-600 hover:bg-red-50">
                  PDF
                </a>
              )}
              {!aiAvailable && paper.summary_status !== 'completed' && (
                <span className="text-xs text-gray-400">无 AI：未配置 API Key</span>
              )}
              {aiAvailable && paper.summary_status !== 'completed' && !isStreaming && (
                <button
                  onClick={() => handleStreamSummarize(paper.id)}
                  disabled={isStreaming || paper.summary_status === 'processing'}
                  className="text-sm px-3 py-1.5 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {paper.summary_status === 'processing' ? '生成中...' : 'AI 导读'}
                </button>
              )}
              {isStreaming && (
                <button
                  onClick={() => {
                    abortRef.current?.abort();
                    if (elapsedTimerRef.current) clearInterval(elapsedTimerRef.current);
                    setIsStreaming(false);
                  }}
                  className="text-sm px-3 py-1.5 rounded-md bg-red-100 text-red-600 hover:bg-red-200"
                >
                  取消
                </button>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
